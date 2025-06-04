import base64
import traceback
from typing import Any

import yaml
from src.core.template_loader import template_loader
from src.core.utils import encrypt_password

from src.api.schemas.cluster import ClusterPool
from src.core.apps.other import longhorn_chart, certmanager_chart, cluster_autoscaler_chart
from src.core.exceptions import NamespaceTerminatedException
from src.core.kubernetes.configuration import ClusterConfiguration
from src.core.kubernetes.kubernetes_client import KubernetesClient
from src.core.kubernetes.helm_client import HelmClient
from pathlib import Path
from src.core.kubernetes.chart_config import HelmChart
from src.database.models.cluster import Cluster
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type


class KubernetesCluster:
    def __init__(self, config: ClusterConfiguration, access_ip: str, kubeconfig_path: Path):
        self.config = config
        self.access_ip = access_ip
        self.kubeconfig_path = kubeconfig_path
        self._client = KubernetesClient(kubeconfig_path)
        self._helm_client = HelmClient(kubeconfig=kubeconfig_path)

    def create_namespace(self, namespace: str):
        try:
            self._client.create_namespace(namespace)
            print(f'Namespace {namespace} created')
        except Exception as e:
            # TODO: better error handling, e.g. for duplicated namespace name
            print(f'Failed to create namespace {namespace}: {e}')

    @retry(retry=retry_if_exception_type(NamespaceTerminatedException), stop=stop_after_attempt(5), wait=wait_fixed(5), reraise=True)
    async def install_or_upgrade_chart(self, helm_chart: HelmChart, values: dict[str, Any] = None, namespace: str = None):
        values = values or {}
        namespace = namespace or helm_chart.name.lower().split('/')[-1]

        self.create_namespace(namespace)

        print(f"Installing {helm_chart.name}... with values: {values}")
        try:
            if helm_chart.is_oci:
                chart = await self._helm_client.get_oci_chart(
                    helm_chart.name,
                    repo=helm_chart.repo_url,
                    version=helm_chart.version
                )
            else:
                chart = await self._helm_client.get_chart(
                    helm_chart.name,
                    repo=helm_chart.repo_url,
                    version=helm_chart.version
                )
        except Exception as e:
            msg = f"Failed to get chart: {e}"
            print(msg)
            raise ValueError(msg)

        try:
            if helm_chart.is_oci:
                result = await self._helm_client.install_or_upgrade_oci_release(
                    helm_chart.name,
                    chart,
                    values,
                    create_namespace=False,
                    reuse_values=True,
                    namespace=namespace.lower(),
                    #wait=True,     # wait=True sometime caused errors with Airflow deployment
                    timeout='300s'
                )
            else:
                result = await self._helm_client.install_or_upgrade_release(
                    helm_chart.name,
                    chart,
                    values,
                    create_namespace=False,
                    reuse_values=True,
                    namespace=namespace.lower(),
                    #wait=True,
                    timeout='300s'
                )
        except Exception as e:
            if f"namespace {namespace} because it is being terminated" in str(e):
                raise NamespaceTerminatedException(f'Namespace {namespace} in terminated state, retrying...')

            msg = f"Failed to install chart: {e}"
            #print(msg)
            #print(traceback.format_exc())
            raise ValueError(msg)

        print(f"{helm_chart.name} installation complete: {result.status}")

        return True

    async def uninstall_chart(self, helm_chart: HelmChart, namespace: str = None):
        namespace = namespace or helm_chart.name.lower()
        print(f'Will uninstall chart {helm_chart.name}')
        await self._helm_client.uninstall_release(release_name=helm_chart.name, namespace=namespace)

        self._client.delete_namespace(namespace)
        print(f'Successfully uninstalled chart {helm_chart.name}')

    def cordon_node(self, node_name: str):
        self._client.cordon_node(node_name)

    async def install_longhorn(self):
        print("Installing Longhorn")
        values = {
            "defaultSettings": {
                "defaultDataPath": "/var/longhorn"
            },
            "persistence": {
                "defaultFsType": "ext4",
                "defaultClassReplicaCount": 2,
                "defaultClass": False
            }
        }
        await self.install_or_upgrade_chart(longhorn_chart, values)

        print("Installed Longhorn successfully")

    async def install_certmanager(self, domain_name: str):
        print("Installing Certmanager")
        values = {
            "crds": {
                "enabled": True
            }
        }
        await self.install_or_upgrade_chart(certmanager_chart, values)
        print("Installed Certmanager successfully")

        self._add_acme_certificate_issuer()
        self.create_certificate(certificate_name='main-certificate', domain_name=domain_name,
                                   secret_name="main-certificate-tls", namespace='kube-system')

    async def install_clusterautoscaler(self, provider_token: str, cluster_config: ClusterConfiguration, cloud_init: str):
        print("Installing ClusterAutoscaler")
        values = {
            "cloudProvider": "hetzner",
            "extraEnv": {
                "HCLOUD_TOKEN": provider_token,
                "HCLOUD_CLOUD_INIT": base64.b64encode(cloud_init.encode()).decode("ascii"),
                # TODO: remove hardcoded values
                "HCLOUD_NETWORK": f'{cluster_config.name}-network',
                "HCLOUD_SSH_KEY": f'{cluster_config.name}-ssh-key'
            },
            "autoscalingGroups": [
                {"name": f'{x.name}-autoscaled', "minSize": x.autoscaling.min_nodes, "maxSize": x.autoscaling.max_nodes,
                 "instanceType": x.node_type, "region": x.region}
                for x in cluster_config.pools if x.autoscaling and x.autoscaling.enabled
            ]
        }

        await self.install_or_upgrade_chart(cluster_autoscaler_chart, values, namespace='kube-system')
        print("Installed ClusterAutoscaler successfully")

    def expose_traefik_dashboard(self, username: str, password: str, enable_https: bool, domain_name: str = None, secret_name: str = None):
        traefik_custom_config_template = template_loader.get_template('traefik-custom-config.yaml', 'kubernetes')

        # Update default Traefik config to allow change of API base path
        try:
            self._client.install_from_yaml(traefik_custom_config_template, with_custom_objects=True)
            print('Traefik custom config applied successfully!')
        except Exception as e:
            print(f"Failed to apply Traefik custom config: {e}")

        encrypted_password = encrypt_password(username, password)
        dashboard_creds_secret_name = 'traefik-dashboard-creds-secret'
        dashboard_creds_secret_namespace = 'kube-system'
        middleware_name = 'traefik-dashboard-auth-middleware'

        self.create_secret(dashboard_creds_secret_name, dashboard_creds_secret_namespace, {'users': encrypted_password})

        values = {
            'namespace': dashboard_creds_secret_namespace,
            'secret_name': dashboard_creds_secret_name,
            'middleware_name': middleware_name,
        }

        with template_loader.render_to_temp_file('traefik-basic-auth-middleware.yaml', values, 'kubernetes') as rendered_template_file:
            try:
                self._client.install_from_yaml(rendered_template_file, with_custom_objects=True)
                print('Traefik basic auth middleware applied successfully!')
            except Exception as e:
                print(f"Failed to apply Traefik basic auth middleware: {e}")

        values = {
            'enable_https': enable_https,
            'domain_name': domain_name,
            'certificate_secret_name': secret_name,
            'middleware_name': middleware_name,
        }

        with template_loader.render_to_temp_file('traefik-dashboard-ingress-route.yaml', values, 'kubernetes') as rendered_template_file:
            try:
                self._client.install_from_yaml(rendered_template_file, with_custom_objects=True)
                print('Traefik dashboard exposed successfully!')
            except Exception as e:
                print(f"Failed to expose Traefik dashboard: {e}")

    def _add_acme_certificate_issuer(self):
        path_to_template = template_loader.get_template('cert-manager-acme-issuer.yaml', 'kubernetes')

        try:
            self._client.install_from_yaml(path_to_template, with_custom_objects=True)
            print('Certificate issuer successfully added!')
        except Exception as e:
            print(f"Failed to add certificate issuer: {e}")

    def create_certificate(self, certificate_name, domain_name, secret_name, namespace):
        print(f'Creating certificate {certificate_name} for domain {domain_name} as secret {secret_name}')

        values = {'certificate_name': certificate_name, 'domain_name': domain_name, 'secret_name': secret_name}

        with template_loader.render_to_temp_file('cert-manager-acme-certificate.yaml', values, 'kubernetes') as rendered_template_file:
            try:
                self._client.install_from_yaml(rendered_template_file, with_custom_objects=True)
                print('Certificate successfully created!')
            except Exception as e:
                print(f"Failed to create certificate: {e}")

    def install_csi(self, provider: str):
        path_to_template = template_loader.get_template(f'{provider}-csi.yaml', 'kubernetes')

        try:
            self._client.install_from_yaml(path_to_template)
            print(f'{provider.capitalize()} CSI installed successfully!')
        except Exception as e:
            print(f"Failed to install {provider.capitalize()} CSI: {e}")

    def install_cloud_controller(self, provider: str):
        path_to_template = template_loader.get_template(f'{provider}-cloud-controller.yaml', 'kubernetes')

        try:
            self._client.install_from_yaml(path_to_template)
            print(f'{provider.capitalize()} installed successfully!')
        except Exception as e:
            print(f"Failed to install {provider.capitalize()} Cloud Controller: {e}")

    def execute_command_on_pod(self, pod: str, namespace: str, command: list[str], interactive: bool = False, command_input: str = None):
        output, errors = self._client.execute_command(pod, namespace, command, interactive, command_input)

        return output

    def apply_file(self, path_to_template: Path, with_custom_objects: bool = False):
        if not path_to_template.exists():
            raise FileNotFoundError(f"File {path_to_template} does not exist")

        try:
            self._client.install_from_yaml(path_to_template, with_custom_objects)
            print(f'Applied file {path_to_template} successfully!')
        except Exception as e:
            print(f"Failed to apply file {path_to_template}: {e}")
            raise

    def create_object_from_content(self, yaml_content: dict | list[dict]):
        self._client.install_from_content(yaml_content)

    def create_secret(self, secret_name: str, namespace: str, data: dict[str, str]):
        self._client.create_secret(secret_name, namespace, data)

    def get_secret(self, secret_name: str, namespace: str) -> dict | None:
        return self._client.get_secret(secret_name, namespace)

    @classmethod
    def from_db_model(cls, cluster: Cluster):
        return cls(
            ClusterConfiguration(
                domain_name=cluster.domain_name,
                name=cluster.name,
                k3s_version=cluster.k3s_version,
                pools=[ClusterPool(**x) for x in cluster.pools],
                additional_components=cluster.additional_components
            ),
            cluster.access_ip,
            cluster.kubeconfig_path
        )
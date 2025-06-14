import base64
import json
from typing import Any

import yaml
from src.core.template_loader import template_loader
from src.core.utils import encrypt_password, setup_logger

from src.api.schemas.cluster import ClusterPool
from src.core.apps.other import longhorn_chart, certmanager_chart, cluster_autoscaler_chart
from src.core.exceptions import NamespaceTerminatedException
from kubernetes.client.exceptions import ApiException
from src.core.kubernetes.configuration import ClusterConfiguration
from src.core.kubernetes.kubernetes_client import KubernetesClient
from src.core.kubernetes.helm_client import HelmClient
from pathlib import Path
from src.core.kubernetes.chart_config import HelmChart
from src.database.models.cluster import Cluster
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type


class KubernetesCluster:
    def __init__(self, config: ClusterConfiguration, access_ip: str, kubeconfig_path: Path):
        self._logger = setup_logger('KubernetesCluster')

        self.config = config
        self.access_ip = access_ip
        self.kubeconfig_path = kubeconfig_path
        self._client = KubernetesClient(kubeconfig_path)
        self._helm_client = HelmClient(kubeconfig=kubeconfig_path)

    def _parse_kubernetes_api_exception(self, exception: ApiException):
        original_reason = exception.reason
        body = json.loads(exception.body)

        self._logger.debug(f'Original reason: {original_reason}')

        return body['reason'], body['message']

    @retry(retry=retry_if_exception_type(NamespaceTerminatedException), wait=wait_fixed(10), stop=stop_after_attempt(10), reraise=True)
    def create_namespace(self, namespace: str, skip_if_exists: bool = True):
        try:
            self._client.create_namespace(namespace)
            self._logger.info(f'Namespace {namespace} created')
        except ApiException as e:
            self._logger.exception(f'Failed to create namespace {namespace}', exc_info=False)
            reason, message = self._parse_kubernetes_api_exception(e)
            self._logger.debug(f"Reason: {reason}")
            self._logger.debug(f"Body: {message}")
            if reason in ('AlreadyExists', 'NamespaceTerminating'):
                if "object is being deleted" in message or "is being terminated" in message:
                    self._logger.warning('Namespace is being deleted, retrying...')
                    raise NamespaceTerminatedException
                else:
                    if skip_if_exists:
                        self._logger.warning(f'Namespace {namespace} already exists, skipping creation')
                        return
                    else:
                        raise e

    async def install_or_upgrade_chart(self, helm_chart: HelmChart, values: dict[str, Any] = None, namespace: str = None):
        values = values or {}
        namespace = namespace or helm_chart.name.lower().split('/')[-1]

        self.create_namespace(namespace)

        self._logger.info(f"Installing {helm_chart.name} with values: {values}")
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
            self._logger.exception(msg, exc_info=False)
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
                    timeout='600s'
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
                    timeout='600s'
                )
        except Exception as e:
            msg = f"Failed to install chart: {e}"
            self._logger.exception(msg, exc_info=False)
            raise ValueError(msg)

        self._logger.info(f"{helm_chart.name} installation complete: {result.status}")

    async def uninstall_chart(self, helm_chart: HelmChart, namespace: str = None):
        namespace = namespace or helm_chart.name.lower()
        self._logger.info(f'Will uninstall chart {helm_chart.name}')
        await self._helm_client.uninstall_release(release_name=helm_chart.name, namespace=namespace)

        self._client.delete_namespace(namespace)
        self._logger.info(f'Successfully uninstalled chart {helm_chart.name}')

    def cordon_node(self, node_name: str):
        self._client.cordon_node(node_name)

    async def install_longhorn(self):
        self._logger.info("Installing Longhorn")
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

        self._logger.info("Installed Longhorn successfully")

    async def install_certmanager(self, domain_name: str):
        self._logger.info("Installing Certmanager")
        values = {
            "crds": {
                "enabled": True
            }
        }
        await self.install_or_upgrade_chart(certmanager_chart, values)
        self._logger.info("Installed Certmanager successfully")

        self._add_acme_certificate_issuer()
        self.create_certificate(certificate_name='main-certificate', domain_name=domain_name,
                                   secret_name="main-certificate-tls", namespace='kube-system')

    async def install_clusterautoscaler(self, provider_token: str, cluster_config: ClusterConfiguration, cloud_init: str):
        self._logger.info("Installing ClusterAutoscaler")
        values = {
            "cloudProvider": "hetzner",
            "extraEnv": {
                "HCLOUD_TOKEN": provider_token,
                "HCLOUD_CLOUD_INIT": base64.b64encode(cloud_init.encode()).decode("ascii"),
                # TODO: remove hardcoded values
                "HCLOUD_NETWORK": f'{cluster_config.name}-network',
                "HCLOUD_SSH_KEY": f'{cluster_config.name}-ssh-key'
            },
            # The following args should disable scale down based on utilization,
            # however seems they don't work as expected, keeping for reference for now
            "extraArgs": {
                "scale-down-utilization-threshold": 0,
                "scale-down-gpu-utilization-threshold": 0
            },
            "autoscalingGroups": [
                {"name": f'{x.name}-autoscaled', "minSize": x.autoscaling.min_nodes, "maxSize": x.autoscaling.max_nodes,
                 "instanceType": x.node_type, "region": x.region}
                for x in cluster_config.pools if x.autoscaling and x.autoscaling.enabled
            ]
        }

        await self.install_or_upgrade_chart(cluster_autoscaler_chart, values, namespace='kube-system')
        self._logger.info("Installed ClusterAutoscaler successfully")

    def expose_traefik_dashboard(self, username: str, password: str, enable_https: bool, domain_name: str = None, secret_name: str = None):
        traefik_custom_config_template = template_loader.get_template('traefik-custom-config.yaml', 'kubernetes')

        # Update default Traefik config to allow change of API base path
        try:
            self._client.install_from_yaml(traefik_custom_config_template, with_custom_objects=True)
            self._logger.info('Traefik custom config applied successfully!')
        except Exception as e:
            self._logger.exception(f"Failed to apply Traefik custom config: {e}", exc_info=False)

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
                self._logger.info('Traefik basic auth middleware applied successfully!')
            except Exception as e:
                self._logger.exception(f"Failed to apply Traefik basic auth middleware: {e}", exc_info=False)

        values = {
            'enable_https': enable_https,
            'domain_name': domain_name,
            'certificate_secret_name': secret_name,
            'middleware_name': middleware_name,
        }

        with template_loader.render_to_temp_file('traefik-dashboard-ingress-route.yaml', values, 'kubernetes') as rendered_template_file:
            try:
                self._client.install_from_yaml(rendered_template_file, with_custom_objects=True)
                self._logger.info('Traefik dashboard exposed successfully!')
            except Exception as e:
                self._logger.exception(f"Failed to expose Traefik dashboard: {e}", exc_info=True)

    def _add_acme_certificate_issuer(self):
        path_to_template = template_loader.get_template('cert-manager-acme-issuer.yaml', 'kubernetes')

        try:
            self._client.install_from_yaml(path_to_template, with_custom_objects=True)
            self._logger.info('Certificate issuer successfully added!')
        except Exception as e:
            self._logger.exception(f"Failed to add certificate issuer: {e}", exc_info=False)

    def create_certificate(self, certificate_name, domain_name, secret_name, namespace):
        self._logger.info(f'Creating certificate {certificate_name} for domain {domain_name} as secret {secret_name}')

        values = {'certificate_name': certificate_name, 'domain_name': domain_name, 'secret_name': secret_name, 'namespace': namespace}

        with template_loader.render_to_temp_file('cert-manager-acme-certificate.yaml', values, 'kubernetes') as rendered_template_file:
            try:
                self._client.install_from_yaml(rendered_template_file, with_custom_objects=True)
                self._logger.info('Certificate successfully created!')
            except Exception as e:
                self._logger.exception(f"Failed to create certificate: {e}", exc_info=False)

    def install_csi(self, provider: str):
        path_to_template = template_loader.get_template(f'{provider}-csi.yaml', 'kubernetes')

        try:
            self._client.install_from_yaml(path_to_template)
            self._logger.info(f'{provider.capitalize()} CSI installed successfully!')
        except Exception as e:
            self._logger.exception(f"Failed to install {provider.capitalize()} CSI: {e}", exc_info=False)

    def install_cloud_controller(self, provider: str):
        path_to_template = template_loader.get_template(f'{provider}-cloud-controller.yaml', 'kubernetes')

        try:
            self._client.install_from_yaml(path_to_template)
            self._logger.info(f'{provider.capitalize()} Clod Controller installed successfully!')
        except Exception as e:
            self._logger.exception(f"Failed to install {provider.capitalize()} Cloud Controller: {e}", exc_info=False)

    def execute_command_on_pod(self, pod: str, namespace: str, command: list[str], interactive: bool = False, command_input: str = None):
        output, errors = self._client.execute_command(pod, namespace, command, interactive, command_input)

        return output

    def apply_file(self, path_to_template: Path, with_custom_objects: bool = False):
        if not path_to_template.exists():
            raise FileNotFoundError(f"File {path_to_template} does not exist")

        try:
            self._client.install_from_yaml(path_to_template, with_custom_objects)
            self._logger.info(f'Applied file {path_to_template} successfully!')
        except Exception as e:
            self._logger.exception(f"Failed to apply file {path_to_template}: {e}", exc_info=False)
            raise

    def create_object_from_content(self, yaml_content: dict | list[dict]):
        self._client.install_from_content(yaml_content)

    def create_secret(self, secret_name: str, namespace: str, data: dict[str, str], secret_type: str | None = None):
        self.create_namespace(namespace)

        if secret_type == 'docker-registry':
            self._client.create_docker_registry_secret(secret_name, data['url'], data['username'], data['password'], namespace)
        else:
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
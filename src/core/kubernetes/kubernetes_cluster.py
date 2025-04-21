from typing import Any

import yaml

from src.core.config import PATH_TO_K3S_YAML_CONFIGS
from src.core.providers.base_provider import BaseProvider
from src.core.kubernetes.configuration import ClusterConfiguration
from src.core.kubernetes.kubernetes_client import KubernetesClient
from pyhelm3 import Client
from pathlib import Path
from src.core.kubernetes.chart_config import HelmChart
from src.database.models.cluster import Cluster


class KubernetesCluster:
    def __init__(self, config: ClusterConfiguration, access_ip: str, kubeconfig_path: Path):
        self.config = config
        self.access_ip = access_ip
        self.kubeconfig_path = kubeconfig_path
        self._client = KubernetesClient(kubeconfig_path)
        self._helm_client = Client(kubeconfig=kubeconfig_path)

    def get_pods(self):
        pass

    async def install_chart(self, helm_chart: HelmChart, values: dict[str, Any] = None, namespace: str = None):
        values = values or {}
        namespace = namespace or helm_chart.name.lower()

        print(f"Installing {helm_chart.name}... with values: {values}")
        try:
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
            result = await self._helm_client.install_or_upgrade_release(
                helm_chart.name,
                chart,
                values,
                create_namespace=True,
                namespace=namespace.lower(),
            )
        except Exception as e:
            msg = f"Failed to install chart: {e}"
            print(msg)
            raise ValueError(msg)

        print(f"{helm_chart.name} installation complete: {result.status}")

        return True

    async def uninstall_chart(self, helm_chart: HelmChart, namespace: str = None):
        namespace = namespace or helm_chart.name.lower()
        print(f'Will uninstall chart {helm_chart.name}')
        await self._helm_client.uninstall_release(helm_chart, namespace=namespace)

        self._client.delete_namespace(namespace)
        print(f'Successfully uninstalled chart {helm_chart.name}')

    def expose_traefik_dashboard(self):
        path_to_template = Path(Path(__file__).parent.parent.absolute(), 'templates', 'kubernetes', 'traefik-dashboard-ingress-route.yaml')

        try:
            self._client.install_from_yaml(path_to_template, with_custom_objects=True)
            print('Traefik dashboard exposed successfully!')
        except Exception as e:
            print(f"Failed to expose traefik dashboard: {e}")

    def install_csi(self, csi_provider: str):
        path_to_template = Path(Path(__file__).parent.parent.absolute(), 'templates', 'kubernetes', f'{csi_provider}.yaml')

        try:
            self._client.install_from_yaml(path_to_template)
            print(f'CSI {csi_provider} installed successfully!')
        except Exception as e:
            print(f"Failed to install CSI {csi_provider}: {e}")

    def create_object_from_content(self, yaml_content: dict | list[dict]):
        self._client.install_from_content(yaml_content)

    def apply_files(self):
        pass

    @classmethod
    def from_db_model(cls, cluster: Cluster):
        return cls(
            ClusterConfiguration(cluster.name, cluster.pools),
            cluster.access_ip,
            cluster.kubeconfig_path
        )
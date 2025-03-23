from src.core.providers.base_provider import BaseProvider
from src.core.kubernetes.configuration import ClusterConfiguration
from src.core.kubernetes.kubernetes_client import KubernetesClient
from pyhelm3 import Client
from pathlib import Path
from src.core.kubernetes.chart_config import ChartConfig


class KubernetesCluster:
    def __init__(self, config: ClusterConfiguration, access_ip: str, kubeconfig_path: Path):
        self.config = config
        self.access_ip = access_ip
        self.kubeconfig_path = kubeconfig_path
        self._client = KubernetesClient(kubeconfig_path)
        self._helm_client = Client(kubeconfig=kubeconfig_path)

    def get_pods(self):
        pass

    async def install_chart(self, chart_config: ChartConfig, namespace: str):
        print(f"Installing {chart_config.name}...")
        chart = await self._helm_client.get_chart(
            chart_config.name,
            repo=chart_config.repo_url,
            version=chart_config.version
        )

        result = await self._helm_client.install_or_upgrade_release(
            chart_config.name,
            chart,
            chart_config.values,
            namespace=namespace,
        )

        print(f"{chart_config.name} installation complete: {result.status}")

    def install_traefik_dashboard(self):
        self._client.install_from_yaml(Path(Path(__file__).parent.parent.absolute(), 'templates', 'kubernetes', 'traefik-dashboard.yaml'))

    def apply_files(self):
        pass

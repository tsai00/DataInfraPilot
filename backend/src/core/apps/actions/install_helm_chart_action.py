from typing import override

from src.core.apps.actions.base_post_install_action import BasePrePostInstallAction
from src.core.kubernetes.chart_config import HelmChart
from src.core.kubernetes.kubernetes_cluster import KubernetesCluster


class InstallHelmChartAction(BasePrePostInstallAction):
    def __init__(
        self, name: str, helm_chart: HelmChart, chart_values: dict | None = None, condition: bool = True
    ) -> None:
        self.helm_chart = helm_chart
        self.chart_values = chart_values or {}

        super().__init__(name=name, condition=condition)

    @override
    async def run(self, cluster: KubernetesCluster, namespace: str, *args, **kwargs) -> None:
        await cluster.install_or_upgrade_chart(
            helm_chart=self.helm_chart, values=self.chart_values, namespace=namespace
        )

    def _validate(self) -> None:
        pass

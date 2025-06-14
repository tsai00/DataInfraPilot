from src.core.kubernetes.chart_config import HelmChart

cluster_autoscaler_chart = HelmChart(
    name='cluster-autoscaler',
    repo_url='https://kubernetes.github.io/autoscaler',
    version='9.46.6'
)

certmanager_chart = HelmChart(
    name='cert-manager',
    repo_url='https://charts.jetstack.io',
    version='v1.17.2'
)

longhorn_chart = HelmChart(
    name='longhorn',
    repo_url='https://charts.longhorn.io',
    version='1.8.1'
)


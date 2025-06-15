from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from src.core.apps.actions.apply_template_action import ApplyTemplateAction
from src.core.apps.actions.base_post_install_action import BasePrePostInstallAction
from src.core.apps.base_application import AccessEndpoint, AccessEndpointConfig, AccessEndpointType, BaseApplication
from src.core.kubernetes.chart_config import HelmChart


class SparkConfig(BaseModel):
    version: str = '3.5.0'
    cluster_name: str
    min_workers: int = Field(default=1, ge=1, description='Minimum number of worker nodes')
    max_workers: int = Field(default=3, ge=2, description='Maximum number of worker nodes')


class SparkApplication(BaseApplication):
    _helm_chart = HelmChart(
        name='spark-kubernetes-operator',
        repo_url='https://apache.github.io/spark-kubernetes-operator',
        version='1.0.0',
    )

    credentials_secret_name = ''

    def __init__(self, config: SparkConfig) -> None:
        self._config = config

        super().__init__('Spark')

    @classmethod
    @lru_cache
    def get_available_versions(cls) -> list[str]:
        # TODO: replace with actual version list + move to base class
        return ['3.5.1']

    @classmethod
    def get_accessible_endpoints(cls) -> list[AccessEndpoint]:
        return [
            AccessEndpoint(
                name='web-ui',
                description='Spark Web UI',
                default_access=AccessEndpointType.CLUSTER_IP_PATH,
                default_value='/spark',
                required=True,
            )
        ]

    def _generate_endpoint_helm_values(
        self, endpoint_config: AccessEndpointConfig, cluster_base_ip: str, namespace: str
    ) -> dict[str, Any]:
        pass

    def get_ingress_helm_values(
        self, access_endpoint_configs: list[AccessEndpointConfig], cluster_base_ip: str, namespace: str
    ) -> dict[str, Any]:
        web_ui_access_endpoint = next(iter([x for x in access_endpoint_configs if x.name == 'web-ui']))

        return {'web_ui_path': web_ui_access_endpoint.value}

    @classmethod
    def get_resource_values(cls) -> dict:
        pass

    @classmethod
    def get_volume_requirements(cls) -> list:
        return []

    @property
    def chart_values(self) -> dict[str, Any]:
        return {}

    @property
    def post_installation_actions(self) -> list[BasePrePostInstallAction]:
        return [
            ApplyTemplateAction(
                name='CreateSparkCluster',
                template_name='spark-cluster.yaml',
                template_module='kubernetes',
                with_custom_objects=True,
            ),
            ApplyTemplateAction(
                name='CreateSparkStripPrefixMiddleware',
                template_name='traefik-spark-strip-prefix-middleware.yaml',
                template_module='kubernetes',
                with_custom_objects=True,
            ),
            ApplyTemplateAction(
                name='CreateSparkIngress',
                template_name='spark-ingress.yaml',
                template_module='kubernetes',
                with_custom_objects=True,
            ),
            ApplyTemplateAction(
                name='CreateSparkUIService',
                template_name='spark-master-svc.yaml',
                template_module='kubernetes',
                with_custom_objects=True,
            ),
        ]

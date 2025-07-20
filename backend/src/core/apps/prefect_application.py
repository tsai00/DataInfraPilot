from functools import lru_cache
from typing import Any

from pydantic import BaseModel
from src.core.apps.actions.base_post_install_action import BasePrePostInstallAction
from src.core.apps.actions.create_secret_action import CreateSecretAction
from src.core.apps.base_application import AccessEndpoint, AccessEndpointConfig, AccessEndpointType, BaseApplication
from src.core.kubernetes.chart_config import HelmChart
from src.core.utils import generate_password


class PrefectConfig(BaseModel):
    version: str = '3.4.8'


class PrefectApplication(BaseApplication):
    _helm_chart = HelmChart(
        name='prefect-server',
        repo_url='https://prefecthq.github.io/prefect-helm',
        version='2025.7.10174756',
    )

    credentials_secret_name = 'prefect-creds'  # noqa: S105 (not a secret)

    def __init__(self, config: PrefectConfig) -> None:
        self._config = config

        self._base_url = None

        super().__init__('Prefect')

    @classmethod
    @lru_cache
    def get_available_versions(cls) -> list[str]:
        # TODO: replace with actual version list + move to base class
        return ['2.10.3']

    @classmethod
    def get_volume_requirements(cls) -> list:
        return []

    @classmethod
    def get_accessible_endpoints(cls) -> list[AccessEndpoint]:
        return [
            AccessEndpoint(
                name='web-ui',
                description='Prefect Web UI',
                default_access=AccessEndpointType.CLUSTER_IP_PATH,
                default_value='/prefect',
                required=True,
            )
        ]

    @classmethod
    def get_resource_values(cls) -> dict:
        return {}

    def get_ingress_helm_values(
        self, access_endpoint_configs: list[AccessEndpointConfig], cluster_base_ip: str, namespace: str
    ) -> dict[str, Any]:
        defined_endpoints = {ep.name: ep for ep in self.get_accessible_endpoints()}
        configured_map = {epc.name: epc for epc in access_endpoint_configs}

        # Validate that all required endpoints are configured
        for ep_name, accessible_ep in defined_endpoints.items():
            if accessible_ep.required and ep_name not in configured_map:
                raise ValueError(f"Required endpoint '{ep_name}' is not configured.")

        web_ui_access_endpoint = next(iter([x for x in access_endpoint_configs if x.name == 'web-ui']))

        web_ui_config = self._generate_endpoint_helm_values(web_ui_access_endpoint, cluster_base_ip, namespace)

        use_https = web_ui_access_endpoint.access_type in (AccessEndpointType.SUBDOMAIN, AccessEndpointType.DOMAIN_PATH)

        common_annotations = {
            'traefik.ingress.kubernetes.io/router.entrypoints': 'websecure' if use_https else 'web',
            'traefik.ingress.kubernetes.io/router.priority': '10',
            'cert-manager.io/cluster-issuer': 'acme-prod',
            #'traefik.ingress.kubernetes.io/router.middlewares': 'prefect-server-3-strip-prefix-prefect@kubernetescrd'
        }

        self._base_url = f'{web_ui_config["base_url"]}/api'

        return {
            # 'global': {
            #     # 'prefect': {
            #     #     # 'image': {
            #     #     #     'prefectTag': self._config.version,
            #     #     # },
            #     #     #'prefectApiUrl': self._base_url
            #     # },
            #     # 'env': [
            #     #     {'name': 'PREFECT_SERVER_API_BASE_PATH', 'value': f'{web_ui_access_endpoint.value}/api'},
            #     #     # {'name': 'PREFECT_UI_API_URL', 'value': 'http://0.0.0.0:4200/prefect'},
            #     #     # {'name': 'PREFECT_API_URL', 'value': 'http://0.0.0.0:4200/prefect/api'},
            #     #     # {'name': 'PREFECT_UI_SERVE_BASE', 'value': '/prefect'},
            #     #     # {'name': 'BASE_PATH', 'value': '/prefect'},
            #     # ]
            # },
            'server': {
                'apiBasePath': f'{web_ui_access_endpoint.value}',
                'uiConfig': {'prefectUiApiUrl': f'{web_ui_access_endpoint.value}/api'},
            },
            'ingress': {
                'enabled': True,
                'className': 'traefik',
                'annotations': common_annotations,
                'tls': False,
                'host': {
                    'hostname': ''
                    if web_ui_access_endpoint.access_type == AccessEndpointType.CLUSTER_IP_PATH
                    else web_ui_config['base_url'],
                    'pathType': 'Prefix',
                    'path': web_ui_config['path'],
                },
                'extraRules': [
                    {
                        'http': {
                            'paths': [
                                {
                                    'path': web_ui_config['path'],
                                    'pathType': 'Prefix',
                                    'backend': {
                                        'service': {'name': 'prefect-server', 'port': {'name': 'server-svc-port'}}
                                    },
                                }
                            ]
                        },
                    }
                ],
            },
        }

    def _generate_endpoint_helm_values(
        self, endpoint_config: AccessEndpointConfig, cluster_base_ip: str, namespace: str
    ) -> dict[str, Any]:
        self._validate_access_config(endpoint_config)

        if endpoint_config.access_type == AccessEndpointType.SUBDOMAIN:
            path_value = '/'
            hosts = [
                {
                    'name': endpoint_config.value,
                    'tls': {'enabled': True, 'secretName': f'{endpoint_config.value}-tls'},
                }
            ]
            base_url = f'https://{endpoint_config.value}'
        elif endpoint_config.access_type == AccessEndpointType.DOMAIN_PATH:
            path_value = endpoint_config.value[endpoint_config.value.find('/') :]
            hosts = [
                {
                    'name': endpoint_config.value[: endpoint_config.value.find('/')],
                    'tls': {'enabled': True, 'secretName': f'{endpoint_config.value}-tls'},
                }
            ]
            base_url = f'https://{endpoint_config.value}'
        elif endpoint_config.access_type == AccessEndpointType.CLUSTER_IP_PATH:
            path_value = endpoint_config.value
            hosts = []
            base_url = f'http://{cluster_base_ip}{path_value}'
        else:
            raise ValueError(f'Unsupported access type: {endpoint_config.access_type}')

        return {'path': path_value, 'hosts': hosts, 'base_url': base_url}

    @property
    def chart_values(self) -> dict[str, Any]:
        values = {'server': {'basicAuth': {'enabled': True, 'existingSecret': self.credentials_secret_name}}}

        return values

    @property
    def pre_installation_actions(self) -> list[BasePrePostInstallAction]:
        return [
            CreateSecretAction(
                name='CreatePrefectCredentialsSecret',
                secret_name=self.credentials_secret_name,
                secret_data={'auth-string': f'admin:{generate_password(10)}'},
                secret_type='regular',  # noqa: S106 (not a secret)
            ),
            # ApplyTemplateAction(
            #     name='CreateTraefikPrefectStripPrefixMiddleware',
            #     template_name='traefik-strip-prefix-middleware.yaml',
            #     template_module='kubernetes',
            #     values={'prefix': 'prefect'},
            #     with_custom_objects=True,
            # )
        ]

    # @property
    # def post_installation_actions(self) -> list[BasePrePostInstallAction]:
    #     helm_chart = HelmChart(
    #         name='prefect-worker',
    #         repo_url='https://prefecthq.github.io/prefect-helm',
    #         version='2025.2.19212245',
    #     )
    #
    #     print('READ API URL AS ', self._base_url)
    #
    #
    #     values = {
    #         'worker': {
    #             'apiConfig': 'selfHostedServer',
    #             'config': {
    #                 'workPool': 'default-pool'
    #             },
    #             'serverApiConfig': {
    #                 'apiUrl': self._base_url,
    #                 'uiUrl': self._base_url.replace('/api', '')
    #             }
    #         }
    #     }
    #
    #     return [
    #         InstallHelmChartAction(
    #             name='InstallPrefectWorkerChart',
    #             helm_chart=helm_chart,
    #             chart_values=values
    #         )
    #     ]

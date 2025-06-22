from functools import lru_cache
from typing import Any

from pydantic import BaseModel
from src.core.apps.base_application import AccessEndpoint, AccessEndpointConfig, AccessEndpointType, BaseApplication
from src.core.kubernetes.chart_config import HelmChart


class GrafanaConfig(BaseModel):
    version: str = '11.6'


class GrafanaApplication(BaseApplication):
    _helm_chart = HelmChart(
        name='grafana',
        repo_url='https://grafana.github.io/helm-charts',
        version='8.12.1',
    )

    credentials_secret_name = 'grafana'  # noqa: S105 (not a secret)

    def __init__(self, config: GrafanaConfig) -> None:
        self._config = config

        super().__init__('Grafana')

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
                description='Grafana Web UI',
                default_access=AccessEndpointType.CLUSTER_IP_PATH,
                default_value='/grafana',
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
        }

        helm_ingress_hosts = []
        helm_ingress_tls = []

        if web_ui_config['hosts']:
            host_entry = web_ui_config['hosts'][0]
            hostname = host_entry['name']

            helm_ingress_hosts.append(hostname)

            if host_entry.get('tls', {}).get('enabled'):
                secret_name = host_entry['tls']['secretName']
                helm_ingress_tls.append({'hosts': [hostname], 'secretName': secret_name})
        return {
            'ingress': {
                'enabled': True,
                'ingressClassName': 'traefik',
                'pathType': 'Prefix',
                'annotations': common_annotations,
                'path': web_ui_config['path'],
                'hosts': helm_ingress_hosts,
                'tls': helm_ingress_tls,
            },
            'grafana.ini': {'server': {'root_url': web_ui_config['base_url'], 'serve_from_sub_path': True}},
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
                    'tls': {'enabled': True, 'secretName': f'{namespace}-{endpoint_config.name}-tls'},
                }
            ]
            base_url = f'https://{endpoint_config.value}'
        elif endpoint_config.access_type == AccessEndpointType.DOMAIN_PATH:
            path_value = endpoint_config.value[endpoint_config.value.find('/') :]
            hosts = [
                {
                    'name': endpoint_config.value[: endpoint_config.value.find('/')],
                    'tls': {'enabled': True, 'secretName': f'{namespace}-{endpoint_config.name}-tls'},
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
        values = {
            'persistence': {
                'enabled': True,
                'type': 'pvc',
                'accessModes': ['ReadWriteOnce'],
                'size': '10Gi',
                'storageClassName': 'hcloud-volumes',
            },
            'rbac': {
                'namespaced': True  # allows deploying multiple instances on one cluster
            },
        }

        return values

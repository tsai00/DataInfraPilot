from functools import lru_cache
from typing import Any

from pydantic import BaseModel
from src.core.apps.base_application import AccessEndpoint, AccessEndpointConfig, AccessEndpointType, BaseApplication
from src.core.kubernetes.chart_config import HelmChart


class SupersetConfig(BaseModel):
    version: str = '4.1.3'


class SupersetApplication(BaseApplication):
    _helm_chart = HelmChart(
        name='superset',
        repo_url='http://apache.github.io/superset/',
        version='0.14.2',
    )

    credentials_secret_name = 'superset'  # noqa: S105 (not a secret)

    def __init__(self, config: SupersetConfig) -> None:
        self._config = config

        super().__init__('Superset')

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
                description='Superset Web UI',
                default_access=AccessEndpointType.CLUSTER_IP_PATH,
                default_value='/superset',
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
                'extraHostsRaw': [
                    {
                        'http': {
                            'paths': [
                                {
                                    'path': web_ui_config['path'],
                                    'pathType': 'Prefix',
                                    'backend': {'service': {'name': 'superset', 'port': {'name': 'http'}}},
                                }
                            ]
                        }
                    }
                ],
            }
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
            'image': {
                'tag': self._config.version,
            },
            'extraSecretEnv': {'SUPERSET_SECRET_KEY': 'hyfSKeVsfW40F2+kU+bhodC3p8JSzuHcU4adic00vh+607Sbndjeq8qH'},
            'bootstrapScript': """
              #!/bin/bash
              
              # Install system-level dependencies
              apt-get update && apt-get install -y \
                python3-dev \
                default-libmysqlclient-dev \
                build-essential \
                pkg-config
            
              # Install required Python packages
              pip install \
                authlib \
                psycopg2-binary \
                mysqlclient \
            
              # Create bootstrap file if it doesn't exist
              if [ ! -f ~/bootstrap ]; then
                echo "Running Superset with uid {{ .Values.runAsUser }}" > ~/bootstrap
              fi
            """,  # noqa: W293
        }

        return values

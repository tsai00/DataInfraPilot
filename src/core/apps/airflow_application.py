from typing import Any

from src.core.apps.actions.base_post_install_action import BasePrePostInstallAction
from src.core.apps.actions.create_secret_action import CreateSecretAction
from src.core.apps.base_application import BaseApplication, VolumeRequirement, AccessEndpoint, AccessEndpointType, AccessEndpointConfig
from src.core.kubernetes.chart_config import HelmChart
from pydantic import BaseModel, Field
from enum import StrEnum
import requests
import re
import base64
from functools import lru_cache


class AirflowExecutor(StrEnum):
    CeleryExecutor = 'CeleryExecutor'
    LocalExecutor = 'LocalExecutor'
    KubernetesExecutor = 'KubernetesExecutor'
    CeleryKubernetesExecutor = 'CeleryKubernetesExecutor'


class AirflowConfig(BaseModel):
    version: str = Field(pattern=r"^\d\.\d{1,2}\.\d$")
    node_selector: dict | None = Field(default=None)
    dags_repository: str = Field(pattern=r"^https:\/\/.{10,}\.git$")
    dags_repository_ssh_private_key: str = Field(default=None, alias='dagsRepositorySshPrivateKey')
    dags_repository_branch: str = Field(default='main', alias='dagsRepositoryBranch')
    dags_repository_subpath: str = Field(default='dags', alias='dagsRepositorySubpath')
    executor: AirflowExecutor = AirflowExecutor.CeleryExecutor
    flower_enabled: bool = False
    pgbouncer_enabled: bool = False
    instance_name: str = Field(max_length=20)


class AirflowApplication(BaseApplication):
    _helm_chart = HelmChart(
        name="airflow",
        repo_url="https://airflow.apache.org",
        version="1.15.0",
    )

    def __init__(self, config: AirflowConfig):
        self._config = config
        self._version = self._config.version

        super().__init__("Airflow")

    @classmethod
    def get_volume_requirements(cls) -> list[VolumeRequirement]:
        return [
            VolumeRequirement(name='airflow-logs', size=100, description='Persistent storage for Airflow logs')
        ]

    def validate_volume_requirements(self):
        pass

    def get_initial_credentials(self) -> dict[str, str]:
        return {'username': 'admin', 'password': 'admin'}

    @classmethod
    def get_accessible_endpoints(cls) -> list[AccessEndpoint]:
        return [
            AccessEndpoint(
                name="web-ui",
                description="Airflow Web UI",
                default_access=AccessEndpointType.CLUSTER_IP_PATH,
                default_value="/airflow",
                required=True,
            ),
            AccessEndpoint(
                name="flower-ui",
                description="Airflow Flower UI",
                default_access=AccessEndpointType.CLUSTER_IP_PATH,
                default_value="/flower",
                required=False,
            )
        ]

    def get_ingress_helm_values(self, access_endpoint_configs: list[AccessEndpointConfig], cluster_base_ip: str, namespace: str) -> dict[str, Any]:
        defined_endpoints = {ep.name: ep for ep in self.get_accessible_endpoints()}
        configured_map = {epc.name: epc for epc in access_endpoint_configs}

        # Validate that all required endpoints are configured
        for ep_name, accessible_ep in defined_endpoints.items():
            if accessible_ep.required and ep_name not in configured_map:
                raise ValueError(f"Required endpoint '{ep_name}' is not configured.")

        common_annotations = {
            "traefik.ingress.kubernetes.io/router.entrypoints": "web",
            "traefik.ingress.kubernetes.io/router.priority": "10"
        }

        web_ui_access_endpoint = [x for x in access_endpoint_configs if x.name == "web-ui"][0]
        flower_ui_access_endpoint = [x for x in access_endpoint_configs if x.name == "flower-ui"]

        if flower_ui_access_endpoint:
            flower_ui_access_endpoint = flower_ui_access_endpoint[0]

        web_ui_config = self._generate_endpoint_helm_values(web_ui_access_endpoint, cluster_base_ip, namespace)
        flower_ui_config = self._generate_endpoint_helm_values(flower_ui_access_endpoint, cluster_base_ip, namespace)

        return {
            "config": {
                "webserver": {
                    "base_url": web_ui_config['base_url']
                }
            },
            "ingress": {
                "web": {
                    "enabled": True,
                    "ingressClassName": 'traefik',
                    "pathType": 'Prefix',
                    "annotations": common_annotations,
                    "path": web_ui_config['path'],
                    "hosts": web_ui_config['hosts']
                },
                "flower": {
                    "enabled": True if flower_ui_access_endpoint else False,
                    "ingressClassName": 'traefik',
                    "pathType": 'Prefix',
                    "annotations": common_annotations,
                    "path": flower_ui_config['path'],
                    "hosts": flower_ui_config['hosts']
                }
            }
        }

    def _generate_endpoint_helm_values(self, endpoint_config: AccessEndpointConfig, cluster_base_ip: str, namespace: str) -> dict[str, Any]:
        self._validate_access_config(endpoint_config)

        if endpoint_config.access_type == AccessEndpointType.SUBDOMAIN:
            path_value = "/"

            hosts = [
                {'name': endpoint_config.value, 'tls': {'enabled': True, 'secretName': f'{namespace}-{endpoint_config.name}-tls'}}]

            base_url = f'http://{endpoint_config.value}'
        elif endpoint_config.access_type == AccessEndpointType.DOMAIN_PATH:
            path_value = endpoint_config.value[endpoint_config.value.find('/'):]

            hosts = [{'name': endpoint_config.value[:endpoint_config.value.find('/')],
                      'tls': {'enabled': True, 'secretName': f'{namespace}-{endpoint_config.name}-tls'}}]

            base_url = f'http://{endpoint_config.value}'
        elif endpoint_config.access_type == AccessEndpointType.CLUSTER_IP_PATH:
            path_value = endpoint_config.value

            hosts = []

            base_url = f'http://{cluster_base_ip}:8080{endpoint_config.value}'
        else:
            raise ValueError(f"Unsupported access type: {endpoint_config.access_type}")

        return value_copy


    @classmethod
    @lru_cache()
    def get_available_versions(cls) -> list[str]:
        try:
            r = requests.get('https://api.github.com/repos/apache/airflow/releases').json()
        except Exception as e:
            print(f'Failed to retrieve availble verions for Airflow: {e}')
            raise
        return [x['tag_name'] for x in r if bool(re.search(r"^\d\.\d{1,2}\.\d$", x['tag_name']))][:5]

    def __post_init__(self):
        if self._version not in self.get_available_versions():
            raise ValueError

    @property
    def chart_values(self) -> dict[str, Any]:
        dags_repository_ssh_key_base64 = base64.b64encode(self._config.dags_repository_ssh_private_key.encode()).decode()

        values = {
            "airflowVersion": self._version,
            "defaultAirflowTag": self._version,
            "executor": self._config.executor,
            "flower": {
                "enabled": self._config.flower_enabled
            },
            "config": {
                "webserver": {
                    #"expose_config": True,
                    #"navbar_color": '#000',
                    "require_confirmation_dag_change": True,
                    "instance_name": self._config.instance_name,
                    "default_ui_timezone": 'Europe/Prague'
                },
                "core": {
                    "max_active_runs_per_dag": 1,
                    "dags_are_paused_at_creation": True,
                    "load_examples": False
                },
                "scheduler": {
                    "enable_health_check": False,
                    "catchup_by_default": False
                }
            },
            "pgbouncer": {
                "enabled": self._config.pgbouncer_enabled
            },
            "dags": {
                "gitSync": {
                    "enabled": True,
                    "repo": self._config.dags_repository,
                    "branch": self._config.dags_repository_branch,
                    "rev": "HEAD",
                    "depth": 1,
                    "maxFailures": 1,
                    "subPath": self._config.dags_repository_subpath,
                    #"sshKeySecret": "airflow-ssh-secret" if self._config.dags_repository_ssh_private_key is not None else None
                }
            },
            "logs": {
                "persistence": {
                    "enabled": True,
                    "size": "10Gi",
                    "storageClassName": "longhorn",
                }
            },
            "nodeSelector": self._config.node_selector
            # "extraSecrets": f"""
            # 'airflow-ssh-secret':
            #     type: 'Opaque'
            #     data: |
            #       gitSshKey: '{dags_repository_ssh_key_base64}'
            # """
        }

        return values

    @property
    def pre_installation_actions(self) -> list[BasePrePostInstallAction]:
        return [
            CreateSecretAction(
                name="CreatePrivateRegistryCredentialsSecret",
                secret_name="private-registry-creds",
                secret_data={
                    "url": self._config.private_registry_url[:self._config.private_registry_url.index('/', 8)],
                    "username": self._config.private_registry_username,
                    "password": self._config.private_registry_password
                },
                secret_type='docker-registry',
                condition=self._config.use_custom_image
            )
        ]


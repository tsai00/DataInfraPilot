from typing import Any

from src.api.schemas.deployment import EndpointAccessConfig
from src.core.apps.base_application import BaseApplication, VolumeRequirement, AccessEndpoint
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


class AirflowConfig(BaseModel):
    version: str = Field(pattern=r"^\d\.\d{1,2}\.\d$")
    webserver_hostname: str
    node_selector: dict | None = Field(default=None)
    dags_repository: str = Field(pattern=r"^https:\/\/.{10,}\.git$")
    dags_repository_ssh_private_key: str = Field(default=None, alias='dagsRepositorySshPrivateKey')
    dags_repository_branch: str = Field(default='main', alias='dagsRepositoryBranch')
    dags_repository_subpath: str = Field(default='dags', alias='dagsRepositorySubpath')
    traefik_webserver_path: str = Field(pattern=r"^\/[a-z0-9]+$", default='/airflow')
    traefik_flower_path: str = '/airflow/flower'
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
                default_access="subdomain",
                default_value="airflow",
                required=True
            ),
            AccessEndpoint(
                name="flower-ui",
                description="Airflow Flower UI",
                default_access="domain_path",
                default_value="/flower",
                required=False
            ),
        ]

    def set_endpoints(self, values: dict, endpoints: list[EndpointAccessConfig]) -> dict:
        value_copy = values.copy()
        default_endpoints = self.get_accessible_endpoints()

        new_endpoints_names = [x.name for x in endpoints]
        default_endpoints_names = [x.name for x in default_endpoints]

        for endpoint in endpoints:
            if endpoint.name == 'web-ui':
                if endpoint.access_type == 'subdomain':
                    path_value = "/"
                    hosts = [endpoint.value]
                    base_url = f'http://{endpoint.value}'
                elif endpoint.access_type == 'domain_path':
                    path_value = endpoint.value[endpoint.value.find('/'):]
                    hosts = [endpoint.value[:endpoint.value.find('/')]]
                    base_url = f'http://{endpoint.value}'
                elif endpoint.access_type == 'ip':
                    path_value = endpoint.value
                    hosts = []
                    base_url = f'http://{self._config.webserver_hostname}:8080{endpoint.value}'
                else:
                    raise ValueError('Wrong access type')

                value_copy['ingress']['web']['path'] = path_value
                value_copy['ingress']['web']['hosts'] = hosts
                values['config']['webserver']['base_url'] = base_url

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
                    "base_url": f'http://{self._config.webserver_hostname}:8080{self._config.traefik_webserver_path}',
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
            "ingress": {
                "web": {
                    "enabled": True,
                    "ingressClassName": 'traefik',
                    "pathType": 'Prefix',
                    "annotations": {
                        "traefik.ingress.kubernetes.io/router.entrypoints": "web",
                        "traefik.ingress.kubernetes.io/router.priority": "10"
                    },
                    "path": self._config.traefik_webserver_path
                },
                "flower": {
                    "enabled": True,
                    "ingressClassName": 'traefik',
                    "pathType": 'Prefix',
                    "annotations": {
                        "traefik.ingress.kubernetes.io/router.entrypoints": "web",
                        "traefik.ingress.kubernetes.io/router.priority": "10"
                    },
                    "path": self._config.traefik_flower_path
                }
            },
            "pgbouncer": {
                "enabled": self._config.pgbouncer_enabled
            },
            "webserver": {
                "startupProbe": {
                    "timeoutSeconds": 360,
                    "failureThreshold": 15,
                    "periodSeconds": 15
                }
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



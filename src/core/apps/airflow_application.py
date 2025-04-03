from typing import Any

from src.core.apps.base_application import BaseApplication
from src.core.kubernetes.chart_config import HelmChart
from pydantic import BaseModel, Field
from enum import StrEnum
from cachetools import cached


class AirflowExecutor(StrEnum):
    CeleryExecutor = 'CeleryExecutor'
    LocalExecutor = 'LocalExecutor'


class AirflowConfig(BaseModel):
    version: str
    webserver_hostname: str
    traefik_webserver_path: str = '/airflow'
    traefik_flower_path: str = '/airflow/flower'
    executor: AirflowExecutor = AirflowExecutor.CeleryExecutor
    load_examples: bool = True
    flower_enabled: bool = False
    pgbouncer_enabled: bool = False
    instance_name: str = Field(max_length=20)


class AirflowApplication(BaseApplication):
    def __init__(self, config: AirflowConfig):
        self._config = config
        self._version = self._config.version

        helm_chart = HelmChart(
            name="airflow",
            repo_url="https://airflow.apache.org",
            version="1.15.0",
        )

        super().__init__("Airflow", helm_chart)

    @classmethod
    @cached
    def get_available_versions(cls) -> list[str]:
        # TODO: replace with actual version list + move to base class
        return ['2.10.3']

    def __post_init__(self):
        if self._version not in self.get_available_versions():
            raise ValueError

    @property
    def chart_values(self) -> dict[str, Any]:
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
                    "expose_config": True,
                    "navbar_color": '#000',
                    "require_confirmation_dag_change": True,
                    "instance_name": self._config.instance_name,
                    "default_ui_timezone": 'Europe/Prague'
                },
                "core": {
                    "max_active_runs_per_dag": 1,
                    "dags_are_paused_at_creation": True,
                    "load_examples": self._config.load_examples
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
                    "path": f'{self._config.traefik_webserver_path}'
                },
                "flower": {
                    "enabled": True,
                    "ingressClassName": 'traefik',
                    "pathType": 'Prefix',
                    "annotations": {
                        "traefik.ingress.kubernetes.io/router.entrypoints": "web",
                        "traefik.ingress.kubernetes.io/router.priority": "10"
                    },
                    "path": f'{self._config.traefik_flower_path}'
                }
            },
            "pgbouncer": {
                "enabled": self._config.pgbouncer_enabled
            }
        }

        return values



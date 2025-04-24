from typing import Any

from src.core.apps.base_application import BaseApplication
from src.core.kubernetes.chart_config import HelmChart
from pydantic import BaseModel, Field
from enum import StrEnum
from cachetools import cached


class GrafanaConfig(BaseModel):
    webserver_hostname: str
    version: str = '11.6'
    traefik_path: str = Field(pattern=r"^\/[a-z0-9]+$", default='/grafana')


class GrafanaApplication(BaseApplication):
    _helm_chart = HelmChart(
        name="grafana",
        repo_url="https://grafana.github.io/helm-charts",
        version="8.12.1",
    )

    def __init__(self, config: GrafanaConfig):
        self._config = config
        self._version = self._config.version

        super().__init__("Grafana")

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
            "persistence": {
                "enabled": True,
                "type": "pvc",
                "accessModes": ["ReadWriteOnce"],
                "size": "10Gi",
                "storageClassName": "hcloud-volumes"
            },
            "ingress": {
                "enabled": True,
                "ingressClassName": 'traefik',
                "pathType": 'Prefix',
                "annotations": {
                    "traefik.ingress.kubernetes.io/router.entrypoints": "web",
                    "traefik.ingress.kubernetes.io/router.priority": "10"
                },
                "path": self._config.traefik_path,
                "hosts": []
            },
            "grafana.ini": {
                "server": {
                    "root_url": f"http://{self._config.webserver_hostname}{self._config.traefik_path}",
                    "serve_from_sub_path": True
                }
            }
        }

        return values



from functools import lru_cache
from typing import Any

from src.core.apps.base_application import BaseApplication
from src.core.kubernetes.chart_config import HelmChart
from pydantic import BaseModel, Field


class HashicorpVaultConfig(BaseModel):
    webserver_hostname: str
    version: str = '11.6'
    traefik_path: str = Field(pattern=r"^\/[a-z0-9]+$", default='/vault')


class HashicorpVaultApplication(BaseApplication):
    _helm_chart = HelmChart(
        name="vault",
        repo_url="https://helm.releases.hashicorp.com",
        version="0.30.0",
    )

    def __init__(self, config: HashicorpVaultConfig):
        self._config = config
        self._version = self._config.version

        super().__init__("HashicorpVault")

    @classmethod
    @lru_cache()
    def get_available_versions(cls) -> list[str]:
        return ["0.30.0"]

    @property
    def chart_values(self) -> dict[str, Any]:
        values = {
            "server": {
                "ingress": {
                    "enabled": True,
                    "ingressClassName": 'traefik',
                    "pathType": 'Prefix',
                    "annotations": {
                        "traefik.ingress.kubernetes.io/router.entrypoints": "web",
                        "traefik.ingress.kubernetes.io/router.priority": "10"
                    },
                    "hosts": [
                        {"host": "", "paths": ["/vault"]}
                    ]
                }
            },
            "ui": {
                "enabled": True
            }
        }

        return values
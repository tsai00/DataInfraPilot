from dataclasses import dataclass
from typing import Any, Literal

from src.api.schemas.deployment import EndpointAccessConfig
from src.core.kubernetes.chart_config import HelmChart
from abc import ABC, abstractmethod


@dataclass
class VolumeRequirement:
    name: str
    size: int   # in GB
    description: str


@dataclass
class AccessEndpoint:
    name: str
    description: str
    default_access: Literal["subdomain", "domain_path", "cluster_ip_path"]
    default_value: str
    required: bool = True


class BaseApplication(ABC):
    # TODO: refactor to either expose app config or make application instance config-idepedenent and load config in separate method

    _helm_chart: HelmChart

    def __init__(self, name: str):
        self.name = name

    @classmethod
    def get_helm_chart(cls) -> HelmChart:
        return cls._helm_chart

    @property
    @abstractmethod
    def chart_values(self) -> dict[str, Any]: ...

    @classmethod
    @abstractmethod
    def get_available_versions(cls) -> list[str]: ...

    @abstractmethod
    def get_volume_requirements(self) -> list: ...

    def set_endpoints(self, values: dict, endpoints: list[EndpointAccessConfig]) -> dict: ...

    def validate_volume_requirements(self, volume_requirements: list) -> None: ...

    def get_initial_credentials(self) -> dict[str, str]: ...
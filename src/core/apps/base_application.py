from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from src.core.apps.actions.base_post_install_action import BasePrePostInstallAction
from src.core.kubernetes.chart_config import HelmChart
from abc import ABC, abstractmethod
from enum import StrEnum


if TYPE_CHECKING:
    from src.core.kubernetes.kubernetes_cluster import KubernetesCluster


@dataclass
class VolumeRequirement:
    name: str
    size: int   # in GB
    description: str


class AccessEndpointType(StrEnum):
    SUBDOMAIN = "subdomain"
    DOMAIN_PATH = "domain_path"
    CLUSTER_IP_PATH = "cluster_ip_path"


@dataclass(frozen=True)
class AccessEndpoint:
    # e.g., "web-ui", "flower-ui"
    name: str
    # User-friendly description
    description: str
    # Default choice for FE
    default_access: AccessEndpointType
    # Default path/subdomain for FE
    default_value: str
    # Is this endpoint mandatory to expose?
    required: bool


@dataclass(frozen=True)
class AccessEndpointConfig:
    name: str
    access_type: AccessEndpointType
    value: str

    def to_dict(self):
        return {
            "name": self.name,
            "access_type": self.access_type,
            "value": self.value
        }


class BaseApplication(ABC):
    # TODO: refactor to either expose app config or make application instance config-idepedenent and load config in separate method

    _helm_chart: HelmChart

    credentials_secret_name: str

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

    def get_volume_requirements(self) -> list: ...

    @classmethod
    @abstractmethod
    def get_accessible_endpoints(cls) -> list[AccessEndpoint]:
        pass

    @abstractmethod
    def _generate_endpoint_helm_values(self, endpoint_config: AccessEndpointConfig, cluster_base_ip: str, namespace: str) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_ingress_helm_values(self, access_endpoint_configs: list[AccessEndpointConfig], cluster_base_ip: str, namespace: str) -> dict[str, Any]:
        pass

    def _deep_merge_dicts(self, dict1: dict, dict2: dict):
        for k, v in dict2.items():
            if k in dict1 and isinstance(dict1[k], dict) and isinstance(v, dict):
                self._deep_merge_dicts(dict1[k], v)
            else:
                dict1[k] = v

    @staticmethod
    def _validate_access_config(endpoint_config: AccessEndpointConfig):
        if endpoint_config.access_type == AccessEndpointType.SUBDOMAIN:
            if not re.match(r"^[a-zA-Z0-9.-]+$",
                            endpoint_config.value) or "--" in endpoint_config.value:
                raise ValueError(f"Invalid subdomain format for {endpoint_config.name}: {endpoint_config.value}")
        elif endpoint_config.access_type == AccessEndpointType.DOMAIN_PATH:
            if '/' not in endpoint_config.value:
                raise ValueError(
                    f"Domain path for {endpoint_config.name} must include a domain (e.g., mydomain.com/path).")
        elif endpoint_config.access_type == AccessEndpointType.CLUSTER_IP_PATH:
            if not endpoint_config.value.startswith('/'):
                raise ValueError(f"Cluster IP path for {endpoint_config.name} must start with '/'.")

    def validate_volume_requirements(self, volume_requirements: list) -> None: ...

    @classmethod
    @abstractmethod
    def get_resource_values(cls) -> dict:
        pass

    @property
    def pre_installation_actions(self) -> list[BasePrePostInstallAction]:
        return []

    @property
    def post_installation_actions(self) -> list[BasePrePostInstallAction]:
        return []

    def run_pre_install_actions(self, cluster: KubernetesCluster, namespace: str, config_values: dict[str, Any]) -> None:
        for action in self.pre_installation_actions:
            if not action.condition:
                print(f'Skipping pre-install action: {action.name} as its condition is not met')
            else:
                print(f'Running pre-install action: {action.name}')
                action.run(cluster, namespace, config_values)

    def run_post_install_actions(self, cluster: KubernetesCluster, namespace: str, config_values: dict[str, Any]) -> None:
        for action in self.post_installation_actions:
            if not action.condition:
                print(f'Skipping post-install action: {action.name} as its condition is not met')
            else:
                print(f'Running post-install action: {action.name}')
                action.run(cluster, namespace, config_values)

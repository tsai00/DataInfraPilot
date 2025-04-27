from __future__ import annotations

from abc import abstractmethod, ABC
from src.core.kubernetes.configuration import ClusterConfiguration

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.core.kubernetes.kubernetes_cluster import KubernetesCluster

class BaseProvider(ABC):
    name: str

    def __init__(self):
        # logger
        pass

    @abstractmethod
    def create_cluster(self, cluster_config: ClusterConfiguration) -> KubernetesCluster:
        pass

    @abstractmethod
    def create_volume(self, name: str, size: int, region: str) -> Any:
        pass

    @abstractmethod
    def delete_cluster(self):
        pass

    @abstractmethod
    def delete_volume(self, volume_name: str):
        pass

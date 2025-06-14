from __future__ import annotations

from abc import abstractmethod, ABC
from src.core.kubernetes.configuration import ClusterConfiguration

from typing import TYPE_CHECKING, Any

from src.core.utils import setup_logger

if TYPE_CHECKING:
    from src.core.kubernetes.kubernetes_cluster import KubernetesCluster


class BaseProvider(ABC):
    name: str

    def __init__(self):
        self._logger = setup_logger(self.name.capitalize())

    @abstractmethod
    def create_cluster(self, cluster_config: ClusterConfiguration) -> KubernetesCluster:
        pass

    @abstractmethod
    def create_volume(self, name: str, size: int, region: str | None = None) -> Any:
        pass

    @abstractmethod
    def delete_cluster(self):
        pass

    @abstractmethod
    def delete_volume(self, volume_name: str):
        pass

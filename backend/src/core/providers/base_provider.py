from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from src.core.utils import setup_logger

if TYPE_CHECKING:
    from src.core.kubernetes import ClusterConfiguration, KubernetesCluster


class BaseProvider(ABC):
    name: str

    def __init__(self) -> None:
        self._logger = setup_logger(self.name.capitalize())

    @abstractmethod
    async def create_cluster(self, cluster_config: ClusterConfiguration) -> KubernetesCluster:
        pass

    @abstractmethod
    async def create_volume(self, name: str, size: int, region: str | None = None) -> Any:  # noqa: ANN401 (volume type is provider-specific for now)
        pass

    @abstractmethod
    def delete_cluster(self) -> None:
        pass

    @abstractmethod
    def delete_volume(self, volume_name: str) -> None:
        pass

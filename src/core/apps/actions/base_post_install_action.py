from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.core.kubernetes.kubernetes_cluster import KubernetesCluster


class BasePrePostInstallAction(ABC):
    def __init__(self, name: str, condition: bool):
        self.name = name
        self.condition = condition

        self._validate()

    @abstractmethod
    def run(self, cluster: KubernetesCluster, namespace: str, config_values: dict[str, Any]):
        pass

    @abstractmethod
    def _validate(self):
        pass

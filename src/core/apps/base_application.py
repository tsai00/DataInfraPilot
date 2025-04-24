from typing import Any

from src.core.kubernetes.chart_config import HelmChart
from abc import ABC, abstractmethod


class BaseApplication(ABC):
    _helm_chart: HelmChart

    def __init__(self, name: str):
        self.name = name

    @classmethod
    def get_helm_chart(self) -> HelmChart:
        return self._helm_chart

    @property
    @abstractmethod
    def chart_values(self) -> dict[str, Any]: ...

    @classmethod
    @abstractmethod
    def get_available_versions(cls) -> list[str]: ...

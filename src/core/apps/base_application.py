from typing import Any

from src.core.kubernetes.chart_config import HelmChart
from abc import ABC, abstractmethod


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

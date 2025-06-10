from abc import ABC, abstractmethod
from src.demo.utils import setup_logger
from typing import TypeVar, Generic

T = TypeVar("T")


class BaseStorage(ABC, Generic[T]):
    def __init__(self, name: str):
        self.name = name
        self._logger = setup_logger(name)

    @abstractmethod
    def upload_data(self, data: T, path: str, **kwargs) -> str:
        pass

    @abstractmethod
    def download_data(self, path: str, **kwargs) -> T:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass

    @abstractmethod
    def __enter__(self):
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Generic, TypeVar

from src.demo.utils import setup_logger

T = TypeVar('T')


class BaseStorage(ABC, Generic[T]):
    def __init__(self, name: str) -> None:
        self.name = name
        self._logger = setup_logger(name)

    @abstractmethod
    def upload_data(self, data: T, path: str) -> str:
        pass

    @abstractmethod
    def download_data(self, path: str) -> T:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass

    @abstractmethod
    def __enter__(self) -> 'BaseStorage':
        pass

    @abstractmethod
    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        pass

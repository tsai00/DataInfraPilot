from abc import ABC, abstractmethod

from src.database.models import Cluster


class BaseDatabaseHandler(ABC):
    @abstractmethod
    def create_cluster(self, cluster: Cluster) -> int:
        pass

    @abstractmethod
    def get_cluster(self, cluster_id: int) -> None:
        pass

    @abstractmethod
    def delete_cluster(self, cluster_id: int) -> None:
        pass

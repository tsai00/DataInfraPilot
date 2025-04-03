from abc import ABC, abstractmethod


class BaseDatabaseHandler(ABC):
    @abstractmethod
    def create_cluster(self, data):
        pass

    @abstractmethod
    def get_cluster(self, cluster_id):
        pass

    @abstractmethod
    def delete_cluster(self, cluster_id):
        pass
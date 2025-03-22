from abc import ABC, abstractmethod


class BaseDatabaseHandler(ABC):
    @abstractmethod
    def save_cluster(self, data):
        pass

    @abstractmethod
    def get_cluster(self, cluster_id):
        pass

    @abstractmethod
    def delete_cluster(self, cluster_id):
        pass
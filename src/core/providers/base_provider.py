from abc import abstractmethod, ABC
from src.core.kubernetes.configuration import ClusterConfiguration


class BaseProvider(ABC):
    name: str

    def __init__(self):
        # logger
        pass

    @abstractmethod
    def create_cluster(self, cluster_config: ClusterConfiguration):
        pass

    @abstractmethod
    def delete_cluster(self):
        pass

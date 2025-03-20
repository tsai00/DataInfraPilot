from src.core.kubernetes.kubernetes_cluster import KubernetesCluster
from src.core.providers.base_provider import BaseProvider
from src.core.kubernetes.configuration import ClusterConfiguration
from src.storage.app_storage import SQLiteStorage
from src.storage.models.cluster import Cluster
from pathlib import Path
from src.core.providers.provider_factory import ProviderFactory
from traceback import format_exc
from src.core.kubernetes.cluster_state import ClusterState

class ClusterManager(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

            cls.storage = SQLiteStorage()
            # logger
        return cls._instance

    def check_cluster_status(self):
        pass

    def create_cluster_entry(self, cluster_config: ClusterConfiguration):
        cluster = Cluster(
            name=cluster_config.name,
            provider="test",
            region="test",
            kubeconfig_path="",
            num_of_master_nodes=cluster_config.num_of_master_nodes,
            num_of_worker_nodes=cluster_config.num_of_worker_nodes,
            status=ClusterState.PROVISIONING
        )

        return self.storage.save_cluster(cluster)

    async def create_cluster(self, cluster_id: int, provider: BaseProvider, cluster_config: ClusterConfiguration):
        print(f'Will create cluster {cluster_config}')

        try:
            cluster = await provider.create_cluster(cluster_config)

            await self.update_cluster(cluster_id, {"status": ClusterState.RUNNING, "kubeconfig_path": str(cluster.kubeconfig_path)})

        except Exception as e:
            print(f"Error while creating cluster: {e}")
            print(format_exc())

            await self.update_cluster(cluster_id, {"status": ClusterState.FAILED})

    def get_cluster_kubeconfig(self, cluster_id: int):
        kubeconfig_path = Path(self.storage.get_cluster(cluster_id).kubeconfig_path)

        return kubeconfig_path.read_text()

    async def update_cluster(self, cluster_id: int, cluster_data: str):
        self.storage.update_cluster(cluster_id, cluster_data)

    def get_cluster(self, cluster_id: int):
        return self.storage.get_cluster(cluster_id)

    def get_clusters(self):
        return self.storage.get_clusters()

    def delete_cluster(self, cluster_id: int):
        cluster = self.storage.get_cluster(cluster_id)

        provider = ProviderFactory.get_provider('hetzner')
        provider.delete_cluster()

        self.storage.delete_cluster(cluster_id)

    def install_app(self, app):
        pass

    def find_disparencies_in_clusters_state(self):
        pass
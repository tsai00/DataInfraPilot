import re
import traceback
from datetime import datetime

from src.api.schemas.volume import VolumeCreateSchema
from src.core.apps.airflow_application import AirflowApplication, AirflowConfig
from src.core.apps.application_factory import ApplicationFactory
from src.core.apps.grafana_application import GrafanaApplication, GrafanaConfig
from src.core.apps.hashicorp_vault_application import HashicorpVaultApplication, HashicorpVaultConfig
from src.core.kubernetes.kubernetes_cluster import KubernetesCluster
from src.core.providers.base_provider import BaseProvider
from src.core.kubernetes.configuration import ClusterConfiguration
from src.database.handlers.sqlite_handler import SQLiteHandler
from src.database.models.cluster import Cluster
from src.database.models.deployment import Deployment
from pathlib import Path
from src.core.providers.provider_factory import ProviderFactory
from traceback import format_exc
from src.core.kubernetes.deployment_status import DeploymentStatus
from src.core.kubernetes.chart_config import HelmChart
from src.database.models.volume import Volume


class ClusterManager(object):
    _instance = None
    _application_registry = {
        1: (AirflowApplication, AirflowConfig),
        2: (GrafanaApplication, GrafanaConfig),
        3: (HashicorpVaultApplication, HashicorpVaultConfig),
    }

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

            cls.storage = SQLiteHandler(f"sqlite:///{str(Path(Path(__file__).parent.parent.parent.parent.absolute(), 'app.db'))}")
            # logger
        return cls._instance

    def check_cluster_status(self):
        pass

    async def create_cluster(self, provider: BaseProvider, cluster_config: ClusterConfiguration):
        print(f'Will create cluster {cluster_config}')

        cluster = Cluster(
            name=cluster_config.name,
            k3s_version=cluster_config.k3s_version,
            provider=provider.name,
            pools=[x.to_dict() for x in cluster_config.pools],
            status=DeploymentStatus.CREATING
        )

        cluster_id = self.storage.create_cluster(cluster)

        try:
            cluster = await provider.create_cluster(cluster_config)

            self.storage.update_cluster(cluster_id, {"status": DeploymentStatus.RUNNING, "kubeconfig_path": str(cluster.kubeconfig_path), 'access_ip': cluster.access_ip})

            cluster.expose_traefik_dashboard()

            print("Installing Longhorn")
            longhorn_chart = HelmChart(name='longhorn', repo_url='https://charts.longhorn.io', version='1.8.1')
            values = {
                "defaultSettings": {
                    "defaultDataPath": "/var/longhorn"
                },
                "persistence": {
                    "defaultFsType": "ext4",
                    "defaultClassReplicaCount": 2,
                    "defaultClass": False
                }
            }
            await cluster.install_or_upgrade_chart(longhorn_chart, values)
            print("Installed Longhorn successfully")
        except Exception as e:
            print(f"Error while creating cluster: {e}")
            print(format_exc())

            self.storage.update_cluster(cluster_id, {"status": DeploymentStatus.FAILED, "error_message": str(e)})

    async def create_volume(self, provider: str, volume_config: VolumeCreateSchema):
        provider = ProviderFactory.get_provider(provider)

        volume = Volume(
            provider=provider.name,
            region=volume_config.region,
            name=volume_config.name,
            size=volume_config.size,
            status=DeploymentStatus.CREATING
        )
        volume_id = self.storage.create_volume(volume)

        try:
            await provider.create_volume(volume_config.name, volume_config.size, volume_config.region)

            print(f'Volume {volume_config.name} created')
            self.storage.update_volume(volume_id, {'status': DeploymentStatus.RUNNING})
        except Exception as e:
            print(f'Error while creating volume: {e}')
            self.storage.update_volume(volume_id, {'status': DeploymentStatus.FAILED, 'error_message': str(e)})

    def get_cluster_kubeconfig(self, cluster_id: int):
        kubeconfig_path = Path(self.storage.get_cluster(cluster_id).kubeconfig_path)

        return kubeconfig_path.read_text()

    def get_cluster(self, cluster_id: int):
        return self.storage.get_cluster(cluster_id)

    def get_clusters(self):
        return self.storage.get_clusters()

    def delete_cluster(self, cluster_id: int):
        # TODO: parametrize provider
        provider = ProviderFactory.get_provider('hetzner')
        provider.delete_cluster()

        self.storage.delete_cluster(cluster_id)

    def get_applications(self):
        return self.storage.get_applications()

    def get_application(self, application_id: int):
        return self.storage.get_application(application_id)

    def get_volumes(self):
        return self.storage.get_volumes()

    def get_volume(self, volume_id: int):
        return self.get_volume(volume_id)

    def delete_volume(self, volume_id: int):
        # TODO: parametrize provider
        provider = ProviderFactory.get_provider('hetzner')
        volume_from_db = self.storage.get_volume(volume_id)
        provider.delete_volume(volume_from_db.name)

        self.storage.delete_volume(volume_id)

    async def create_deployment(self, cluster_id: int, deployment_application_id: int, deployment_config: dict, node_pool: str):
        print(f"Deploying application to cluster {cluster_id}, config: {deployment_config}")

        cluster_from_db = self.get_cluster(cluster_id)

        if not cluster_from_db:
            raise ValueError(f"Cluster {cluster_id} was not found")

        cluster = KubernetesCluster.from_db_model(cluster_from_db)
        cluster_pools = [x.name for x in cluster.config.pools]

        if node_pool not in cluster_pools:
            raise ValueError(f"Node pool {node_pool} does not exist in cluster {cluster_id}. Available pools: {cluster_pools}")

        # TODO: dont like hardcoded assignment of webserver_hostname
        deployment_config['webserver_hostname'] = cluster.access_ip

        if deployment_application_id == 1:
            deployment_config['node_selector'] = {"pool": node_pool}

        application_instance = ApplicationFactory.get_application(deployment_application_id, deployment_config)

        helm_chart = application_instance.get_helm_chart()

        deployment = Deployment(
            cluster_id=cluster_from_db.id,
            application_id=deployment_application_id,
            status=DeploymentStatus.DEPLOYING,
            installed_at=datetime.now(),
            node_pool=node_pool,
            config=deployment_config
        )

        deployment_id = self.storage.create_deployment(deployment)

        namespace = f"{helm_chart.name}-{deployment_id}"
        self.storage.update_deployment(deployment_id, {"namespace": namespace})

        try:
            chart_installed = await cluster.install_or_upgrade_chart(helm_chart, application_instance.chart_values, namespace)

            if chart_installed:
                print(f"Successfully deployed application {deployment_application_id} to cluster {cluster_from_db.name}")
                self.storage.update_deployment(deployment_id, {"status": DeploymentStatus.RUNNING})
            else:
                print(f"Failed to deploy application {deployment_application_id} to cluster {cluster_from_db.name}")
                self.storage.update_deployment(deployment_id, {"status": DeploymentStatus.FAILED, "error_message": f"Failed to deploy application {deployment_application_id} to cluster {cluster_from_db.name}"})

        except Exception as e:
            print(f"Error during application deployment: {e}")
            print(traceback.format_exc())

            self.storage.update_deployment(deployment_id, {"status": DeploymentStatus.FAILED, "error_message": str(e)})

        # TODO: move under application class (something like post_init_actions)
        if deployment_application_id == 3:
            print('Executing post-init commands')
            command = ["vault", "operator", "init"]

            output = cluster.execute_command_on_pod('vault-0', namespace, command)

            unseal_keys = re.findall(r'Unseal Key \d: (.{44})', output)

            if not unseal_keys:
                raise ValueError(f'Could not find unseal keys in {output}')
            root_token_match = re.search(r'Initial Root Token: (.{28})', output)

            if root_token_match:
                root_token = root_token_match.group(1)
            else:
                raise ValueError(f'Could not find root token in {output}')

            print(f'Unsealed keys: {unseal_keys}')

            for unseal_key in unseal_keys:
                command = ["vault", "operator", "unseal"]
                output = cluster.execute_command_on_pod('vault-0', namespace, command, True, unseal_key)

    async def update_deployment(self, cluster_id: int, deployment_id: int, deployment_config: dict):
        cluster_from_db = self.get_cluster(cluster_id)

        if not cluster_from_db:
            raise ValueError(f"Cluster {cluster_id} was not found")

        deployment_from_db = self.get_deployment(deployment_id)

        if not deployment_from_db:
            raise ValueError(f"Deployment {deployment_id} was not found")

        cluster = KubernetesCluster.from_db_model(cluster_from_db)

        # TODO: dont like hardcoded assignment of webserver_hostname
        deployment_config['webserver_hostname'] = cluster.access_ip

        if deployment_from_db.application_id == 1:
            deployment_config['node_selector'] = {"pool": deployment_from_db.node_pool}

        application_instance = ApplicationFactory.get_application(deployment_from_db.application_id, deployment_config)

        self.storage.update_deployment(deployment_from_db.application_id,
                                     {"status": DeploymentStatus.UPDATING, "config": deployment_config})

        try:
            chart_updated = await cluster.install_or_upgrade_chart(application_instance.get_helm_chart(),
                                                                     application_instance.chart_values, deployment_from_db.namespace)

            if chart_updated:
                print(f"Successfully updated application {application_instance.name} {cluster_from_db.name}")
                self.storage.update_deployment(deployment_from_db.application_id, {"status": DeploymentStatus.RUNNING})
            else:
                print(f"Failed to update application {application_instance.name} to cluster {cluster_from_db.name}")
                self.storage.update_deployment(deployment_from_db.application_id, {"status": DeploymentStatus.FAILED, "error_message": f"Failed to update application {application_instance.name} to cluster {cluster_from_db.name}"})
        except Exception as e:
            print(traceback.format_exc())
            print(f'Error while updating application: {e}')
            self.storage.update_deployment(deployment_from_db.application_id, {"status": DeploymentStatus.FAILED, "error_message": str(e)})

    async def remove_deployment(self, deployment_id: int):
        deployment_from_db = self.get_deployment(deployment_id)
        
        if not deployment_from_db:
            raise ValueError(f"Deployment {deployment_id} was not found")

        cluster_from_db = self.get_cluster(deployment_from_db.cluster_id)

        cluster = KubernetesCluster.from_db_model(cluster_from_db)

        # TODO: handle misssing application
        helm_chart = self._application_registry.get(deployment_from_db.application_id)[0].get_helm_chart()

        await cluster.uninstall_chart(helm_chart, deployment_from_db.namespace)

        self.storage.delete_deployment(deployment_id)

    def get_deployments(self, cluster_id: int):
        return self.storage.get_deployments(cluster_id)

    def get_deployment(self, deployment_id: int):
        return self.storage.get_deployment(deployment_id)

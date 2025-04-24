import traceback
from datetime import datetime

from src.core.apps.airflow_application import AirflowApplication, AirflowConfig
from src.core.apps.grafana_application import GrafanaApplication, GrafanaConfig
from src.core.apps.base_application import BaseApplication
from src.core.kubernetes.kubernetes_cluster import KubernetesCluster
from src.core.providers.base_provider import BaseProvider
from src.core.kubernetes.configuration import ClusterConfiguration
from src.database.handlers.sqlite_handler import SQLiteHandler
from src.database.models.cluster import Cluster
from src.database.models.cluster_application import ClusterApplication
from src.core.apps.application_config import ApplicationConfig
from pathlib import Path
from src.core.providers.provider_factory import ProviderFactory
from traceback import format_exc
from src.core.kubernetes.deployment_status import DeploymentStatus
from src.core.kubernetes.chart_config import HelmChart


class ClusterManager(object):
    _instance = None

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

            await self.update_cluster(cluster_id, {"status": DeploymentStatus.RUNNING, "kubeconfig_path": str(cluster.kubeconfig_path), 'access_ip': cluster.access_ip})

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

            await self.update_cluster(cluster_id, {"status": DeploymentStatus.FAILED, "error_message": str(e)})

    def get_cluster_kubeconfig(self, cluster_id: int):
        kubeconfig_path = Path(self.storage.get_cluster(cluster_id).kubeconfig_path)

        return kubeconfig_path.read_text()

    async def update_cluster(self, cluster_id: int, cluster_data: dict):
        self.storage.update_cluster(cluster_id, cluster_data)

    async def update_cluster_application(self, cluster_application_id: int, cluster_application_data: dict):
        self.storage.update_cluster_application(cluster_application_id, cluster_application_data)

    def get_cluster(self, cluster_id: int):
        return self.storage.get_cluster(cluster_id)

    def get_clusters(self):
        return self.storage.get_clusters()

    def delete_cluster(self, cluster_id: int):
        provider = ProviderFactory.get_provider('hetzner')
        provider.delete_cluster()

        self.storage.delete_cluster(cluster_id)

    def install_app(self, app):
        pass

    def find_disparencies_in_clusters_state(self):
        pass

    # TODO: probably rename to distinguish between get all applications anf get cluster applications
    def get_applications(self):
        return self.storage.get_applications()

    def get_application(self, application_id: int):
        return self.storage.get_application(application_id)

    async def deploy_application(self, cluster_id: int, application_config: ApplicationConfig):
        try:
            print(f"Deploying application to cluster {cluster_id}, config: {application_config}")

            cluster_from_db = self.get_cluster(cluster_id)

            if not cluster_from_db:
                raise ValueError(f"Cluster {cluster_id} was not found")

            application = self.get_application(application_config.id)

            if not application:
                raise ValueError(f"Application {application_config.id} was not found")

            cluster = KubernetesCluster.from_db_model(cluster_from_db)

            # TODO: dont like hardcoded assignment of webserver_hostname
            application_config.config['webserver_hostname'] = cluster.access_ip

            application_instance = self._get_application_instance(application_config)

            cluster_application = ClusterApplication(
                cluster_id=cluster_from_db.id,
                application_id=application.id,
                status=DeploymentStatus.DEPLOYING,
                installed_at=datetime.now(),
                config=application_config.config
            )

            cluster_application_id = self.storage.create_cluster_application(cluster_application)

            chart_installed = await cluster.install_or_upgrade_chart(application_instance.helm_chart, application_instance.chart_values)

            if chart_installed:
                print(f"Successfully deployed application {application.name} to cluster {cluster_from_db.name}")
                await self.update_cluster_application(cluster_application_id, {"status": DeploymentStatus.RUNNING})
            else:
                print(f"Failed to deploy application {application.name} to cluster {cluster_from_db.name}")
                await self.update_cluster_application(cluster_application_id, {"status": DeploymentStatus.FAILED})

        except Exception as e:
            print(f"Error during application deployment: {e}")
            print(traceback.format_exc())

            await self.update_cluster_application(cluster_application_id, {"status": DeploymentStatus.FAILED})

    async def update_application(self, cluster_id: int, application_config: ApplicationConfig):
        cluster_from_db = self.get_cluster(cluster_id)

        if not cluster_from_db:
            raise ValueError(f"Cluster {cluster_id} was not found")

        cluster = KubernetesCluster.from_db_model(cluster_from_db)

        # TODO: dont like hardcoded assignment of webserver_hostname
        application_config.config['webserver_hostname'] = cluster.access_ip

        application_instance = self._get_application_instance(application_config)

        application_from_db = self.storage.get_cluster_application(cluster_id, application_config.id)

        await self.update_cluster_application(application_from_db.id,
                                              {"status": DeploymentStatus.UPDATING, "config": application_config.config})

        try:
            chart_updated = await cluster.install_or_upgrade_chart(application_instance.helm_chart,
                                                                     application_instance.chart_values)

            if chart_updated:
                print(f"Successfully updated application {application_instance.name} {cluster_from_db.name}")
                await self.update_cluster_application(application_from_db.id, {"status": DeploymentStatus.RUNNING})
            else:
                print(f"Failed to update application {application_instance.name} to cluster {cluster_from_db.name}")
                await self.update_cluster_application(application_from_db.id, {"status": DeploymentStatus.FAILED})
        except Exception as e:
            print(traceback.format_exc())
            print(f'Error while updating application: {e}')
            await self.update_cluster_application(application_from_db.id, {"status": DeploymentStatus.FAILED})

    async def remove_application(self, cluster_id: int, application_id: int):
        cluster_from_db = self.get_cluster(cluster_id)

        if not cluster_from_db:
            raise ValueError(f"Cluster {cluster_id} was not found")

        cluster = KubernetesCluster.from_db_model(cluster_from_db)

        if application_id == 1:
            # TODO: solve this so there is no need to initalise dummy app config when retrieving helm chart
            helm_chart = AirflowApplication(AirflowConfig(version="2.10.3", webserver_hostname='', instance_name='', dags_repository='https://testsdfsdfs.git')).helm_chart
        elif application_id == 2:
            helm_chart = GrafanaApplication(GrafanaConfig(webserver_hostname='')).helm_chart
        else:
            raise ValueError('Unsupported application')

        cluster = KubernetesCluster.from_db_model(cluster_from_db)

        await cluster.uninstall_chart(helm_chart)

        self.storage.delete_cluster_application(cluster_id, application_id)

    def _get_application_instance(self, application_config: ApplicationConfig) -> BaseApplication:
        if application_config.id == 1:
            return AirflowApplication(AirflowConfig(**application_config.config))
        elif application_config.id == 2:
            return GrafanaApplication(GrafanaConfig(**application_config.config))
        else:
            raise ValueError(f"Unsupported application: {application_config.id}")

    def get_cluster_applications(self, cluster_id: int):
        return self.storage.get_cluster_applications(cluster_id)

    def get_cluster_application(self, cluster_id: int, application_id: int):
        return self.storage.get_cluster_application(cluster_id, application_id)

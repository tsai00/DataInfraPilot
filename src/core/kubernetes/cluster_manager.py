import asyncio
import re
import traceback
from datetime import datetime

from src.api.schemas.deployment import DeploymentCreateSchema
from src.api.schemas.volume import VolumeCreateSchema
from src.core.apps.application_factory import ApplicationFactory
from src.core.apps.base_application import AccessEndpointType
from src.core.exceptions import ResourceUnavailableException
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
from src.database.models.volume import Volume
from pydantic_core._pydantic_core import ValidationError


class ClusterManager(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

            db_folder = Path(Path(__file__).parent.parent.parent.parent.absolute(), 'data')

            db_folder.mkdir(exist_ok=True)

            cls.storage = SQLiteHandler(f"sqlite:///{str(Path(db_folder, 'app.db'))}")
            # logger
        return cls._instance

    async def create_cluster(self, provider: BaseProvider, cluster_config: ClusterConfiguration):
        print(f'Will create cluster {cluster_config}')

        cluster = Cluster(
            name=cluster_config.name,
            k3s_version=cluster_config.k3s_version,
            domain_name=cluster_config.domain_name,
            provider=provider.name,
            provider_config=provider._config.to_dict(),
            pools=[x.to_dict() for x in cluster_config.pools],
            status=DeploymentStatus.CREATING,
            additional_components=cluster_config.additional_components.dict()
        )

        cluster_id = self.storage.create_cluster(cluster)

        try:
            cluster = await provider.create_cluster(cluster_config)

            await cluster.install_longhorn()

            # explicit wait to avoid 404 error when exposing Traefik dashboard
            await asyncio.sleep(10)

            if cluster_config.domain_name and cluster_config.additional_components.traefik_dashboard.enabled:
                await cluster.install_certmanager(cluster_config.domain_name)

                cluster.expose_traefik_dashboard(
                    username=cluster_config.additional_components.traefik_dashboard.username,
                    password=cluster_config.additional_components.traefik_dashboard.password,
                    enable_https=True,
                    domain_name=cluster_config.domain_name,
                    secret_name='main-certificate-tls'
                )
            elif cluster_config.additional_components.traefik_dashboard.enabled:
                cluster.expose_traefik_dashboard(
                    username=cluster_config.additional_components.traefik_dashboard.username,
                    password=cluster_config.additional_components.traefik_dashboard.password,
                    enable_https=False,
                )

            # TODO: remove hardcoded node name
            cluster.cordon_node(f"{cluster_config.name}-control-plane-node-1")

            self.storage.update_cluster(cluster_id, {"status": DeploymentStatus.RUNNING, "kubeconfig_path": str(cluster.kubeconfig_path), 'access_ip': cluster.access_ip})
        except ResourceUnavailableException as e:
            error_message = f'{str(e)}. Right now Hetzner does not have available machines for selected type/region. Please try removing the cluster and creating it again later or choose VM of different type / location.'
            self.storage.update_cluster(cluster_id, {"status": DeploymentStatus.FAILED, "error_message": error_message})
        except Exception as e:
            print(f"Error while creating cluster: {e}")
            print(format_exc())

            error_msg_formatted = re.sub(r'WARNING: Kubernetes configuration file is (?:world|group)-readable\. This is insecure\. Location: .*\.yaml','', str(e))

            self.storage.update_cluster(cluster_id, {"status": DeploymentStatus.FAILED, "error_message": error_msg_formatted})

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
        cluster = self.storage.get_cluster(cluster_id)
        provider = ProviderFactory.get_provider('hetzner', cluster.provider_config)

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

    async def create_deployment(self, cluster_id: int, deployment_create: DeploymentCreateSchema):
        volume_requirements = deployment_create.volumes or []
        node_pool = deployment_create.node_pool if deployment_create.node_pool != "noselection" else None

        deployment_config = deployment_create.config.copy()

        print(f"Deploying application to cluster {cluster_id}, config: {deployment_config}")

        cluster_from_db = self.get_cluster(cluster_id)

        if not cluster_from_db:
            raise ValueError(f"Cluster {cluster_id} was not found")

        cluster = KubernetesCluster.from_db_model(cluster_from_db)

        if node_pool:
            cluster_pools = [x.name for x in cluster.config.pools]

            if node_pool not in cluster_pools:
                raise ValueError(
                    f"Node pool {node_pool} does not exist in cluster {cluster_id}. Available pools: {cluster_pools}")

            if deployment_create.application_id == 1:
                deployment_config['node_selector'] = {"pool": node_pool}

        # for volume_requirement in volume_requirements:
        #     if volume_requirement.volume_type == "new":
        #         print(f'Will create new volume as per requirement {volume_requirement}')
        #         helm_chart_values['logs']['persistence']['size'] = f'{volume_requirement.size}Gi'
        #     elif volume_requirement.volume_type == "existing":
        #         print(f'Will use existing volume as per requirement {volume_requirement}')
        #         volumes = [x for x in self.storage.get_volumes() if x.name == volume_requirement.name]
        #
        #         if not volumes:
        #             raise ValueError(f'Could not find volume {volume_requirement.name} in DB')
        #         else:
        #             volume = volumes[0]
        #
        #         helm_chart_values['logs']['persistence']['size'] = f'{volume.size}Gi'
        #         helm_chart_values['logs']['persistence']['existingClaim'] = volume.name
        #
        #     else:
        #         raise ValueError(f"Unknown volume requirement type: {volume_requirement.volume_type}")

        deployment = Deployment(
            cluster_id=cluster_from_db.id,
            name=deployment_create.name,
            application_id=deployment_create.application_id,
            status=DeploymentStatus.DEPLOYING,
            installed_at=datetime.now(),
            node_pool=node_pool,
            config=deployment_config,
            endpoints=[x.to_dict() for x in deployment_create.endpoints],
        )

        deployment_id = self.storage.create_deployment(deployment)

        try:
            application_instance = ApplicationFactory.get_application(deployment_create.application_id,
                                                                      deployment_config)
        except ValidationError as e:
            print(f"Application config validation error: {e.errors()}")
            self.storage.update_deployment(deployment_id, {"status": DeploymentStatus.FAILED,
                                                           "error_message": f"Application config error: {e.errors()}"})
            return

        helm_chart = application_instance.get_helm_chart()
        helm_chart_values = application_instance.chart_values.copy()

        namespace = f"{helm_chart.name.split('/')[-1]}-{deployment_id}"
        self.storage.update_deployment(deployment_id, {"namespace": namespace})

        for x in deployment_create.endpoints:
            if x.access_type in ('subdomain', 'domain_path'):
                cluster.create_certificate(f'{namespace}-{x.name}-tls', x.value[:x.value.find('/')], f'{namespace}-{x.name}-tls', namespace=namespace)

        access_endpoints_values = application_instance.get_ingress_helm_values(deployment_create.endpoints, cluster.access_ip, namespace)

        helm_chart_values = {**helm_chart_values, **access_endpoints_values}

        try:
            application_instance.run_pre_install_actions(cluster, namespace, deployment_config)

            chart_installed = await cluster.install_or_upgrade_chart(helm_chart, helm_chart_values, namespace)

            if chart_installed:
                print(f"Successfully deployed application {deployment.application_id} to cluster {cluster_from_db.name}")
                self.storage.update_deployment(deployment_id, {"status": DeploymentStatus.RUNNING})

                application_instance.run_post_install_actions(cluster, namespace, {**deployment_config, **access_endpoints_values})

                # TODO: move decision create/not create secret to application class or od exists_ok paamater to create_secret
                if deployment.application_id != 2 and application_instance.get_initial_credentials_secret_name():
                    cluster.create_secret(application_instance.get_initial_credentials_secret_name(), namespace, application_instance.get_initial_credentials())
            else:
                print(f"Failed to deploy application {deployment.application_id} to cluster {cluster_from_db.name}")
                self.storage.update_deployment(deployment_id, {"status": DeploymentStatus.FAILED, "error_message": f"Failed to deploy application {deployment.application_id} to cluster {cluster_from_db.name}"})

        except Exception as e:
            print(f"Error during application deployment: {e}")
            print(traceback.format_exc())
            error_msg_formatted = re.sub(r'WARNING: Kubernetes configuration file is (?:world|group)-readable\. This is insecure\. Location: .*\.yaml','', str(e))

            self.storage.update_deployment(deployment_id, {"status": DeploymentStatus.FAILED, "error_message": error_msg_formatted})

    async def update_deployment(self, cluster_id: int, deployment_id: int, deployment_config: dict):
        cluster_from_db = self.get_cluster(cluster_id)

        if not cluster_from_db:
            raise ValueError(f"Cluster {cluster_id} was not found")

        deployment_from_db = self.get_deployment(deployment_id)

        if not deployment_from_db:
            raise ValueError(f"Deployment {deployment_id} was not found")

        cluster = KubernetesCluster.from_db_model(cluster_from_db)

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

        helm_chart = ApplicationFactory.get_application_class(deployment_from_db.application_id).get_helm_chart()

        await cluster.uninstall_chart(helm_chart, deployment_from_db.namespace)

        self.storage.delete_deployment(deployment_id)

    def get_deployments(self, cluster_id: int):
        return self.storage.get_deployments(cluster_id)

    def get_deployment(self, deployment_id: int):
        return self.storage.get_deployment(deployment_id)

    def get_deployment_initial_credentials(self, deployment_id: int) -> dict:
        deployment = self.get_deployment(deployment_id)

        if not deployment:
            raise ValueError(f"Deployment {deployment_id} was not found")

        cluster_from_db = self.get_cluster(deployment.cluster_id)

        cluster = KubernetesCluster.from_db_model(cluster_from_db)
        application_id = deployment.application_id

        application = ApplicationFactory.get_application_class(application_id)
        application_metadata = ApplicationFactory.get_application_metadata(application_id)

        secret = cluster.get_secret(application.get_initial_credentials_secret_name(), deployment.namespace)

        return {'username': secret[application_metadata.username_key], 'password': secret[application_metadata.password_key]}

    def get_existing_endpoints(self, cluster_id: int) -> dict:
        deployments = self.storage.get_deployments(cluster_id)

        existing_cluster_ip_path_endpoints = []
        existing_domain_path_endpoints = []
        existing_subdomain_endpoints = []

        for deployment in deployments:
            for endpoint in deployment.endpoints:
                if endpoint['access_type'] == AccessEndpointType.CLUSTER_IP_PATH:
                    existing_cluster_ip_path_endpoints.append(endpoint['value'])
                elif endpoint['access_type'] == AccessEndpointType.DOMAIN_PATH:
                    existing_domain_path_endpoints.append(endpoint['value'])
                elif endpoint['access_type'] == AccessEndpointType.SUBDOMAIN:
                    existing_subdomain_endpoints.append(endpoint['value'])
                else:
                    raise ValueError(f"Unknown access type {endpoint['access_type']} for endpoint {endpoint['name']} in deployment {deployment.name}")

        return {
            AccessEndpointType.CLUSTER_IP_PATH: existing_cluster_ip_path_endpoints,
            AccessEndpointType.DOMAIN_PATH: existing_domain_path_endpoints,
            AccessEndpointType.SUBDOMAIN: existing_subdomain_endpoints
        }
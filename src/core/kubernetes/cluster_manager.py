import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path

from pydantic_core._pydantic_core import ValidationError

from src.api.schemas import DeploymentCreateSchema, VolumeCreateSchema
from src.core.apps.application_factory import ApplicationFactory
from src.core.apps.base_application import AccessEndpointType
from src.core.deployment_status import DeploymentStatus
from src.core.exceptions import ResourceUnavailableError
from src.core.kubernetes.configuration import ClusterConfiguration
from src.core.kubernetes.kubernetes_cluster import KubernetesCluster
from src.core.providers.base_provider import BaseProvider
from src.core.providers.provider_factory import ProviderFactory
from src.core.utils import setup_logger
from src.database.handlers.sqlite_handler import SQLiteHandler
from src.database.models import Application, Cluster, Deployment, Volume


class ClusterManager:
    _instance: 'ClusterManager' = None
    _logger: logging.Logger = None

    def __new__(cls, *args, **kwargs) -> None:
        if cls._instance is None:
            cls._instance = super().__new__(cls)

            cls._logger = setup_logger('ClusterManager')

            db_folder = Path(Path(__file__).parent.parent.parent.parent.absolute(), 'data')

            db_folder.mkdir(exist_ok=True)

            cls.storage = SQLiteHandler(f'sqlite:///{str(Path(db_folder, "app.db"))}')

            cls._logger.info('ClusterManager initialised')
        return cls._instance

    async def create_cluster(self, provider: BaseProvider, cluster_config: ClusterConfiguration) -> None:
        self._logger.info(f'Will create cluster {cluster_config}')

        cluster_db = Cluster(
            name=cluster_config.name,
            k3s_version=cluster_config.k3s_version,
            domain_name=cluster_config.domain_name,
            provider=provider.name,
            provider_config=provider._config.to_dict(),
            pools=[x.to_dict() for x in cluster_config.pools],
            status=DeploymentStatus.CREATING,
            additional_components=cluster_config.additional_components.dict(),
        )

        cluster_id = self.storage.create_cluster(cluster_db)

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
                    secret_name='main-certificate-tls',  # noqa: S106 (not a secret)
                )
            elif cluster_config.additional_components.traefik_dashboard.enabled:
                cluster.expose_traefik_dashboard(
                    username=cluster_config.additional_components.traefik_dashboard.username,
                    password=cluster_config.additional_components.traefik_dashboard.password,
                    enable_https=False,
                )

            # TODO: remove hardcoded node name
            cluster.cordon_node(f'{cluster_config.name}-control-plane-node-1')

            self.storage.update_cluster(
                cluster_id,
                {
                    'status': DeploymentStatus.RUNNING,
                    'kubeconfig_path': str(cluster.kubeconfig_path),
                    'access_ip': cluster.access_ip,
                },
            )
        except ResourceUnavailableError as e:
            error_message = f'{str(e)}. Right now Hetzner does not have available machines for selected type/region. Please try removing the cluster and creating it again later or choose VM of different type / location.'
            self.storage.update_cluster(cluster_id, {'status': DeploymentStatus.FAILED, 'error_message': error_message})
        except Exception as e:
            self._logger.exception(f'Error while creating cluster: {e}', exc_info=True)

            error_msg_formatted = re.sub(
                r'WARNING: Kubernetes configuration file is (?:world|group)-readable\. This is insecure\. Location: .*\.yaml',
                '',
                str(e),
            )

            self.storage.update_cluster(
                cluster_id, {'status': DeploymentStatus.FAILED, 'error_message': error_msg_formatted}
            )

        self._logger.info(f'Cluster {cluster_db.name} created')

    async def create_volume(self, provider: str, volume_config: VolumeCreateSchema) -> None:
        provider = ProviderFactory.get_provider(provider)

        volume = Volume(
            provider=provider.name,
            region=volume_config.region,
            name=volume_config.name,
            size=volume_config.size,
            status=DeploymentStatus.CREATING,
        )
        volume_id = self.storage.create_volume(volume)

        try:
            await provider.create_volume(volume_config.name, volume_config.size, volume_config.region)

            self._logger.info(f'Volume {volume_config.name} created')
            self.storage.update_volume(volume_id, {'status': DeploymentStatus.RUNNING})
        except Exception as e:
            self._logger.exception(f'Error while creating volume: {e}')
            self.storage.update_volume(volume_id, {'status': DeploymentStatus.FAILED, 'error_message': str(e)})

    def get_cluster_kubeconfig(self, cluster_id: int) -> str:
        kubeconfig_path = Path(self.storage.get_cluster(cluster_id).kubeconfig_path)

        return kubeconfig_path.read_text()

    def get_cluster(self, cluster_id: int) -> type[Cluster]:
        return self.storage.get_cluster(cluster_id)

    def get_clusters(self) -> list[type[Cluster]]:
        return self.storage.get_clusters()

    def delete_cluster(self, cluster_id: int) -> None:
        # TODO: parametrize provider
        cluster = self.storage.get_cluster(cluster_id)
        provider = ProviderFactory.get_provider('hetzner', cluster.provider_config)

        provider.delete_cluster()

        self.storage.delete_cluster(cluster_id)

    def get_applications(self) -> list[type[Application]]:
        return self.storage.get_applications()

    def get_application(self, application_id: int) -> type[Application]:
        return self.storage.get_application(application_id)

    def get_volumes(self) -> list[type[Volume]]:
        return self.storage.get_volumes()

    def get_volume(self, volume_id: int) -> type[Volume]:
        return self.get_volume(volume_id)

    def delete_volume(self, volume_id: int) -> None:
        # TODO: parametrize provider
        provider = ProviderFactory.get_provider('hetzner')
        volume_from_db = self.storage.get_volume(volume_id)
        provider.delete_volume(volume_from_db.name)

        self.storage.delete_volume(volume_id)

    async def create_deployment(self, cluster_id: int, deployment_create: DeploymentCreateSchema) -> None:
        # volume_requirements = deployment_create.volumes or []
        node_pool = deployment_create.node_pool if deployment_create.node_pool != 'noselection' else None

        deployment_config = deployment_create.config.copy()

        self._logger.info(f'Deploying application to cluster {cluster_id}, config: {deployment_config}')

        cluster_from_db = self.get_cluster(cluster_id)

        if not cluster_from_db:
            msg = f'Cluster {cluster_id} was not found'
            self._logger.exception(msg)
            raise ValueError(msg)

        cluster = KubernetesCluster.from_db_model(cluster_from_db)

        if node_pool:
            cluster_pools = [x.name for x in cluster.config.pools]

            if node_pool not in cluster_pools:
                msg = f'Node pool {node_pool} does not exist in cluster {cluster_id}. Available pools: {cluster_pools}'
                self._logger.exception(msg)
                raise ValueError(msg)

            if deployment_create.application_id == 1:
                deployment_config['node_selector'] = {'pool': node_pool}

        # for volume_requirement in volume_requirements:
        #     if volume_requirement.volume_type == "new":
        #         self._logger.info(f'Will create new volume as per requirement {volume_requirement}')
        #         helm_chart_values['logs']['persistence']['size'] = f'{volume_requirement.size}Gi'
        #     elif volume_requirement.volume_type == "existing":
        #         self._logger.info(f'Will use existing volume as per requirement {volume_requirement}')
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
            application_instance = ApplicationFactory.get_application(
                deployment_create.application_id, deployment_config
            )
        except ValidationError as e:
            self._logger.exception(f'Application config validation error: {e.errors()}', exc_info=False)
            self.storage.update_deployment(
                deployment_id,
                {'status': DeploymentStatus.FAILED, 'error_message': f'Application config error: {e.errors()}'},
            )
            return

        helm_chart = application_instance.get_helm_chart()
        helm_chart_values = application_instance.chart_values.copy()

        namespace = f'{helm_chart.name.split("/")[-1]}-{deployment_id}'
        self.storage.update_deployment(deployment_id, {'namespace': namespace})

        for x in deployment_create.endpoints:
            if x.access_type in ('subdomain', 'domain_path'):
                cluster.create_certificate(
                    f'{namespace}-{x.name}-tls',
                    x.value[: x.value.find('/')],
                    f'{namespace}-{x.name}-tls',
                    namespace=namespace,
                )

        access_endpoints_values = application_instance.get_ingress_helm_values(
            deployment_create.endpoints, cluster.access_ip, namespace
        )

        helm_chart_values = {**helm_chart_values, **access_endpoints_values}

        try:
            application_instance.run_pre_install_actions(cluster, namespace, deployment_config)

            await cluster.install_or_upgrade_chart(helm_chart, helm_chart_values, namespace)

            self._logger.info(
                f'Successfully deployed application {deployment.application_id} to cluster {cluster_from_db.name}'
            )
            self.storage.update_deployment(deployment_id, {'status': DeploymentStatus.RUNNING})

            application_instance.run_post_install_actions(
                cluster, namespace, {**deployment_config, **access_endpoints_values}
            )
        except Exception as e:
            self._logger.exception(f'Error during application deployment: {e}', exc_info=True)
            error_msg_formatted = re.sub(
                r'WARNING: Kubernetes configuration file is (?:world|group)-readable\. This is insecure\. Location: .*\.yaml',
                '',
                str(e),
            )
            self.storage.update_deployment(
                deployment_id, {'status': DeploymentStatus.FAILED, 'error_message': error_msg_formatted}
            )

    async def update_deployment(self, cluster_id: int, deployment_id: int, deployment_config: dict) -> None:
        cluster_from_db = self.get_cluster(cluster_id)

        if not cluster_from_db:
            msg = f'Cluster {cluster_id} was not found'
            self._logger.exception(msg)
            raise ValueError(msg)

        deployment_from_db = self.get_deployment(deployment_id)

        if not deployment_from_db:
            msg = f'Deployment {deployment_id} was not found'
            self._logger.exception(msg)
            raise ValueError(msg)

        cluster = KubernetesCluster.from_db_model(cluster_from_db)

        if deployment_from_db.application_id == 1:
            deployment_config['node_selector'] = {'pool': deployment_from_db.node_pool}

        application_instance = ApplicationFactory.get_application(deployment_from_db.application_id, deployment_config)

        self.storage.update_deployment(
            deployment_from_db.application_id, {'status': DeploymentStatus.UPDATING, 'config': deployment_config}
        )

        try:
            await cluster.install_or_upgrade_chart(
                application_instance.get_helm_chart(), application_instance.chart_values, deployment_from_db.namespace
            )

            self._logger.info(f'Successfully updated application {application_instance.name} {cluster_from_db.name}')
            self.storage.update_deployment(deployment_from_db.application_id, {'status': DeploymentStatus.RUNNING})
        except Exception as e:
            self._logger.exception(f'Error while updating application: {e}', exc_info=True)
            self.storage.update_deployment(
                deployment_from_db.application_id, {'status': DeploymentStatus.FAILED, 'error_message': str(e)}
            )

    async def remove_deployment(self, deployment_id: int) -> None:
        deployment_from_db = self.get_deployment(deployment_id)

        if not deployment_from_db:
            raise ValueError(f'Deployment {deployment_id} was not found')

        cluster_from_db = self.get_cluster(deployment_from_db.cluster_id)

        cluster = KubernetesCluster.from_db_model(cluster_from_db)

        helm_chart = ApplicationFactory.get_application_class(deployment_from_db.application_id).get_helm_chart()

        await cluster.uninstall_chart(helm_chart, deployment_from_db.namespace)

        self.storage.delete_deployment(deployment_id)

    def get_deployments(self, cluster_id: int) -> list[type[Deployment]]:
        return self.storage.get_deployments(cluster_id)

    def get_deployment(self, deployment_id: int) -> type[Deployment]:
        return self.storage.get_deployment(deployment_id)

    def get_deployment_initial_credentials(self, deployment_id: int) -> dict:
        deployment = self.get_deployment(deployment_id)

        if not deployment:
            msg = f'Deployment {deployment_id} was not found'
            self._logger.exception(msg)
            raise ValueError(msg)

        cluster_from_db = self.get_cluster(deployment.cluster_id)

        cluster = KubernetesCluster.from_db_model(cluster_from_db)
        application_id = deployment.application_id

        application = ApplicationFactory.get_application_class(application_id)
        application_metadata = ApplicationFactory.get_application_metadata(application_id)

        secret = cluster.get_secret(application.credentials_secret_name, deployment.namespace)

        return {
            'username': secret[application_metadata.username_key],
            'password': secret[application_metadata.password_key],
        }

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
                    raise ValueError(
                        f'Unknown access type {endpoint["access_type"]} for endpoint {endpoint["name"]} in deployment {deployment.name}'
                    )

        return {
            AccessEndpointType.CLUSTER_IP_PATH: existing_cluster_ip_path_endpoints,
            AccessEndpointType.DOMAIN_PATH: existing_domain_path_endpoints,
            AccessEndpointType.SUBDOMAIN: existing_subdomain_endpoints,
        }

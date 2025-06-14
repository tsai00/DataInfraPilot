import asyncio
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import asyncssh
import yaml
from hcloud import APIException, Client
from hcloud.images import Image
from hcloud.locations import Location
from hcloud.networks import Network, NetworkSubnet
from hcloud.placement_groups import CreatePlacementGroupResponse, PlacementGroup
from hcloud.server_types import ServerType
from hcloud.servers import ServerCreatePublicNetwork
from hcloud.ssh_keys import SSHKey
from hcloud.volumes import Volume

from src.core.config import PATH_TO_K3S_YAML_CONFIGS
from src.core.exceptions import ProjectNotEmptyError, ResourceUnavailableError
from src.core.kubernetes.configuration import ClusterConfiguration
from src.core.kubernetes.kubernetes_cluster import KubernetesCluster
from src.core.providers.base_provider import BaseProvider
from src.core.template_loader import template_loader
from src.core.utils import generate_password


class HetznerNodeType(StrEnum):
    CX22 = 'cx22'
    CX32 = 'cx32'
    CX42 = 'cx42'
    CX52 = 'cx52'


class HetznerRegion(StrEnum):
    FSN1 = 'fsn1'
    NBG1 = 'nbg1'
    HEL1 = 'hel1'


@dataclass
class HetznerConfig:
    api_token: str
    ssh_private_key_path: str | None = None
    ssh_public_key_path: str | None = None

    def to_dict(self) -> dict:
        return {
            'api_token': self.api_token,
            'ssh_private_key_path': self.ssh_private_key_path,
            'ssh_public_key_path': self.ssh_public_key_path,
        }


class HetznerProvider(BaseProvider):
    name = 'hetzner'

    def __init__(self, config: HetznerConfig) -> None:
        super().__init__()

        self.client = Client(token=config.api_token)

        self._ssh_private_key_path = Path(config.ssh_private_key_path).expanduser()
        self._ssh_public_key_path = Path(config.ssh_public_key_path).expanduser()

        self._config = config

    async def _wait_until_server_is_initialised(self, server_id: str) -> None:
        while True:
            server = await asyncio.to_thread(self.client.servers.get_by_id, server_id)

            if server.status == 'running':
                self._logger.info(f'Server {server_id} is running.')
                break
            else:
                self._logger.warning(f'Server {server_id} not ready yet, status: {server.status}')
                await asyncio.sleep(2)

    async def _wait_until_cloud_init_finished(self, ip: str, username: str) -> None:
        while True:
            try:
                async with asyncssh.connect(
                    ip, username=username, client_keys=[self._ssh_private_key_path], known_hosts=None
                ) as ssh:
                    result = await ssh.run('test -f /var/lib/cloud/instance/boot-finished && echo "done"', check=True)
                    if result.stdout.strip() == 'done':
                        self._logger.info('Cloud-init finished successfully.')
                        break
                    else:
                        self._logger.warning('Cloud-init still running...')
            except Exception as e:
                self._logger.warning(f'SSH connection failed: {e}')

            await asyncio.sleep(5)

    async def _install_k3s(self, ip: str, username: str, content: str) -> None:
        try:
            async with asyncssh.connect(
                ip, username=username, client_keys=[self._ssh_private_key_path], known_hosts=None
            ) as ssh:
                await ssh.run(content, check=True)

                self._logger.info('K3s installed successfully.')
        except Exception as e:
            self._logger.warning(f'SSH connection failed: {e}')

    async def _create_network(self, name: str) -> Network:
        try:
            network = self.client.networks.create(
                name=name,
                ip_range='10.0.0.0/16',
                subnets=[NetworkSubnet(ip_range='10.0.1.0/24', network_zone='eu-central', type='cloud')],
            )
        except APIException as e:
            # TODO: add general exception handler, mapping Hetzner error (uniqueness_error, protected, ...)
            if e.code == 'uniqueness_error':
                self._logger.warning(f'Network with name "{name}" already exists')
                return self.client.networks.get_by_name(name)

            raise

        return network

    async def _create_ssh_key(self, name: str, public_key: str) -> SSHKey:
        try:
            ssh_key = self.client.ssh_keys.create(
                name=name,
                public_key=public_key,
            )
        except APIException as e:
            # TODO: add general exception handler, mapping Hetzner error (uniqueness_error, protected, ...)
            if e.code == 'uniqueness_error':
                self._logger.warning(f'SSHKey with name "{name}" already exists')
                return self.client.ssh_keys.get_by_name(name)

            raise

        return ssh_key

    async def _create_server(
        self,
        name: str,
        node_type: HetznerNodeType,
        node_region: HetznerRegion,
        user_data: str,
        placement_group: PlacementGroup,
        networks: list[Network],
        ssh_keys: list[SSHKey] | None = None,
        enable_public_ip: bool = False,
    ) -> dict:
        self._logger.info(f'Creating server {name}...')

        try:
            response = self.client.servers.create(
                name=name,
                server_type=ServerType(name=node_type),
                image=Image(name='ubuntu-22.04'),
                user_data=user_data,
                location=Location(name=node_region),
                placement_group=placement_group,
                networks=networks,
                ssh_keys=ssh_keys,
                public_net=ServerCreatePublicNetwork(enable_ipv4=enable_public_ip, enable_ipv6=enable_public_ip),
            )
        except APIException as e:
            if e.code == 'uniqueness_error':
                self._logger.warning(f'Server with name "{name}" already exists')
            elif e.code == 'resource_unavailable':
                self._logger.exception(f'Failed to get server with name "{name}"', exc_info=False)
                raise ResourceUnavailableError(f'Resource {name} unavailable') from e

            raise

        server = response.server

        self._logger.info(
            f'Created server {server.name=}, {server.status=}, IP={server.public_net.ipv4.ip}, waiting until k3s is installed'
        )

        await self._wait_until_server_is_initialised(server.id)
        await self._wait_until_cloud_init_finished(server.public_net.ipv4.ip, 'root')

        self._logger.info(f'Server {server.name} ready')

        return {'name': server.name, 'ip': server.public_net.ipv4.ip}

    async def _create_placement_group(self, name: str) -> PlacementGroup:
        try:
            placement_group_response: CreatePlacementGroupResponse = self.client.placement_groups.create(
                name=name, type='spread'
            )
        except APIException as e:
            if e.code == 'uniqueness_error':
                self._logger.warning(f'Placement Group with name "{name}" already exists')
                return self.client.placement_groups.get_by_name(name)

            raise

        return placement_group_response.placement_group

    def _can_create_cluster(self) -> bool:
        try:
            servers = self.client.servers.get_all()
        except APIException as e:
            if e.code == 'unauthorized':
                raise ValueError('Wrong Hetzner token provided') from e
            else:
                raise

        if servers:
            self._logger.warning(f'Project is not empty, found {len(servers)} servers')
            return False

        return True

    async def create_cluster(self, cluster_config: ClusterConfiguration) -> KubernetesCluster:
        if not self._can_create_cluster():
            raise ProjectNotEmptyError('Project is not empty, please delete existing resources first')

        k3s_token = generate_password(20)
        ssh_public_key_path = self._ssh_public_key_path

        if not ssh_public_key_path.exists():
            raise ValueError(f'SSH key path {ssh_public_key_path} does not exist')

        ssh_key_name = f'{cluster_config.name}-ssh-key'

        ssh_public_key = ssh_public_key_path.read_text()

        ssh_key = await self._create_ssh_key(ssh_key_name, ssh_public_key)

        private_network = await self._create_network(f'{cluster_config.name}-network')

        control_plane_pool = cluster_config.pools[0]
        control_plane_pool_name = f'{cluster_config.name}-{control_plane_pool.name}'
        control_plane_placement_group = await self._create_placement_group(control_plane_pool_name)

        control_plane_node_content = template_loader.render_template(
            template_name='cloud-init-master.yml',
            values={
                'k3s_token': k3s_token,
                'k3s_version': cluster_config.k3s_version,
                'pool_name': control_plane_pool_name,
            },
        )

        master_plane_node = await self._create_server(
            name=f'{cluster_config.name}-control-plane-node-1',
            node_type=HetznerNodeType[control_plane_pool.node_type.upper()],
            user_data=control_plane_node_content,
            node_region=HetznerRegion[control_plane_pool.region.upper()],
            placement_group=control_plane_placement_group,
            ssh_keys=[ssh_key],
            networks=[private_network],
            enable_public_ip=True,
        )

        master_plane_ip = master_plane_node['ip']

        tasks = [
            self._create_server(
                name=f'{cluster_config.name}-worker-node-{i}',
                node_type=HetznerNodeType[pool.node_type.upper()],
                user_data=template_loader.render_template(
                    template_name='cloud-init-worker.yml',
                    values={
                        'k3s_token': k3s_token,
                        'k3s_version': cluster_config.k3s_version,
                        'master_ip': master_plane_ip,
                        'pool_name': pool.name,
                    },
                ),
                node_region=HetznerRegion[pool.region.upper()],
                placement_group=await self._create_placement_group(f'{cluster_config.name}-{pool.name}'),
                networks=[private_network],
                ssh_keys=[ssh_key],
                enable_public_ip=True,
            )
            for i, pool in enumerate(
                pool
                for pool in cluster_config.pools[1:]
                for _ in range(pool.number_of_nodes)
                if not pool.autoscaling.enabled
            )
        ]

        worker_nodes = await asyncio.gather(*tasks)

        for s in [master_plane_node, *worker_nodes]:
            self._logger.info(f'Created server: {s["name"]} ({s["ip"]})')

        local_config = Path(PATH_TO_K3S_YAML_CONFIGS, 'k3s-config-cluster-id.yaml')

        await self._download_kubeconfig(
            ip=master_plane_node['ip'],
            username='root',
            remote_path='/etc/rancher/k3s/k3s.yaml',
            local_path=local_config,
        )

        text = local_config.read_text()
        local_config.write_text(text.replace('127.0.0.1', master_plane_node['ip']))
        self._logger.info(f'run export KUBECONFIG={local_config!s}')

        cluster = KubernetesCluster(cluster_config, master_plane_node['ip'], local_config)

        # TODO: remove hardcoded network name
        hcloud_secret_rendered = template_loader.render_template(
            template_name='hetzner-token-secret.yaml',
            template_module='kubernetes',
            values={'hcloud_token': self._config.api_token, 'network_name': f'{cluster_config.name}-network'},
        )

        is_autoscaling_requested = any(x.autoscaling.enabled for x in cluster_config.pools if x.autoscaling)

        if is_autoscaling_requested:
            worker_node_template_rendered = template_loader.render_template(
                template_name='cloud-init-autoscaler.yml',
                values={
                    'k3s_token': k3s_token,
                    'k3s_version': cluster_config.k3s_version,
                    'master_ip': cluster.access_ip,
                },
            )

            await cluster.install_clusterautoscaler(
                self._config.api_token, cluster_config, worker_node_template_rendered
            )

        cluster.create_object_from_content(yaml.safe_load(hcloud_secret_rendered))
        self._logger.info('Hetzner secret created')

        cluster.install_csi('hetzner')
        cluster.install_cloud_controller('hetzner')

        return cluster

    async def create_volume(self, name: str, size: int, region: str | None = None) -> None:
        try:
            self.client.volumes.create(
                name=name,
                size=size,
                location=Location(name=region or 'fsn1'),
            )
        except APIException as e:
            # TODO: add general exception handler, mapping Hetzner error (uniqueness_error, protected, ...)
            if e.code == 'uniqueness_error':
                raise ValueError(f'Volume with name "{name}" already exists') from e

            raise

    async def _download_kubeconfig(self, ip: str, username: str, remote_path: str, local_path: Path) -> None:
        try:
            async with asyncssh.connect(
                ip, username=username, client_keys=[self._ssh_private_key_path], known_hosts=None
            ) as conn:
                await asyncssh.scp((conn, remote_path), local_path)
                self._logger.info(f'File downloaded to {local_path}')
        except Exception as e:
            self._logger.exception(f'Failed to download file: {e}')

    def delete_cluster(self) -> None:
        try:
            servers = self.client.servers.get_all()
            placement_groups = self.client.placement_groups.get_all()
            networks = self.client.networks.get_all()
            ssh_keys = self.client.ssh_keys.get_all()
        except APIException as e:
            if e.code == 'unauthorized':
                self._logger.warning('Could not delete resources, please remove them manually from Hetzner console')
                return
            else:
                raise

        for x in servers + placement_groups + networks + ssh_keys:
            try:
                x.delete()
                self._logger.info(f'Removed resource {x}')
            except APIException as e:
                if e.code == 'not_found':
                    self._logger.warning(f'Cannot find resource {x} (might have been already deleted)')
                else:
                    raise

    def delete_volume(self, volume_name: str) -> None:
        try:
            volume = self.client.volumes.get_by_name(volume_name)
        except Exception as e:
            # TODO: handle non existing volume
            raise ValueError(f'Error while deleting volume: {e}') from e

        if volume:
            volume.delete()

    def get_volumes(self) -> list[Volume]:
        try:
            volumes = self.client.volumes.get_all()
        except Exception as e:
            raise ValueError(f'Error while fetching volumes: {e}') from e

        return volumes

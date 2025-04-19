from hcloud.placement_groups import PlacementGroup, CreatePlacementGroupResponse
from hcloud.servers import Server, CreateServerResponse

from src.core.providers.base_provider import BaseProvider
import asyncssh
import asyncio

from hcloud import Client, APIException
from hcloud.images import Image
from hcloud.server_types import ServerType
from hcloud.locations import Location
from src.core.kubernetes.kubernetes_cluster import KubernetesCluster
from src.core.kubernetes.configuration import ClusterConfiguration
from src.core.config import PATH_TO_K3S_YAML_CONFIGS, HCLOUD_TOKEN, K3S_TOKEN, SSH_PASSWORD
from traceback import format_exc

from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from enum import StrEnum


class HetznerNodeType(StrEnum):
    CX22 = "cx22"
    CX32 = "cx32"
    CX42 = "cx42"
    CX52 = "cx52"


class HetznerRegion(StrEnum):
    FSN1 = "fsn1"
    NBG1 = "nbg1"
    HEL1 = "hel1"


class HetznerProvider(BaseProvider):
    name = 'hetzner'

    def __init__(self):
        self.client = Client(token=HCLOUD_TOKEN)

        super().__init__()

    async def _wait_until_server_is_initialised(self, server_id):
        while True:
            server = await asyncio.to_thread(self.client.servers.get_by_id, server_id)

            if server.status == 'running':
                print(f'Server {server_id} is running.')
                break
            else:
                print(f'Server {server_id} not ready yet, status: {server.status}')
                await asyncio.sleep(2)

    async def _wait_until_cloud_init_finished(self, ip, username):
        while True:
            try:
                async with asyncssh.connect(ip, username=username, password=SSH_PASSWORD, known_hosts=None) as ssh:
                    result = await ssh.run('test -f /var/lib/cloud/instance/boot-finished && echo "done"', check=True)
                    if result.stdout.strip() == "done":
                        print("Cloud-init finished successfully.")
                        break
                    else:
                        print("Cloud-init still running...")
            except Exception as e:
                print(f"SSH connection failed: {e}")

            await asyncio.sleep(5)

    async def _create_server(self, name: str, node_type: HetznerNodeType, node_region: HetznerRegion, user_data: str, placement_group: PlacementGroup) -> dict:
        print(f"Creating server {name}...")

        try:
            response = self.client.servers.create(
                name=name,
                server_type=ServerType(name=node_type),
                image=Image(name="ubuntu-22.04"),
                user_data=user_data,
                location=Location(name=node_region),
                placement_group=placement_group
            )
        except APIException as e:
            if e.code == 'uniqueness_error':
                print(f'Server with name "{name}" already exists')

            raise

        server = response.server

        print(f"Created server {server.name=}, {server.status=}, IP={server.public_net.ipv4.ip}, waiting until k3s is installed")

        await self._wait_until_server_is_initialised(server.id)
        await self._wait_until_cloud_init_finished(server.public_net.ipv4.ip, 'root')

        print(f'Server {server.name} ready')

        return {'name': server.name, 'ip': server.public_net.ipv4.ip}

    async def _create_placement_group(self, name: str) -> PlacementGroup:
        try:
            placement_group_response: CreatePlacementGroupResponse = self.client.placement_groups.create(name=name, type='spread')
        except APIException as e:
            if e.code == 'uniqueness_error':
                print(f'Placement Group with name "{name}" already exists')
                return self.client.placement_groups.get_by_name(name)

            raise

        return placement_group_response.placement_group

    async def create_cluster(self, cluster_config: ClusterConfiguration) -> KubernetesCluster:
        environment = Environment(
            loader=FileSystemLoader(Path(Path(__file__).parent.parent.parent.resolve(), 'templates')), autoescape=True
        )

        control_plane_pool = cluster_config.pools[0]
        control_plane_pool_name = f"{cluster_config.name}-{control_plane_pool.name}"
        control_plane_placement_group = await self._create_placement_group(control_plane_pool_name)

        control_plane_node_template = environment.get_template('cloud-init-master.yml')
        control_plane_node_content = control_plane_node_template.render(
            k3s_token=K3S_TOKEN,
            k3s_version=cluster_config.k3s_version,
            pool_name=control_plane_pool_name,
        )

        master_plane_node = await self._create_server(
            name=f"{cluster_config.name}-control-plane-node-1",
            node_type=HetznerNodeType[control_plane_pool.node_type.upper()],
            user_data=control_plane_node_content,
            node_region=HetznerRegion[control_plane_pool.region.upper()],
            placement_group=control_plane_placement_group
        )

        worker_node_template = environment.get_template('cloud-init-worker.yml')
        worker_node_content = worker_node_template.render(k3s_token=K3S_TOKEN, master_ip=master_plane_node['ip'],
                                                                 pool_name=control_plane_pool_name)

        total_num_of_nodes = sum(x.number_of_nodes for x in cluster_config.pools[1:])
        print(f'Total nodes to create: {total_num_of_nodes}')

        tasks_dry = [
            {
                "name": f"{cluster_config.name}-worker-node-{i}",
                "node_type": pool.node_type.upper(),
                "node_region": pool.region.upper(),
                "placement_group": f'{cluster_config.name}-{pool.name}'
            }
            for i, pool in enumerate(
                pool
                for pool in cluster_config.pools[1:]
                for _ in range(pool.number_of_nodes)
            )
        ]

        print(f'will create the following ndoes: {tasks_dry}')

        tasks = [
            self._create_server(
                name=f"{cluster_config.name}-worker-node-{i}",
                node_type=HetznerNodeType[pool.node_type.upper()],
                user_data=worker_node_template.render(
                    k3s_token=K3S_TOKEN,
                    k3s_version=cluster_config.k3s_version,
                    master_ip=master_plane_ip,
                    pool_name=pool.name,
                ),
                node_region=HetznerRegion[pool.region.upper()],
                placement_group=await self._create_placement_group(f'{cluster_config.name}-{pool.name}')
            )
            for i, pool in enumerate(
                pool
                for pool in cluster_config.pools[1:]
                for _ in range(pool.number_of_nodes)
            )
        ]

        worker_nodes = await asyncio.gather(*tasks)
        print(worker_nodes)

        for s in [master_plane_node] + worker_nodes:
            print(f"{s['name']} ({s['ip']})")

        local_config = Path(PATH_TO_K3S_YAML_CONFIGS, f'k3s-config-cluster-id.yaml')

        await self._download_kubeconfig(
            ip=master_plane_node['ip'],
            username='root',
            password=SSH_PASSWORD,
            remote_path='/etc/rancher/k3s/k3s.yaml',
            local_path=local_config
        )

        text = local_config.read_text()
        local_config.write_text(text.replace('127.0.0.1', master_plane_node['ip']))
        print(f'run export KUBECONFIG={str(local_config)}')

        return KubernetesCluster(cluster_config, master_plane_node['ip'], local_config)

    async def _download_kubeconfig(self, ip, username, password, remote_path, local_path):
        try:
            async with asyncssh.connect(ip, username=username, password=password, known_hosts=None) as conn:
                await asyncssh.scp((conn, remote_path), local_path)
                print(f"File downloaded to {local_path}")
        except Exception as e:
            print(f"Failed to download file: {e}")
            print(format_exc())

    def delete_cluster(self):
        servers = self.client.servers.get_all()
        placement_groups = self.client.placement_groups.get_all()

        for x in servers + placement_groups:
            x.delete()
            print(f'Removed resource {x}')


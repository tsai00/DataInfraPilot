from src.core.providers.base_provider import BaseProvider
import asyncssh
import asyncio

from hcloud import Client
from hcloud.images import Image
from hcloud.server_types import ServerType
from src.core.kubernetes.kubernetes_cluster import KubernetesCluster
from src.core.kubernetes.configuration import ClusterConfiguration
from src.core.config import PATH_TO_K3S_YAML_CONFIGS, HCLOUD_TOKEN, K3S_TOKEN, SSH_PASSWORD
from traceback import format_exc

from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import os

class HetznerProvider(BaseProvider):
    def __init__(self):
        self.client = Client(token=os.environ.get('HCLOUD_TOKEN'))

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

    async def _create_master_nodes(self, num: int):
        environment = Environment(
            loader=FileSystemLoader(Path(Path(__file__).parent.parent.parent.resolve(), 'templates')), autoescape=True
        )

        template = environment.get_template('cloud-init-master.yml')
        content = template.render(k3s_token=K3S_TOKEN)

        response = self.client.servers.create(
            name="k8s-master-node-1",
            server_type=ServerType(name="cx22"),
            image=Image(name="ubuntu-22.04"),
            user_data=content,
        )
        server = response.server
        print(f"Creating server {server.name=}, {server.status=}, IP={server.public_net.ipv4.ip}")

        await self._wait_until_server_is_initialised(server.id)
        await self._wait_until_cloud_init_finished(server.public_net.ipv4.ip, 'root')
        print(f'Server {server.name} ready')

        return {'name': server.name, 'ip': server.public_net.ipv4.ip}

    async def _create_single_worker_node(self, i, content, master_ip):
        response = self.client.servers.create(
            name=f"k8s-worker-node-{i}",
            server_type=ServerType(name="cx22"),
            image=Image(name="ubuntu-22.04"),
            user_data=content
        )
        server = response.server
        print(f"Creating server {server.name=}, {server.status=}, IP={server.public_net.ipv4.ip}")

        await self._wait_until_server_is_initialised(server.id)
        await self._wait_until_cloud_init_finished(server.public_net.ipv4.ip, 'root')

        print(f'Server {server.name} ready')
        return {'name': server.name, 'ip': server.public_net.ipv4.ip}

    async def _create_worker_nodes(self, num: int, master_ip):
        environment = Environment(
            loader=FileSystemLoader(Path(Path(__file__).parent.parent.parent.resolve(), 'templates')), autoescape=True
        )

        template = environment.get_template('cloud-init-worker.yml')
        content = template.render(k3s_token=K3S_TOKEN, master_ip=master_ip)

        servers = []

        tasks = [
            self._create_single_worker_node(i, content, master_ip) for i in range(num)
        ]
        results = await asyncio.gather(*tasks)

        return results

    async def create_cluster(self, cluster_config: ClusterConfiguration) -> KubernetesCluster:
        master_plane = await self._create_master_nodes(cluster_config.num_of_master_nodes)
        workers = await self._create_worker_nodes(cluster_config.num_of_worker_nodes, master_plane['ip'])

        for s in [master_plane] + workers:
            print(f"{s['name']} ({s['ip']})")

        local_config = Path(PATH_TO_K3S_YAML_CONFIGS, f'k3s-config-cluster-id.yaml')

        await self._download_kubeconfig(
            ip=master_plane['ip'],
            username='root',
            password=SSH_PASSWORD,
            remote_path='/etc/rancher/k3s/k3s.yaml',
            local_path=local_config
        )

        text = local_config.read_text()
        local_config.write_text(text.replace('127.0.0.1', master_plane['ip']))
        print(f'run export KUBECONFIG={str(local_config)}')

        return KubernetesCluster(cluster_config, master_plane['ip'], local_config)

    async def _download_kubeconfig(self, ip, username, password, remote_path, local_path):
        try:
            async with asyncssh.connect(ip, username=username, password=password, known_hosts=None) as conn:
                await asyncssh.scp((conn, remote_path), local_path)
                print(f"File downloaded to {local_path}")
        except Exception as e:
            print(f"Failed to download file: {e}")
            print(format_exc())

    def delete_cluster(self):
        response = self.client.servers.get_all()

        for x in response:
            x.delete()
            print(f'Removed server {x}')


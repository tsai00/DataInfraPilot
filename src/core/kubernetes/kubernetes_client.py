import time
import traceback

from kubernetes import client, config, utils
from kubernetes.client import ApiException, Configuration
from kubernetes.dynamic.client import DynamicClient
from kubernetes.dynamic.exceptions import NotFoundError
from pathlib import Path
import yaml
from kubernetes.stream import stream
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class KubernetesClients:
    def __init__(self):
        self.Api = client.ApiClient()
        self.Core = client.CoreV1Api()  # Pods, Services, ConfigMaps
        self.Apps = client.AppsV1Api()  # Deployments, StatefulSets, DaemonSets
        self.Batch = client.BatchV1Api()  # Jobs, CronJobs
        self.Networking = client.NetworkingV1Api()  # Ingress, NetworkPolicies
        self.RBAC = client.RbacAuthorizationV1Api()  # Role-Based Access Control
        self.CustomObjects = client.CustomObjectsApi()  # Custom Resources (CRDs)
        self.Namespaces = client.V1Namespace()

        self.Dynamic = DynamicClient(client.ApiClient())


class KubernetesClient:
    def __init__(self, kubeconfig_path: Path):
        config.load_kube_config(str(kubeconfig_path))

        Configuration._default.verify_ssl = False

        self._clients = KubernetesClients()

    def install_from_content(self, yaml_content: dict | list[dict]):
        if isinstance(yaml_content, dict):
            yaml_content = [yaml_content]

        try:
            utils.create_from_yaml(self._clients.Api, yaml_objects=yaml_content)
            print(f'Custom object installed successfully!')
        except Exception as e:
            print(f'Error while installing object: {e}')
            print(traceback.format_exc())

    def install_from_yaml(self, path_to_yaml: Path, with_custom_objects: bool = False):
        if path_to_yaml.is_dir():
            utils.create_from_directory(self._clients.CustomObjects, str(path_to_yaml))
        else:
            if with_custom_objects:
                print('Applying custom objects')
                manifest = yaml.safe_load(path_to_yaml.read_text())
                self._apply_simple_item(manifest)
            else:
                manifest = [x for x in yaml.safe_load_all(path_to_yaml.read_text())]
                utils.create_from_yaml(self._clients.Api, yaml_objects=manifest)

    def _apply_simple_item(self, manifest: dict, verbose: bool = False):
        api_version = manifest.get("apiVersion")
        kind = manifest.get("kind")
        resource_name = manifest.get("metadata").get("name")
        namespace = manifest.get("metadata").get("namespace")
        crd_api = self._clients.Dynamic.resources.get(api_version=api_version, kind=kind)

        try:
            crd_api.get(namespace=namespace, name=resource_name)
            crd_api.patch(body=manifest, content_type="application/merge-patch+json")
            if verbose:
                print(f"{namespace}/{resource_name} patched")
        except NotFoundError:
            crd_api.create(body=manifest, namespace=namespace)
            if verbose:
                print(f"{namespace}/{resource_name} created")

    def execute_command(self, pod: str, namespace: str, command: list[str], interactive: bool = False,
                        command_input: str = None):
        print(f"Executing command: {pod=}, {namespace=}, {command=}, {interactive=}, {command_input=}")
        try:
            resp = self._clients.Core.read_namespaced_pod(name=pod, namespace=namespace)
        except ApiException as e:
            if e.status != 404:
                raise ValueError(f"Unknown error: {e}")
            print(f"Pod '{pod}' in namespace '{namespace}' not found.")
            return None, f"Pod '{pod}' not found."

        while resp.status.phase != 'Running':
            print(f'Pod not ready yet: {resp.status.phase}...')
            resp = self._clients.Core.read_namespaced_pod(name=pod, namespace=namespace)
            time.sleep(3)

        resp = stream(
            self._clients.Core.connect_get_namespaced_pod_exec,
            name=pod,
            namespace=namespace,
            command=command,
            stderr=True,
            stdin=interactive,
            stdout=True,
            tty=interactive,
            _preload_content=False
        )

        output = ''
        errors = ''

        while resp.is_open():
            resp.update(timeout=1)
            if resp.peek_stdout():
                output += resp.read_stdout()
            if resp.peek_stderr():
                errors += resp.read_stderr()
            if command_input:
                resp.write_stdin(command_input + "\n")

        return output, errors

    def create_namespace(self, namespace: str):
        self._clients.Core.create_namespace(client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace)))

    def delete_namespace(self, namespace: str):
        try:
            self._clients.Core.delete_namespace(namespace)
        except Exception as e:
            print(f'Error while deleting namespace {namespace}: {e}')

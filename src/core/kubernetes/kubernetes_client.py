import json
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
import base64
from dataclasses import dataclass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass(frozen=True)
class KubernetesClients:
    api = client.ApiClient()
    core = client.CoreV1Api()  # Pods, Services, ConfigMaps
    apps = client.AppsV1Api()  # Deployments, StatefulSets, DaemonSets
    batch = client.BatchV1Api()  # Jobs, CronJobs
    networking = client.NetworkingV1Api()  # Ingress, NetworkPolicies
    rbac = client.RbacAuthorizationV1Api()  # Role-Based Access Control
    custom_objects = client.CustomObjectsApi()  # Custom Resources (CRDs)
    namespaces = client.V1Namespace()
    dynamic = DynamicClient(client.ApiClient())


class KubernetesClient:
    def __init__(self, kubeconfig_path: Path):
        config.load_kube_config(str(kubeconfig_path))

        Configuration._default.verify_ssl = False

        self._clients = KubernetesClients()

    def install_from_content(self, yaml_content: dict | list[dict]):
        if isinstance(yaml_content, dict):
            yaml_content = [yaml_content]

        try:
            utils.create_from_yaml(self._clients.api, yaml_objects=yaml_content)
            print(f'Custom object installed successfully!')
        except Exception as e:
            print(f'Error while installing object: {e}')
            print(traceback.format_exc())

    def cordon_node(self, node_name: str):
        body = {
            "spec": {
                "unschedulable": True,
            },
        }

        print(f'Cordoning node: {node_name}')
        self._clients.core.patch_node(node_name, body)
        print(f'Node {node_name} cordoned successfully!')

    def install_from_yaml(self, path_to_yaml: Path, with_custom_objects: bool = False):
        if path_to_yaml.is_dir():
            utils.create_from_directory(self._clients.custom_objects, str(path_to_yaml))
        else:
            if with_custom_objects:
                print('Applying custom objects')
                manifest = yaml.safe_load(path_to_yaml.read_text())
                self._apply_simple_item(manifest)
            else:
                manifest = [x for x in yaml.safe_load_all(path_to_yaml.read_text())]
                utils.create_from_yaml(self._clients.api, yaml_objects=manifest)

    def _apply_simple_item(self, manifest: dict, verbose: bool = False):
        api_version = manifest.get("apiVersion")
        kind = manifest.get("kind")
        resource_name = manifest.get("metadata").get("name")
        namespace = manifest.get("metadata").get("namespace")
        crd_api = self._clients.dynamic.resources.get(api_version=api_version, kind=kind)

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
            resp = self._clients.core.read_namespaced_pod(name=pod, namespace=namespace)
        except ApiException as e:
            if e.status != 404:
                raise ValueError(f"Unknown error: {e}")
            print(f"Pod '{pod}' in namespace '{namespace}' not found.")
            return None, f"Pod '{pod}' not found."

        while resp.status.phase != 'Running':
            print(f'Pod not ready yet: {resp.status.phase}...')
            resp = self._clients.core.read_namespaced_pod(name=pod, namespace=namespace)
            time.sleep(3)

        resp = stream(
            self._clients.core.connect_get_namespaced_pod_exec,
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
        self._clients.core.create_namespace(client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace)))

    def delete_namespace(self, namespace: str):
        try:
            self._clients.core.delete_namespace(namespace)
        except Exception as e:
            print(f'Error while deleting namespace {namespace}: {e}')

    def create_docker_registry_secret(self, secret_name: str, registry_url: str, registry_username: str, registry_password: str, namespace: str = "default"):
        print(f'Creating secret {secret_name} of type "docker-registry"')

        cred_payload = {
            "auths": {
                registry_url: {
                    "username": registry_username,
                    "password": registry_password,
                }
            }
        }

        data = {
            ".dockerconfigjson": base64.b64encode(
                json.dumps(cred_payload).encode()
            ).decode()
        }

        secret = client.V1Secret(
            api_version="v1",
            data=data,
            kind="Secret",
            metadata=dict(name=secret_name, namespace=namespace),
            type="kubernetes.io/dockerconfigjson",
        )

        self._clients.core.create_namespaced_secret(namespace, body=secret)

        print(f'Secret {secret_name} of type "docker-registry" created successfully!')

    def create_secret(self, secret_name: str, namespace: str, data: dict[str, str]):
        print(f'Creating secret {secret_name}')

        secret = client.V1Secret(
            api_version="v1",
            kind="Secret",
            metadata=client.V1ObjectMeta(name=secret_name, namespace=namespace),
            string_data=data,
        )
        self._clients.core.create_namespaced_secret(namespace=namespace, body=secret)
        print(f'Secret {secret_name} created successfully!')

    def get_secret(self, secret_name: str, namespace: str):
        try:
            secret = self._clients.core.read_namespaced_secret(secret_name, namespace)
            return {k: base64.b64decode(v) for k, v in secret.data.items()} if secret.data is not None else None
        except ApiException as e:
            if e.status == 404:
                print(f"Secret '{secret_name}' not found in namespace '{namespace}'.")
            else:
                print(f"Error retrieving secret '{secret_name}': {e}")
        return None

import base64
import json
import time
from pathlib import Path

import urllib3
import yaml
from kubernetes import client, config, utils
from kubernetes.client import ApiException, Configuration
from kubernetes.dynamic.client import DynamicClient
from kubernetes.dynamic.exceptions import NotFoundError
from kubernetes.stream import stream

from src.core.utils import setup_logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class KubernetesClients:
    def __init__(self):
        self.api = client.ApiClient()
        self.core = client.CoreV1Api()  # Pods, Services, ConfigMaps
        self.apps = client.AppsV1Api()  # Deployments, StatefulSets, DaemonSets
        self.batch = client.BatchV1Api()  # Jobs, CronJobs
        self.networking = client.NetworkingV1Api()  # Ingress, NetworkPolicies
        self.rbac = client.RbacAuthorizationV1Api()  # Role-Based Access Control
        self.custom_objects = client.CustomObjectsApi()  # Custom Resources (CRDs)
        self.namespaces = client.V1Namespace()

        self.dynamic = DynamicClient(client.ApiClient())


class KubernetesClient:
    def __init__(self, kubeconfig_path: Path):
        self._logger = setup_logger('KubernetesClient')
        config.load_kube_config(str(kubeconfig_path))

        Configuration._default.verify_ssl = False

        self._clients = KubernetesClients()

    def install_from_content(self, yaml_content: dict | list[dict]):
        if isinstance(yaml_content, dict):
            yaml_content = [yaml_content]

        try:
            utils.create_from_yaml(self._clients.api, yaml_objects=yaml_content)
            self._logger.info('Custom object installed successfully!')
        except Exception as e:
            self._logger.exception(f'Error while installing object: {e}', exc_info=True)

    def cordon_node(self, node_name: str):
        body = {
            "spec": {
                "unschedulable": True,
            },
        }

        self._logger.debug(f'Cordoning node: {node_name}')
        self._clients.core.patch_node(node_name, body)
        self._logger.info(f'Node {node_name} cordoned successfully!')

    def install_from_yaml(self, path_to_yaml: Path, with_custom_objects: bool = False):
        if path_to_yaml.is_dir():
            utils.create_from_directory(self._clients.custom_objects, str(path_to_yaml))
        else:
            if with_custom_objects:
                self._logger.info('Applying custom objects...')
                manifest = yaml.safe_load(path_to_yaml.read_text())
                self._apply_simple_item(manifest)
            else:
                manifest = list(yaml.safe_load_all(path_to_yaml.read_text()))
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
                self._logger.info(f"{namespace}/{resource_name} patched")
        except NotFoundError:
            crd_api.create(body=manifest, namespace=namespace)
            if verbose:
                self._logger.info(f"{namespace}/{resource_name} created")

    def execute_command(self, pod: str, namespace: str, command: list[str], interactive: bool = False,
                        command_input: str = None):
        self._logger.info(f"Executing command: {pod=}, {namespace=}, {command=}, {interactive=}, {command_input=}")
        try:
            resp = self._clients.core.read_namespaced_pod(name=pod, namespace=namespace)
        except ApiException as e:
            if e.status != 404:
                raise ValueError(f"Unknown error during command execution: {e}") from e
            self._logger.exception(f"Pod '{pod}' in namespace '{namespace}' not found.", exc_info=False)
            return None, f"Pod '{pod}' not found."

        while resp.status.phase != 'Running':
            self._logger.info(f'Pod not ready yet: {resp.status.phase}...')
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
            self._logger.exception(f'Error while deleting namespace {namespace}: {e}', exc_info=False)

    def create_docker_registry_secret(self, secret_name: str, registry_url: str, registry_username: str, registry_password: str, namespace: str = "default"):
        self._logger.info(f'Creating secret {secret_name} of type "docker-registry"')

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
            metadata={'name': 'secret_name', 'namespace': 'namespace'},
            type="kubernetes.io/dockerconfigjson",
        )

        self._clients.core.create_namespaced_secret(namespace, body=secret)

        self._logger.info(f'Secret {secret_name} of type "docker-registry" created successfully!')

    def create_secret(self, secret_name: str, namespace: str, data: dict[str, str]):
        self._logger.info(f'Creating secret {secret_name}')

        secret = client.V1Secret(
            api_version="v1",
            kind="Secret",
            metadata=client.V1ObjectMeta(name=secret_name, namespace=namespace),
            string_data=data,
        )
        self._clients.core.create_namespaced_secret(namespace=namespace, body=secret)
        self._logger.info(f'Secret {secret_name} created successfully!')

    def get_secret(self, secret_name: str, namespace: str):
        try:
            secret = self._clients.core.read_namespaced_secret(secret_name, namespace)
            return {k: base64.b64decode(v) for k, v in secret.data.items()} if secret.data is not None else None
        except ApiException as e:
            if e.status == 404:
                msg = f"Secret '{secret_name}' not found in namespace '{namespace}'."
            else:
                msg = f"Error retrieving secret '{secret_name}': {e}"

            self._logger.exception(msg, exc_info=False)
            raise ValueError(msg) from e

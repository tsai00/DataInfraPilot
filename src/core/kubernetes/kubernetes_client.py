import traceback

from kubernetes import client, config, utils
from kubernetes.dynamic.client import DynamicClient
from kubernetes.dynamic.exceptions import NotFoundError
from pathlib import Path
import yaml


class KubernetesClients:
    def __init__(self):
        self.Api = client.ApiClient()
        self.Core = client.CoreV1Api()  # Pods, Services, ConfigMaps
        self.Apps = client.AppsV1Api()  # Deployments, StatefulSets, DaemonSets
        self.Batch = client.BatchV1Api()  # Jobs, CronJobs
        self.Networking = client.NetworkingV1Api()  # Ingress, NetworkPolicies
        self.RBAC = client.RbacAuthorizationV1Api()  # Role-Based Access Control
        self.CustomObjects = client.CustomObjectsApi()  # Custom Resources (CRDs)

        self.Dynamic = DynamicClient(client.ApiClient())


class KubernetesClient:
    def __init__(self, kubeconfig_path: Path):
        config.load_kube_config(str(kubeconfig_path))

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

    def delete_namespace(self, namespace: str):
        self._clients.Core.delete_namespace(namespace)

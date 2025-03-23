from kubernetes import client, config, utils
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


class KubernetesClient:
    def __init__(self, kubeconfig_path: Path):
        config.load_kube_config(str(kubeconfig_path))

        self._clients = KubernetesClients()

    def install_from_yaml(self, path_to_yaml: Path):
        if path_to_yaml.is_dir():
            utils.create_from_directory(self._clients.Api, str(path_to_yaml))
        else:
            utils.create_from_yaml(self._clients.Api, str(path_to_yaml))

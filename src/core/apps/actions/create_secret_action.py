from typing import override

from src.core.apps.actions.base_post_install_action import BasePrePostInstallAction
from src.core.kubernetes.kubernetes_cluster import KubernetesCluster


class CreateSecretAction(BasePrePostInstallAction):
    def __init__(self, name: str, secret_name: str, secret_data: dict, secret_type: str | None = None, condition: bool = True):
        self.secret_name = secret_name
        self.secret_data = secret_data
        self.secret_type = secret_type

        super().__init__(name=name, condition=condition)

    @override
    def run(self, cluster: KubernetesCluster, namespace: str, *args, **kwargs):
        cluster.create_secret(self.secret_name, namespace, self.secret_data, self.secret_type)

    def _validate(self):
        if self.secret_type not in ('docker-registry', 'regular'):
            raise ValueError(f'Unknown secret type {self.secret_type}.')

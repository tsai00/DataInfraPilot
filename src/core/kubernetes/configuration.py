from dataclasses import dataclass


# TODO add ClusterInfo dataclass and rename this to ClusterInputConfiguration


@dataclass(frozen=True)
class ClusterConfiguration:
    name: str = 'k8s-cluster'
    num_of_master_nodes: int = 1
    num_of_worker_nodes: int = 3
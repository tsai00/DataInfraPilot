from dataclasses import dataclass, field

from src.api.schemas.cluster import ClusterPool


# TODO add ClusterInfo dataclass and rename this to ClusterInputConfiguration


@dataclass(frozen=True)
class ClusterConfiguration:
    name: str = 'k8s-cluster'
    pools: list[ClusterPool] = field(default_factory=list)
from dataclasses import dataclass, field

from src.api.schemas.cluster import ClusterPool, ClusterAdditionalComponents


# TODO add ClusterInfo dataclass and rename this to ClusterInputConfiguration

@dataclass(frozen=True)
class ClusterConfiguration:
    name: str
    k3s_version: str
    domain_name: str | None
    pools: list[ClusterPool] = field(default_factory=list)
    additional_components: ClusterAdditionalComponents = field(default_factory=dict)
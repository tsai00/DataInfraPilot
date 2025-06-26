from dataclasses import dataclass


@dataclass(frozen=True)
class HelmChart:
    name: str
    repo_url: str
    version: str
    is_oci: bool = False

from dataclasses import dataclass


@dataclass(frozen=True)
class ChartConfig:
    name: str
    repo_url: str
    version: str
    values: dict
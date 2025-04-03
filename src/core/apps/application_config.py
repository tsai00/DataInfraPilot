from dataclasses import dataclass


@dataclass(frozen=True)
class ApplicationConfig:
    id: int
    config: dict
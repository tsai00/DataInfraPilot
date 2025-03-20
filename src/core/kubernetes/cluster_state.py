from enum import StrEnum


class ClusterState(StrEnum):
    PROVISIONING = 'provisioning'
    RUNNING = 'running'
    FAILED = 'failed'
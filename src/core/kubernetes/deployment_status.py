from enum import StrEnum


class DeploymentStatus(StrEnum):
    RUNNING = "running"
    DEPLOYING = "deploying"
    FAILED = "failed"
    DELETING = "deleting"
    CREATING = "creating"
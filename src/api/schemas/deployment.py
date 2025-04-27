from datetime import datetime

from pydantic import BaseModel


class DeploymentUpdateSchema(BaseModel):
    application_id: int
    config: dict

    class Config:
        from_attributes = True


class DeploymentCreateSchema(DeploymentUpdateSchema):
    node_pool: str

    class Config:
        from_attributes = True


class DeploymentSchema(DeploymentCreateSchema):
    id: int
    cluster_id: int
    status: str
    namespace: str
    installed_at: datetime

    class Config:
        from_attributes = True

from datetime import datetime

from pydantic import BaseModel


class DeploymentCreateSchema(BaseModel):
    application_id: int
    config: dict

    class Config:
        orm_mode = True


class DeploymentSchema(DeploymentCreateSchema):
    id: int
    cluster_id: int
    status: str
    namespace: str
    installed_at: datetime

    class Config:
        orm_mode = True

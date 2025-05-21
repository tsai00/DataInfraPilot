from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EndpointAccessConfig(BaseModel):
    name: str
    access_type: Literal["subdomain", "domain_path", "ip"]
    value: str = Field(default="")
    description: str = Field(default="")


class DeploymentVolumeSchema(BaseModel):
    volume_type: Literal["new", "existing"]
    name: str
    size: int

    class Config:
        from_attributes = True


class DeploymentUpdateSchema(BaseModel):
    application_id: int
    config: dict

    class Config:
        from_attributes = True


class DeploymentCreateSchema(DeploymentUpdateSchema):
    name: str
    node_pool: str | None
    volumes: list[DeploymentVolumeSchema] | None
    endpoints: list[EndpointAccessConfig]

    class Config:
        from_attributes = True


class DeploymentSchema(BaseModel):
    id: int
    name: str
    cluster_id: int
    application_id: int
    config: dict
    status: str
    namespace: str
    installed_at: datetime
    error_message: str
    node_pool: str | None
    endpoints: list[EndpointAccessConfig]

    class Config:
        from_attributes = True

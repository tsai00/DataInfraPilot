from pydantic import BaseModel, Field
from datetime import datetime

from src.api.schemas.application import ClusterApplicationSchema, ApplicationSchema


class ClusterPool(BaseModel):
    name: str
    node_type: str
    region: str
    number_of_nodes: int

    def to_dict(self):
        return {'name': self.name, 'node_type': self.node_type, 'region': self.region, 'number_of_nodes': self.number_of_nodes}


class ClusterCreateSchema(BaseModel):
    name: str
    k3s_version: str
    provider: str
    pools: list[ClusterPool]


class ClusterSchema(ClusterCreateSchema):
    id: int
    status: str
    error_message: str
    access_ip: str
    created_at: datetime
    cluster_applications: list[ClusterApplicationSchema] = Field(default=[])

    class Config:
        orm_mode = True


class ClusterCreateResponseSchema(BaseModel):
    name: str
    status: str
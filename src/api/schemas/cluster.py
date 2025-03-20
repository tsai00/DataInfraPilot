from pydantic import BaseModel
from datetime import datetime


class ClusterCreateSchema(BaseModel):
    name: str
    provider: str
    region: str
    num_of_master_nodes: int
    num_of_worker_nodes: int


class ClusterSchema(ClusterCreateSchema):
    id: int
    status: str
    created_at: datetime

    class Config:
        orm_mode = True


class ClusterCreateResponseSchema(BaseModel):
    id: int
    status: str
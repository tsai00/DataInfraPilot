from datetime import datetime

from pydantic import BaseModel


class ApplicationSchema(BaseModel):
    id: int
    name: str
    description: str

    class Config:
        orm_mode = True


class ClusterApplicationCreateSchema(BaseModel):
    id: int
    config: dict

    class Config:
        orm_mode = True


class ClusterApplicationSchema(ClusterApplicationCreateSchema):
    cluster_id: int
    application_id: int
    status: str
    installed_at: datetime

    class Config:
        orm_mode = True






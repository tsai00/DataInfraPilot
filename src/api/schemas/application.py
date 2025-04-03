from datetime import datetime

from pydantic import BaseModel


class ApplicationSchema(BaseModel):
    id: int
    name: str
    description: str

    class Config:
        orm_mode = True


class ClusterApplicationSchema(BaseModel):
    id: int
    cluster_id: int
    application_id: int
    config: dict
    status: str
    installed_at: datetime

    class Config:
        orm_mode = True


class ClusterApplicationCreateSchema(BaseModel):
    id: int
    config: dict

    class Config:
        orm_mode = True


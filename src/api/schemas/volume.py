from datetime import datetime

from pydantic import BaseModel


class VolumeCreateSchema(BaseModel):
    provider: str
    region: str
    name: str
    size: int

    class Config:
        from_attributes = True


class VolumeSchema(VolumeCreateSchema):
    id: int
    status: str
    error_message: str
    created_at: datetime

    class Config:
        from_attributes = True


class VolumeCreateResponseSchema(BaseModel):
    name: str
    status: str

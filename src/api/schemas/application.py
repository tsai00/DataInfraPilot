from pydantic import BaseModel


class ApplicationSchema(BaseModel):
    id: int
    name: str
    description: str

    class Config:
        from_attributes = True

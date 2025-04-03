from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class BaseModel(MappedAsDataclass, DeclarativeBase):
    pass
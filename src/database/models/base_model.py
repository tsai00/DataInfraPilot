from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class BaseModel(DeclarativeBase, MappedAsDataclass):
    pass
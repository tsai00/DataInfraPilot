from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column

from src.database.models import BaseModel


class Application(BaseModel):
    __tablename__ = 'application'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)

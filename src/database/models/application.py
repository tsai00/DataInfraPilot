from __future__ import annotations

from sqlalchemy.orm import mapped_column, Mapped
from src.database.models.base_model import BaseModel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.models.deployment import Deployment


class Application(BaseModel):
    __tablename__ = 'application'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
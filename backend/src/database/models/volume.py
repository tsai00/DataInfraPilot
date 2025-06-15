from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from src.database.models import BaseModel


class Volume(BaseModel):
    __tablename__ = 'volume'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    provider: Mapped[str] = mapped_column(nullable=False)
    region: Mapped[str] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    size: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    error_message: Mapped[str] = mapped_column(nullable=True, default='')
    description: Mapped[str] = mapped_column(nullable=True, default='')
    created_at: Mapped[datetime] = mapped_column(nullable=False, default_factory=lambda: datetime.now())

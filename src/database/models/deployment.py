from __future__ import annotations
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import ForeignKey, JSON
from src.database.models.base_model import BaseModel
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.models.cluster import Cluster
    from src.database.models.application import Application


class Deployment(BaseModel):
    __tablename__ = 'deployment'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    cluster_id: Mapped[int] = mapped_column(ForeignKey("cluster.id", ondelete='CASCADE'), nullable=False)
    application_id: Mapped[int] = mapped_column(ForeignKey("application.id", ondelete='CASCADE'), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default_factory=dict)
    status: Mapped[str] = mapped_column(nullable=False, default="deploying")
    installed_at: Mapped[datetime] = mapped_column(nullable=False, default_factory=lambda: datetime.now())

    cluster: Mapped[Cluster] = relationship(back_populates="deployments", init=False)
    application: Mapped[Application] = relationship(init=False)

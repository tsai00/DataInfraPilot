from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.deployment_status import DeploymentStatus
from src.database.models import BaseModel

if TYPE_CHECKING:
    from src.database.models import Application, Cluster


class Deployment(BaseModel):
    __tablename__ = 'deployment'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    name: Mapped[str] = mapped_column(nullable=False)
    cluster_id: Mapped[int] = mapped_column(ForeignKey('cluster.id', ondelete='CASCADE'), nullable=False)
    application_id: Mapped[int] = mapped_column(ForeignKey('application.id', ondelete='CASCADE'), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default_factory=dict)
    status: Mapped[str] = mapped_column(nullable=False, default=DeploymentStatus.CREATING)
    installed_at: Mapped[datetime] = mapped_column(nullable=False, default_factory=lambda: datetime.now())
    namespace: Mapped[str] = mapped_column(nullable=False, default='')
    error_message: Mapped[str] = mapped_column(nullable=True, default='')
    node_pool: Mapped[str] = mapped_column(nullable=True, default='')
    endpoints: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default_factory=list)

    cluster: Mapped[Cluster] = relationship(back_populates='deployments', init=False)
    application: Mapped[Application] = relationship(init=False)

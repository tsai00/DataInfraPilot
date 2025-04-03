from __future__ import annotations

from sqlalchemy.orm import mapped_column, Mapped, relationship
from datetime import datetime
from src.database.models.base_model import BaseModel

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.models.cluster_application import ClusterApplication


class Cluster(BaseModel):
    __tablename__ = 'cluster'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    name: Mapped[str] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(nullable=False)
    region: Mapped[str] = mapped_column(nullable=False)
    num_of_master_nodes: Mapped[int] = mapped_column(nullable=False)
    num_of_worker_nodes: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    access_ip: Mapped[str] = mapped_column(nullable=True, default="")
    kubeconfig_path: Mapped[str] = mapped_column(nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default_factory=lambda: datetime.now())

    cluster_applications = relationship("ClusterApplication", back_populates="cluster", cascade="all,delete")
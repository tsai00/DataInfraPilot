from __future__ import annotations

from sqlalchemy.orm import mapped_column, Mapped, relationship
from datetime import datetime
from sqlalchemy import ARRAY, JSON
from src.database.models.base_model import BaseModel

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.models.cluster_application import ClusterApplication

from dataclasses import dataclass, asdict


@dataclass
class ClusterPool:
    name: str
    number_of_nodes: str
    node_type: str

    def to_dict(self):
        return asdict(self)


class Cluster(BaseModel):
    __tablename__ = 'cluster'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    name: Mapped[str] = mapped_column(nullable=False)
    k3s_version: Mapped[str] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(nullable=False)
    pools: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    access_ip: Mapped[str] = mapped_column(nullable=True, default="")
    error_message: Mapped[str] = mapped_column(nullable=True, default="")
    kubeconfig_path: Mapped[str] = mapped_column(nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default_factory=lambda: datetime.now())

    cluster_applications = relationship("ClusterApplication", back_populates="cluster", cascade="all,delete")
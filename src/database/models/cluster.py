from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models import BaseModel


class Cluster(BaseModel):
    __tablename__ = 'cluster'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    name: Mapped[str] = mapped_column(nullable=False)
    k3s_version: Mapped[str] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(nullable=False)
    provider_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    additional_components: Mapped[dict] = mapped_column(JSON, nullable=False)
    pools: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    access_ip: Mapped[str] = mapped_column(nullable=True, default='')
    error_message: Mapped[str] = mapped_column(nullable=True, default='')
    domain_name: Mapped[str] = mapped_column(nullable=True, default=None)
    kubeconfig_path: Mapped[str] = mapped_column(nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default_factory=lambda: datetime.now())

    deployments = relationship('Deployment', back_populates='cluster', cascade='all,delete')

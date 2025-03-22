from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy.sql import func
from src.core.kubernetes.kubernetes_cluster import KubernetesCluster
from datetime import datetime
from src.database.models.base_model import BaseModel



class Cluster(BaseModel):
    __tablename__ = 'cluster'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    name: Mapped[str] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(nullable=False)
    region: Mapped[str] = mapped_column(nullable=False)
    num_of_master_nodes: Mapped[int] = mapped_column(nullable=False)
    num_of_worker_nodes: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    kubeconfig_path: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default_factory=lambda: datetime.now())

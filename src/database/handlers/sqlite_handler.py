from src.database.handlers.base_database_handler import BaseDatabaseHandler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models.cluster import Cluster
from src.database.models.base_model import BaseModel


class SQLiteHandler(BaseDatabaseHandler):
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        BaseModel.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)

    def save_cluster(self, cluster: Cluster):
        session = self.session()
        session.add(cluster)
        session.commit()
        session.refresh(cluster)
        cluster_id = cluster.id
        session.close()

        return cluster_id

    def get_cluster(self, cluster_id) -> Cluster:
        session = self.session()
        cluster = session.query(Cluster).filter_by(id=cluster_id).first()
        session.close()

        return cluster if cluster else None

    def get_clusters(self) -> list[Cluster]:
        session = self.session()
        clusters = session.query(Cluster).all()
        session.close()

        return clusters

    def delete_cluster(self, cluster_id):
        session = self.session()
        session.query(Cluster).filter_by(id=cluster_id).delete()
        session.commit()
        session.close()

    def update_cluster(self, cluster_id, updated_data: dict):
        session = self.session()
        session.query(Cluster).filter_by(id=cluster_id).update(updated_data)
        session.commit()
        session.close()
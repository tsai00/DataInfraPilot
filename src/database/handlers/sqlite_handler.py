from datetime import datetime

from src.database.handlers.base_database_handler import BaseDatabaseHandler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from src.database.models import BaseModel, Cluster, ClusterApplication, Application


class SQLiteHandler(BaseDatabaseHandler):
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)

        BaseModel.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)

        if not self.session().query(Application).count():
            initial_apps = [
                Application(
                    name="Airflow",
                    description="Airflow is a platform to programmatically author, schedule and monitor workflows.",
                ),
                Application(name="Grafana", description=""),
            ]
            session = self.session()
            session.add_all(initial_apps)
            session.commit()
            session.close()

    def create_cluster(self, cluster: Cluster):
        with self.session() as session:
            session.add(cluster)
            session.commit()
            session.refresh(cluster)
            cluster_id = cluster.id

            return cluster_id

    def get_cluster(self, cluster_id) -> Cluster:
        with self.session() as session:
            cluster = session.query(Cluster).filter_by(id=cluster_id).first()

            return cluster or None

    def get_clusters(self) -> list[Cluster]:
        with self.session() as session:
            clusters = session.query(Cluster).all()

            return clusters

    def delete_cluster(self, cluster_id):
        with self.session() as session:
            cluster = session.query(Cluster).filter_by(id=cluster_id).first()
            if cluster:
                session.delete(cluster)  # This triggers ORM-level cascade
                session.commit()

    def update_cluster(self, cluster_id, updated_data: dict):
        with self.session() as session:
            session.query(Cluster).filter_by(id=cluster_id).update(updated_data)
            session.commit()

    def get_application(self, application_id) -> Application:
        with self.session() as session:
            application = session.query(Application).filter_by(id=application_id).first()

            return application or None

    def get_applications(self) -> list[Application]:
        with self.session() as session:
            applications = session.query(Application).all()

            return applications

    def create_cluster_application(self, cluster_application: ClusterApplication):
        with self.session() as session:
            session.add(cluster_application)
            session.commit()
            session.refresh(cluster_application)
            cluster_application_id = cluster_application.id

            return cluster_application_id

    def update_cluster_application(self, cluster_application_id: int, updated_data: dict):
        with self.session() as session:
            session.query(ClusterApplication).filter_by(id=cluster_application_id).update(updated_data)
            session.commit()

    def get_cluster_applications(self, cluster_id: int) -> list[ClusterApplication]:
        with self.session() as session:
            cluster_applications = (
                session.query(ClusterApplication)
                .options(
                    joinedload(ClusterApplication.cluster),
                    joinedload(ClusterApplication.application)
                )
                .filter_by(cluster_id=cluster_id)
                .all()
            )
            return cluster_applications

    def get_cluster_application(self, cluster_id: int, application_id: int) -> ClusterApplication:
        with self.session() as session:
            cluster_application = session.query(ClusterApplication).filter_by(cluster_id=cluster_id, application_id=application_id).first()

            return cluster_application or None

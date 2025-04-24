from datetime import datetime
from typing import Type

from src.database.handlers.base_database_handler import BaseDatabaseHandler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload, selectinload
from src.database.models import BaseModel, Cluster, Deployment, Application


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
                Application(
                    name="Grafana",
                    description=""
                )
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

    def get_cluster(self, cluster_id) -> Type[Cluster] | None:
        with self.session() as session:
            cluster = session.query(Cluster).filter_by(id=cluster_id).options(joinedload(Cluster.deployments)).first()

            return cluster or None

    def get_clusters(self) -> list[Type[Cluster]]:
        with self.session() as session:
            clusters = session.query(Cluster).options(joinedload(Cluster.deployments)).all()

            return clusters

    def delete_cluster(self, cluster_id):
        with self.session() as session:
            cluster = session.query(Cluster).filter_by(id=cluster_id).first()
            if cluster:
                session.delete(cluster)
                session.commit()

    def update_cluster(self, cluster_id, updated_data: dict):
        with self.session() as session:
            session.query(Cluster).filter_by(id=cluster_id).update(updated_data)
            session.commit()

    def get_application(self, application_id) -> Type[Application] | None:
        with self.session() as session:
            application = session.query(Application).filter_by(id=application_id).first()

            return application or None

    def get_applications(self) -> list[Type[Application]]:
        with self.session() as session:
            applications = session.query(Application).all()

            return applications

    def create_deployment(self, deployment: Deployment):
        with self.session() as session:
            session.add(deployment)
            session.commit()
            session.refresh(deployment)
            deployment_id = deployment.id

            return deployment_id

    def delete_deployment(self, deployment_id):
        with self.session() as session:
            deployment = session.query(Deployment).filter_by(id=deployment_id).first()
            if deployment:
                session.delete(deployment)
                session.commit()

    def update_deployment(self, deployment_id: int, updated_data: dict):
        with self.session() as session:
            session.query(Deployment).filter_by(id=deployment_id).update(updated_data)
            session.commit()

    def get_deployments(self, cluster_id: int) -> list[Type[Deployment]]:
        with self.session() as session:
            deployments = (
                session.query(Deployment)
                .options(
                    joinedload(Deployment.cluster),
                    joinedload(Deployment.application)
                )
                .filter_by(cluster_id=cluster_id)
                .all()
            )
            return deployments

    def get_deployment(self, deployment_id: int) -> Type[Deployment] | None:
        with self.session() as session:
            deployment = session.query(Deployment).filter_by(id=deployment_id).first()

            return deployment or None

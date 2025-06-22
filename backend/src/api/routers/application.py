from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas import ApplicationSchema
from src.core.apps.airflow_application import AccessEndpoint
from src.core.apps.application_factory import ApplicationFactory
from src.core.kubernetes.cluster_manager import ClusterManager
from src.core.utils import setup_logger

router = APIRouter()

cluster_manager = ClusterManager()

logger = setup_logger('APIApplicationRouter')


def get_cluster_manager() -> ClusterManager:
    return cluster_manager


@router.get('/applications')
def get_applications(
    cluster_manager: Annotated[ClusterManager, Depends(get_cluster_manager)],
) -> list[ApplicationSchema]:
    return cluster_manager.get_applications()


@router.get('/applications/{application_id}')
def get_application(
    application_id: int, cluster_manager: Annotated[ClusterManager, Depends(get_cluster_manager)]
) -> ApplicationSchema:
    application = cluster_manager.get_application(application_id)

    if not application:
        raise HTTPException(status_code=404, detail='Application not found')

    return application


@router.get('/applications/{application_id}/versions')
def get_application_available_versions(application_id: int) -> list[str]:
    return ApplicationFactory.get_application_class(application_id).get_available_versions()


@router.get('/applications/{application_id}/access_endpoints')
async def get_application_accessible_endpoints(
    application_id: int,
) -> list[AccessEndpoint]:
    return ApplicationFactory.get_application_class(application_id).get_accessible_endpoints()

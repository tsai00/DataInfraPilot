from fastapi import APIRouter, HTTPException, Depends
from src.core.kubernetes.cluster_manager import ClusterManager
from src.api.schemas.application import ApplicationSchema

router = APIRouter()

cluster_manager = ClusterManager()


def get_cluster_manager():
    return cluster_manager


@router.get("/applications", response_model=list[ApplicationSchema])
def get_applications(
    cluster_manager: ClusterManager = Depends(get_cluster_manager)
):
    applications = cluster_manager.get_applications()
    print(applications)
    return applications


@router.get("/applications/{application_id}", response_model=ApplicationSchema)
def get_application(
    application_id: int,
    cluster_manager: ClusterManager = Depends(get_cluster_manager)
):
    application = cluster_manager.get_application(application_id)

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    return application

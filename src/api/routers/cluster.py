from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status, Depends
from fastapi.background import BackgroundTasks
from src.core.kubernetes.cluster_manager import ClusterManager
from src.core.providers.provider_factory import ProviderFactory
from src.core.kubernetes.configuration import ClusterConfiguration
from src.api.schemas.cluster import ClusterCreateSchema, ClusterSchema, ClusterCreateResponseSchema
from src.api.schemas.application import ClusterApplicationCreateSchema, ApplicationSchema, ClusterApplicationSchema
from src.core.kubernetes.cluster_state import ClusterState
from src.core.apps.application_config import ApplicationConfig

router = APIRouter()

cluster_manager = ClusterManager()


def get_cluster_manager():
    return cluster_manager


@router.post("/clusters/", response_model=ClusterCreateResponseSchema, status_code=status.HTTP_202_ACCEPTED)
async def create_cluster(
    cluster: ClusterCreateSchema,
    background_tasks: BackgroundTasks,
    cluster_manager: ClusterManager = Depends(get_cluster_manager)
) -> ClusterCreateResponseSchema:
    print(f'Received request to create cluster: {cluster}')
    provider = ProviderFactory.get_provider(cluster.provider)
    cluster_config = ClusterConfiguration(cluster.name, cluster.pools)

    background_tasks.add_task(cluster_manager.create_cluster, provider, cluster_config)

    return {'name': cluster_config.name, 'status': ClusterState.PROVISIONING}


@router.get("/clusters/{cluster_id}", response_model=ClusterSchema)
def get_cluster(
    cluster_id: int,
    cluster_manager: ClusterManager = Depends(get_cluster_manager)
):
    cluster = cluster_manager.get_cluster(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster


@router.get("/clusters/{cluster_id}/kubeconfig", response_model=str)
def get_cluster_kubeconfig(
    cluster_id: int,
    cluster_manager: ClusterManager = Depends(get_cluster_manager)
):
    cluster_kubeconfig = cluster_manager.get_cluster_kubeconfig(cluster_id)

    if not cluster_kubeconfig:
        raise HTTPException(status_code=404, detail="Cluster kubeconfig not found")

    return cluster_kubeconfig


@router.get("/clusters/", response_model=list[ClusterSchema])
def get_clusters(
    cluster_manager: ClusterManager = Depends(get_cluster_manager)
):
    return cluster_manager.get_clusters()


@router.delete("/clusters/{cluster_id}", status_code=status.HTTP_200_OK)
def delete_cluster(
    cluster_id: int,
    cluster_manager: ClusterManager = Depends(get_cluster_manager)
):
    cluster_manager.delete_cluster(cluster_id)


@router.post("/clusters/{cluster_id}/applications", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def deploy_application(
    cluster_id: int,
    application: ClusterApplicationCreateSchema,
    background_tasks: BackgroundTasks,
    cluster_manager: ClusterManager = Depends(get_cluster_manager)
) -> dict:
    print(f'Received request to deploy app: {application}')

    application_config = ApplicationConfig(application.id, application.config)

    background_tasks.add_task(cluster_manager.deploy_application, cluster_id, application_config)

    return {'result': 'ok', 'status': ClusterState.PROVISIONING}


@router.get("/clusters/{cluster_id}/applications", response_model=list[ClusterApplicationSchema])
async def get_cluster_applications(
    cluster_id: int,
    cluster_manager: ClusterManager = Depends(get_cluster_manager)
) -> list[ClusterApplicationCreateSchema]:
    print('Request to get cluster applications')
    cluster_applications = cluster_manager.get_cluster_applications(cluster_id)

    return cluster_applications


@router.get("/clusters/{cluster_id}/applications/{application_id}", response_model=ClusterApplicationSchema)
async def get_cluster_application(
        cluster_id: int,
        application_id: int,
        cluster_manager: ClusterManager = Depends(get_cluster_manager)
) -> ClusterApplicationCreateSchema:
    cluster_application = cluster_manager.get_cluster_application(cluster_id, application_id)

    return cluster_application


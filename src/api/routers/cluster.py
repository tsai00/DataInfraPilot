from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status, Depends
from fastapi.background import BackgroundTasks
from src.core.kubernetes.cluster_manager import ClusterManager
from src.core.providers.provider_factory import ProviderFactory
from src.core.kubernetes.configuration import ClusterConfiguration
from src.api.schemas.cluster import ClusterCreateSchema, ClusterSchema, ClusterCreateResponseSchema
from src.api.schemas.deployment import DeploymentCreateSchema, DeploymentSchema, DeploymentUpdateSchema
from src.core.kubernetes.deployment_status import DeploymentStatus

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
    provider = ProviderFactory.get_provider(cluster.provider, cluster.provider_config)
    cluster_config = ClusterConfiguration(name=cluster.name, k3s_version=cluster.k3s_version, domain_name=cluster.domain_name, pools=cluster.pools)

    background_tasks.add_task(cluster_manager.create_cluster, provider, cluster_config)

    return {'name': cluster_config.name, 'status': DeploymentStatus.CREATING}


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


@router.post("/clusters/{cluster_id}/deployments", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def create_deployment(
    cluster_id: int,
    deployment: DeploymentCreateSchema,
    background_tasks: BackgroundTasks,
    cluster_manager: ClusterManager = Depends(get_cluster_manager)
) -> dict:
    print(f'Received request to deploy app: {deployment}')

    background_tasks.add_task(cluster_manager.create_deployment, cluster_id, deployment)

    return {'result': 'ok', 'status': DeploymentStatus.CREATING}


@router.post("/clusters/{cluster_id}/deployments/{deployment_id}", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def update_deployment(
    cluster_id: int | str,
    deployment_id: int | str,
    deployment: DeploymentUpdateSchema,
    background_tasks: BackgroundTasks,
    cluster_manager: ClusterManager = Depends(get_cluster_manager)
) -> dict:
    print(f'Received request to update deployment: {deployment}')

    background_tasks.add_task(cluster_manager.update_deployment, cluster_id, deployment_id, deployment.config)

    return {'result': 'ok', 'status': DeploymentStatus.UPDATING}


@router.delete("/clusters/{cluster_id}/deployments/{deployment_id}", status_code=status.HTTP_200_OK)
async def delete_cluster_deployment(
    cluster_id: int | str,
    deployment_id: int | str,
    cluster_manager: ClusterManager = Depends(get_cluster_manager)
):
    await cluster_manager.remove_deployment(deployment_id)


@router.get("/clusters/{cluster_id}/deployments", response_model=list[DeploymentSchema])
async def get_cluster_deployments(
    cluster_id: int,
    cluster_manager: ClusterManager = Depends(get_cluster_manager)
) -> list[DeploymentSchema]:
    print('Request to get cluster deployments')
    deployments = cluster_manager.get_deployments(cluster_id)

    return deployments


@router.get("/clusters/{cluster_id}/deployments/{deployment_id}", response_model=DeploymentSchema)
async def get_cluster_deployment(
        cluster_id: int,
        deployment_id: int,
        cluster_manager: ClusterManager = Depends(get_cluster_manager)
) -> DeploymentSchema:
    cluster_deployment = cluster_manager.get_deployment(deployment_id)

    return cluster_deployment


@router.get("/clusters/{cluster_id}/deployments/{deployment_id}/credentials", response_model=dict)
async def get_cluster_deployment_credentials(
        cluster_id: int,
        deployment_id: int,
        cluster_manager: ClusterManager = Depends(get_cluster_manager)
) -> dict:
    credentials = cluster_manager.get_deployment_initial_credentials(deployment_id)

    return credentials



from fastapi import APIRouter, HTTPException, Depends, status

from src.core.kubernetes.cluster_manager import ClusterManager
from src.api.schemas.volume import VolumeSchema, VolumeCreateSchema, VolumeCreateResponseSchema
from fastapi.background import BackgroundTasks

from src.core.kubernetes.deployment_status import DeploymentStatus

router = APIRouter()

cluster_manager = ClusterManager()


def get_cluster_manager():
    return cluster_manager


@router.get("/volumes", response_model=list[VolumeSchema])
def get_volumes(
    cluster_manager: ClusterManager = Depends(get_cluster_manager)
):
    volumes = cluster_manager.get_volumes()
    return volumes


@router.get("/volumes/{volume_id}", response_model=VolumeSchema)
def get_volume(
    volume_id: int,
    cluster_manager: ClusterManager = Depends(get_cluster_manager)
):
    volume = cluster_manager.get_volume(volume_id)

    if not volume:
        raise HTTPException(status_code=404, detail="Volume not found")

    return volume


@router.post("/volumes", response_model=VolumeCreateResponseSchema, status_code=status.HTTP_202_ACCEPTED)
async def create_volume(
    volume: VolumeCreateSchema,
    background_tasks: BackgroundTasks,
    cluster_manager: ClusterManager = Depends(get_cluster_manager)
) -> VolumeCreateResponseSchema:
    print(f'Received request to create volume: {volume}')

    background_tasks.add_task(cluster_manager.create_volume, volume.provider, volume)

    return VolumeCreateResponseSchema(name=volume.name, status=DeploymentStatus.CREATING)


@router.delete("/volumes/{volume_id}", status_code=status.HTTP_200_OK)
def delete_volume(
    volume_id: int,
    cluster_manager: ClusterManager = Depends(get_cluster_manager)
):
    cluster_manager.delete_volume(volume_id)
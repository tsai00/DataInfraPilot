from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.background import BackgroundTasks

from src.api.schemas import VolumeCreateResponseSchema, VolumeCreateSchema, VolumeSchema
from src.core.deployment_status import DeploymentStatus
from src.core.kubernetes.cluster_manager import ClusterManager
from src.core.utils import setup_logger

logger = setup_logger('APIVolumeRouter')

router = APIRouter()

cluster_manager = ClusterManager()


def get_cluster_manager() -> ClusterManager:
    return cluster_manager


@router.get('/volumes')
def get_volumes(cluster_manager: Annotated[ClusterManager, Depends(get_cluster_manager)]) -> list[VolumeSchema]:
    volumes = cluster_manager.get_volumes()
    return volumes


@router.get('/volumes/{volume_id}')
def get_volume(
    volume_id: int, cluster_manager: Annotated[ClusterManager, Depends(get_cluster_manager)]
) -> VolumeSchema:
    volume = cluster_manager.get_volume(volume_id)

    if not volume:
        raise HTTPException(status_code=404, detail='Volume not found')

    return volume


@router.post('/volumes', status_code=status.HTTP_202_ACCEPTED)
async def create_volume(
    volume: VolumeCreateSchema,
    background_tasks: BackgroundTasks,
    cluster_manager: Annotated[ClusterManager, Depends(get_cluster_manager)],
) -> VolumeCreateResponseSchema:
    logger.debug(f'Received request to create volume: {volume}')

    background_tasks.add_task(cluster_manager.create_volume, volume.provider, volume)

    return VolumeCreateResponseSchema(name=volume.name, status=DeploymentStatus.CREATING)


@router.delete('/volumes/{volume_id}', status_code=status.HTTP_200_OK)
def delete_volume(volume_id: int, cluster_manager: Annotated[ClusterManager, Depends(get_cluster_manager)]) -> None:
    cluster_manager.delete_volume(volume_id)

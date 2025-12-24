"""Camera health check endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.camera import CameraRepository
from app.db.session import get_session
from app.schemas.camera import CameraHealthResponse

router = APIRouter()
logger = get_logger(__name__)


@router.get("/{camera_id}/health", response_model=CameraHealthResponse)
async def check_camera_health(
    camera_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> CameraHealthResponse:
    """Check camera health and accessibility.

    Performs hardware-level checks to detect issues like:
    - Missing device files
    - I2C communication failures (CSI cameras)
    - Permission issues
    - Hardware disconnection

    Args:
        camera_id: Camera ID
        session: Database session

    Returns:
        Camera health status with diagnostic details
    """
    from app.services.camera.health import check_camera_health as check_health

    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    # Delegate to health service
    result = await check_health(camera.device_path, camera.camera_type)

    logger.info(
        "camera_health_checked",
        camera_id=camera_id,
        healthy=result.healthy,
        error=result.error,
    )

    return CameraHealthResponse(
        camera_id=camera_id,
        name=camera.name,
        device_path=camera.device_path,
        camera_type=camera.camera_type,
        healthy=result.healthy,
        device_exists=result.device_exists,
        device_accessible=result.device_accessible,
        error=result.error,
        details=result.details if result.details else None,
    )

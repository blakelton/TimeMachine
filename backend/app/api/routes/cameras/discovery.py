"""Camera discovery endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.camera import CameraRepository
from app.db.session import get_session
from app.schemas.camera import DiscoveredCameraResponse
from app.services.camera import CameraDiscovery

router = APIRouter()
logger = get_logger(__name__)


@router.post("/discover", response_model=list[DiscoveredCameraResponse])
async def discover_cameras(
    session: Annotated[AsyncSession, Depends(get_session)],
    camera_type: str | None = None,
) -> list[DiscoveredCameraResponse]:
    """Discover available cameras (CSI and USB), excluding already-configured ones.

    Args:
        camera_type: Optional filter by camera type ('csi' or 'usb')
        session: Database session to check for existing cameras

    Returns:
        List of discovered cameras with capabilities, excluding already-configured ones
    """
    # Discover cameras based on type
    logger.info(
        "camera_discovery_starting",
        camera_type=camera_type,
        message="Starting camera discovery",
    )

    try:
        if camera_type == "csi":
            discovered = await CameraDiscovery.discover_csi_cameras()
        elif camera_type == "usb":
            discovered = await CameraDiscovery.discover_usb_cameras()
        else:
            discovered = await CameraDiscovery.discover_all()

        logger.info(
            "camera_discovery_raw_results",
            camera_type=camera_type,
            discovered_count=len(discovered),
            cameras=[{"name": cam.name, "device": cam.device_path, "type": cam.camera_type} for cam in discovered],
        )
    except Exception as e:
        logger.error(
            "camera_discovery_failed",
            camera_type=camera_type,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise

    # Get existing cameras to filter out already-configured ones
    # Use hardware_id for matching (preferred) and device_path as fallback
    repo = CameraRepository(session)
    existing_cameras = await repo.get_all()
    existing_paths = {cam.device_path for cam in existing_cameras}
    existing_hardware_ids = {cam.hardware_id for cam in existing_cameras if cam.hardware_id}

    # Filter out already-configured cameras by hardware_id or device_path
    available_cameras = [
        cam for cam in discovered
        if (cam.hardware_id not in existing_hardware_ids if cam.hardware_id else True)
        and cam.device_path not in existing_paths
    ]

    logger.info(
        "camera_discovery_completed",
        camera_type=camera_type,
        found=len(discovered),
        available=len(available_cameras),
        filtered=len(discovered) - len(available_cameras),
        existing_paths=list(existing_paths),
        existing_hardware_ids=list(existing_hardware_ids),
    )

    return [
        DiscoveredCameraResponse(
            name=cam.name,
            device_path=cam.device_path,
            camera_type=cam.camera_type,
            hardware_id=cam.hardware_id,
            capabilities=cam.capabilities if cam.capabilities else None,
        )
        for cam in available_cameras
    ]

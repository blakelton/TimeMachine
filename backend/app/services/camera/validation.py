"""Camera validation service for checking if cameras are in use."""

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.camera import Camera
from app.db.repositories.camera import CameraRepository
from app.db.repositories.observation import ObservationRepository
from app.services.camera.pipeline import PipelineState
from app.services.camera.recording import recording_service
from app.services.camera.timelapse import timelapse_service

logger = get_logger(__name__)


@dataclass
class CameraInUseResult:
    """Result of camera in-use check."""

    in_use: bool
    reason: str | None = None
    observation_id: int | None = None
    observation_type: str | None = None


async def check_camera_in_use(
    camera_id: int, session: AsyncSession
) -> CameraInUseResult:
    """Check if a camera is currently in use.

    Checks three sources for active operations:
    1. Database observation status (primary source of truth)
    2. Recording service in-memory state
    3. Timelapse service in-memory state

    Args:
        camera_id: Camera ID to check
        session: Database session

    Returns:
        CameraInUseResult with in_use status and reason if applicable
    """
    obs_repo = ObservationRepository(session)

    # Check database first (source of truth)
    active_obs = await obs_repo.get_active_by_camera(camera_id)
    if active_obs:
        return CameraInUseResult(
            in_use=True,
            reason=f"{active_obs.observation_type} is running",
            observation_id=active_obs.id,
            observation_type=active_obs.observation_type,
        )

    # Check in-memory recording state (handles out-of-sync scenarios)
    if recording_service.get_recording_state(camera_id) == PipelineState.RUNNING:
        return CameraInUseResult(
            in_use=True,
            reason="recording is running",
        )

    # Check in-memory timelapse state
    if timelapse_service.is_running(camera_id):
        return CameraInUseResult(
            in_use=True,
            reason="timelapse is running",
        )

    return CameraInUseResult(in_use=False)


async def get_camera_or_404(
    camera_id: int,
    session: AsyncSession,
    operation: str = "access",
) -> Camera:
    """Get camera by ID, raise HTTPException if not found.

    Args:
        camera_id: Camera ID to retrieve
        session: Database session
        operation: Description of operation for logging (e.g., "update", "delete")

    Returns:
        Camera object if found

    Raises:
        HTTPException: 404 NOT_FOUND if camera doesn't exist
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning(f"camera_{operation}_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    return camera


async def require_camera_available(
    camera_id: int,
    session: AsyncSession,
    operation: str = "perform this operation",
) -> None:
    """Validate camera is available, raise HTTPException if not.

    Args:
        camera_id: Camera ID to check
        session: Database session
        operation: Description of operation for error message (e.g., "edit camera")

    Raises:
        HTTPException: 409 CONFLICT if camera is in use
    """
    result = await check_camera_in_use(camera_id, session)

    if result.in_use:
        log_data = {"camera_id": camera_id, "reason": result.reason}
        if result.observation_id:
            log_data["observation_id"] = result.observation_id

        logger.warning(f"camera_{operation.replace(' ', '_')}_blocked", **log_data)

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot {operation} while {result.reason}. Stop it first or wait for it to complete.",
        )

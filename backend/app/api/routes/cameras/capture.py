"""Camera still capture endpoints."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import ObservationStatus
from app.core.logging import get_logger
from app.db.models.camera import Camera
from app.db.repositories.camera import CameraRepository
from app.db.repositories.observation import ObservationRepository
from app.db.repositories.output_config import OutputConfigRepository
from app.db.session import get_session
from app.schemas.job import OperationResponse
from app.services.camera import capture_service, preview_service
from app.services.camera.device import wait_for_device_release
from app.services.camera.pipeline import PipelineState

router = APIRouter()
logger = get_logger(__name__)


@dataclass
class PreviewState:
    """Captured preview state before stopping for capture."""

    was_running: bool
    fps: int = 10


async def _stop_preview_for_capture(
    camera: Camera, session: AsyncSession
) -> PreviewState:
    """Stop preview if running and wait for device release.

    Args:
        camera: Camera model instance
        session: Database session for config lookup

    Returns:
        PreviewState with original state for later restoration
    """
    preview_state = preview_service.get_preview_state(camera.id)

    if preview_state != PipelineState.RUNNING:
        return PreviewState(was_running=False)

    # Get configured FPS for restart
    config_repo = OutputConfigRepository(session)
    config = await config_repo.get_current()
    fps = config.dashboard_preview_fps if config else 10

    logger.info(
        "capture_stopping_preview",
        camera_id=camera.id,
        camera_type=camera.camera_type,
        device_path=camera.device_path,
    )

    await preview_service.stop_preview(camera.id)
    # Wait for device to be fully released (uses fuser to verify for USB)
    await wait_for_device_release(
        camera.device_path, camera.id, camera.camera_type, "capture"
    )

    return PreviewState(was_running=True, fps=fps or 10)


async def _restart_preview(camera: Camera, fps: int) -> None:
    """Restart preview after capture with timeout protection.

    Note: This function intentionally suppresses all exceptions to ensure
    capture operations complete even if preview restart fails. Errors are
    logged for debugging. The dashboard watchdog will attempt to restart
    preview automatically if this fails.

    Args:
        camera: Camera model instance
        fps: FPS setting for preview
    """
    try:
        logger.info("capture_restarting_preview", camera_id=camera.id)
        await asyncio.wait_for(
            preview_service.start_preview(
                camera_id=camera.id,
                device_path=camera.device_path,
                camera_type=camera.camera_type,
                port=8080 + camera.id,
                fps=fps,
            ),
            timeout=10.0,
        )
        logger.info("capture_preview_restarted", camera_id=camera.id)
    except asyncio.TimeoutError:
        logger.error(
            "capture_preview_restart_timeout",
            camera_id=camera.id,
            message="Preview restart timed out after 10s",
        )
    except Exception as e:
        logger.error(
            "capture_preview_restart_failed",
            camera_id=camera.id,
            error=str(e),
        )


@router.post("/{camera_id}/capture", response_model=OperationResponse)
async def capture_image(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    filename: str | None = None,
) -> OperationResponse:
    """Capture a still image from a camera.

    Creates an observation record for the captured image so it appears
    in the observations list alongside timelapses and recordings.

    Args:
        camera_id: Camera ID
        session: Database session
        filename: Optional custom filename (without extension)

    Returns:
        Capture result with file path

    Raises:
        HTTPException: 404 if camera not found
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("capture_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    # Set capture lock and stop preview if running
    preview_service.set_capture_in_progress(camera_id, True)
    saved_preview = await _stop_preview_for_capture(camera, session)

    try:
        success, message, filepath = await _execute_capture(
            camera, session, filename
        )
    finally:
        # Release capture lock and restart preview if needed
        preview_service.set_capture_in_progress(camera_id, False)
        if saved_preview.was_running:
            await _restart_preview(camera, saved_preview.fps)

    if success:
        return OperationResponse(success=True, message=message, filepath=filepath)
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        )


async def _execute_capture(
    camera: Camera,
    session: AsyncSession,
    filename: str | None,
) -> tuple[bool, str, str | None]:
    """Execute the actual capture and create observation record.

    Args:
        camera: Camera model instance
        session: Database session
        filename: Optional custom filename

    Returns:
        Tuple of (success, message, filepath)
    """
    obs_repo = ObservationRepository(session)
    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")

    # Create observation folder
    folder_name = f"camera{camera.id}_{timestamp_str}_still"
    stills_base = Path(settings.media_path) / "stills"
    observation_folder = stills_base / folder_name
    observation_folder.mkdir(parents=True, exist_ok=True)

    # Generate filename and output path
    capture_filename = filename or f"capture_{timestamp_str}"
    output_file = observation_folder / f"{capture_filename}.jpg"

    logger.info(
        "capture_starting",
        camera_id=camera.id,
        camera_type=camera.camera_type,
        device_path=camera.device_path,
        output_file=str(output_file),
    )

    # Capture image
    success, message, filepath = await capture_service.capture_image(
        camera_id=camera.id,
        device_path=camera.device_path,
        camera_type=camera.camera_type,
        output_path=str(output_file),
    )

    logger.info(
        "capture_result",
        camera_id=camera.id,
        success=success,
        message=message,
        filepath=filepath,
    )

    # Create observation record if successful
    if success and filepath:
        file_size = Path(filepath).stat().st_size if Path(filepath).exists() else 0

        observation = await obs_repo.create(
            camera_id=camera.id,
            observation_type="still",
            status=ObservationStatus.COMPLETED,
            folder_path=str(observation_folder),
            config={"filename": capture_filename},
            progress_current=1,
            progress_total=1,
            size_bytes=file_size,
            started_at=now,
            completed_at=now,
        )

        logger.info(
            "capture_observation_created",
            camera_id=camera.id,
            observation_id=observation.id,
            filepath=filepath,
        )

    return success, message, filepath

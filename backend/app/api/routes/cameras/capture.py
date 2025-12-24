"""Camera still capture endpoints."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.repositories.camera import CameraRepository
from app.db.repositories.observation import ObservationRepository
from app.db.repositories.output_config import OutputConfigRepository
from app.db.session import get_session
from app.schemas.job import OperationResponse
from app.services.camera import capture_service, preview_service
from app.services.camera.pipeline import PipelineState

router = APIRouter()
logger = get_logger(__name__)


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
    obs_repo = ObservationRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("capture_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    # Set capture lock to prevent dashboard watchdog from auto-starting preview
    preview_service.set_capture_in_progress(camera_id, True)

    # Stop preview if running - both USB and CSI cameras need exclusive access
    # USB: V4L2 device exclusivity
    # CSI: libcamera pipeline can only be used by one process at a time
    preview_was_running = False
    preview_fps = 10  # default
    preview_state = preview_service.get_preview_state(camera_id)
    if preview_state == PipelineState.RUNNING:
        preview_was_running = True
        # Get configured FPS from settings for restart
        config_repo = OutputConfigRepository(session)
        config = await config_repo.get_current()
        if config:
            preview_fps = config.dashboard_preview_fps or 10

        logger.info(
            "capture_stopping_preview",
            camera_id=camera_id,
            camera_type=camera.camera_type,
            device_path=camera.device_path,
        )

        await preview_service.stop_preview(camera_id)

        # Wait for device to be released
        if camera.camera_type == "usb":
            # USB: Wait for V4L2 device to be fully released by GStreamer
            # USB devices need time for file descriptors to close and hardware to reset
            device_released = False
            for attempt in range(10):  # Try up to 5 seconds total
                await asyncio.sleep(0.5)
                # Check if any process still has the device open
                try:
                    check_proc = await asyncio.create_subprocess_shell(
                        f"fuser {camera.device_path} 2>/dev/null",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, _ = await asyncio.wait_for(check_proc.communicate(), timeout=2.0)
                    if not stdout.decode().strip():
                        device_released = True
                        logger.info(
                            "capture_device_released",
                            camera_id=camera_id,
                            device_path=camera.device_path,
                            attempts=attempt + 1,
                        )
                        break
                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    logger.warning(
                        "capture_device_check_failed",
                        camera_id=camera_id,
                        error=str(e),
                    )

            if not device_released:
                logger.warning(
                    "capture_device_still_busy",
                    camera_id=camera_id,
                    device_path=camera.device_path,
                    message="Proceeding anyway after 5s wait",
                )
        else:
            # CSI: libcamera needs time to release the camera pipeline
            # Wait for rpicam-vid process to fully exit
            await asyncio.sleep(1.0)
            logger.info(
                "capture_csi_preview_stopped",
                camera_id=camera_id,
            )

    try:
        # Create observation folder for this capture
        now = datetime.now()  # Use local time
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        folder_name = f"camera{camera_id}_{timestamp_str}_still"
        stills_base = Path(settings.media_path) / "stills"
        observation_folder = stills_base / folder_name
        observation_folder.mkdir(parents=True, exist_ok=True)

        # Generate filename for the capture
        capture_filename = filename or f"capture_{timestamp_str}"
        output_file = observation_folder / f"{capture_filename}.jpg"

        logger.info(
            "capture_starting",
            camera_id=camera_id,
            camera_type=camera.camera_type,
            device_path=camera.device_path,
            output_file=str(output_file),
        )

        # Capture image directly to observation folder
        success, message, filepath = await capture_service.capture_image(
            camera_id=camera_id,
            device_path=camera.device_path,
            camera_type=camera.camera_type,
            output_path=str(output_file),
        )

        logger.info(
            "capture_result",
            camera_id=camera_id,
            success=success,
            message=message,
            filepath=filepath,
        )

        # If capture succeeded, create observation record
        if success and filepath:
            file_size = Path(filepath).stat().st_size if Path(filepath).exists() else 0

            observation = await obs_repo.create(
                camera_id=camera_id,
                observation_type="still",
                status="completed",
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
                camera_id=camera_id,
                observation_id=observation.id,
                filepath=filepath,
            )
    finally:
        # Release capture lock BEFORE restarting preview
        # This allows the preview restart to proceed
        preview_service.set_capture_in_progress(camera_id, False)

        # Restart preview if it was running (with error handling and timeout)
        if preview_was_running:
            try:
                logger.info(
                    "capture_restarting_preview",
                    camera_id=camera_id,
                )
                # Use asyncio.wait_for to prevent hanging indefinitely
                await asyncio.wait_for(
                    preview_service.start_preview(
                        camera_id=camera_id,
                        device_path=camera.device_path,
                        camera_type=camera.camera_type,
                        port=8080 + camera_id,
                        fps=preview_fps,
                    ),
                    timeout=10.0,
                )
                logger.info(
                    "capture_preview_restarted",
                    camera_id=camera_id,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "capture_preview_restart_timeout",
                    camera_id=camera_id,
                    message="Preview restart timed out after 10s",
                )
            except Exception as e:
                logger.error(
                    "capture_preview_restart_failed",
                    camera_id=camera_id,
                    error=str(e),
                )

    if success:
        return OperationResponse(
            success=True,
            message=message,
            filepath=filepath,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        )

"""Camera management API endpoints."""

import asyncio
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.camera import CameraRepository
from app.db.session import get_session
from app.schemas.camera import (
    CameraCreate,
    CameraListResponse,
    CameraResponse,
    CameraUpdate,
    DiscoveredCameraResponse,
)
from app.schemas.job import (
    OperationResponse,
    RecordingStatusResponse,
    StartRecordingRequest,
    StartTimelapseRequest,
    StopTimelapseRequest,
    TimelapseStatusResponse,
)
from app.services.camera import (
    CameraDiscovery,
    TimelapseConfig,
    preview_service,
    capture_service,
    recording_service,
    timelapse_service,
)

router = APIRouter(prefix="/cameras", tags=["cameras"])
logger = get_logger(__name__)


@router.get("", response_model=CameraListResponse)
async def list_cameras(
    session: Annotated[AsyncSession, Depends(get_session)],
    enabled_only: bool = False,
    camera_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> CameraListResponse:
    """List all cameras with optional filtering.

    Args:
        session: Database session
        enabled_only: Only return enabled cameras
        camera_type: Filter by camera type ('csi' or 'usb')
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of cameras and total count
    """
    repo = CameraRepository(session)

    if enabled_only:
        cameras = await repo.get_enabled()
    elif camera_type:
        cameras = await repo.get_by_type(camera_type)
    else:
        cameras = await repo.get_all(skip=skip, limit=limit)

    total = await repo.count()

    logger.info(
        "cameras_listed",
        total=total,
        enabled_only=enabled_only,
        camera_type=camera_type,
    )

    return CameraListResponse(
        cameras=[CameraResponse.model_validate(cam) for cam in cameras], total=total
    )


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> CameraResponse:
    """Get a specific camera by ID.

    Args:
        camera_id: Camera ID
        session: Database session

    Returns:
        Camera details

    Raises:
        HTTPException: 404 if camera not found
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    logger.info("camera_retrieved", camera_id=camera_id, name=camera.name)
    return CameraResponse.model_validate(camera)


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    camera_data: CameraCreate, session: Annotated[AsyncSession, Depends(get_session)]
) -> CameraResponse:
    """Create a new camera.

    Args:
        camera_data: Camera creation data
        session: Database session

    Returns:
        Created camera

    Raises:
        HTTPException: 409 if device_path already exists
    """
    repo = CameraRepository(session)

    # Check if device_path already exists
    existing = await repo.get_by_device_path(camera_data.device_path)
    if existing:
        logger.warning(
            "camera_creation_conflict",
            device_path=camera_data.device_path,
            existing_id=existing.id,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Camera with device path '{camera_data.device_path}' already exists",
        )

    # Convert Pydantic models to dict for database
    create_data = camera_data.model_dump()
    if camera_data.capabilities:
        create_data["capabilities"] = camera_data.capabilities.model_dump()
    if camera_data.default_settings:
        create_data["default_settings"] = camera_data.default_settings.model_dump()

    camera = await repo.create(**create_data)

    logger.info(
        "camera_created",
        camera_id=camera.id,
        name=camera.name,
        device_path=camera.device_path,
    )

    return CameraResponse.model_validate(camera)


@router.patch("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: int,
    camera_data: CameraUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CameraResponse:
    """Update a camera.

    Args:
        camera_id: Camera ID
        camera_data: Camera update data
        session: Database session

    Returns:
        Updated camera

    Raises:
        HTTPException: 404 if camera not found
    """
    repo = CameraRepository(session)

    # Convert Pydantic model to dict, excluding unset fields
    update_data = camera_data.model_dump(exclude_unset=True)
    if camera_data.default_settings:
        update_data["default_settings"] = camera_data.default_settings.model_dump()

    camera = await repo.update(camera_id, **update_data)

    if camera is None:
        logger.warning("camera_update_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    logger.info("camera_updated", camera_id=camera.id, updated_fields=update_data)

    return CameraResponse.model_validate(camera)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> None:
    """Delete a camera.

    Args:
        camera_id: Camera ID
        session: Database session

    Raises:
        HTTPException: 404 if camera not found
    """
    repo = CameraRepository(session)
    deleted = await repo.delete(camera_id)

    if not deleted:
        logger.warning("camera_delete_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    logger.info("camera_deleted", camera_id=camera_id)


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

    # Get existing camera device paths to filter them out
    repo = CameraRepository(session)
    existing_cameras = await repo.get_all()
    existing_paths = {cam.device_path for cam in existing_cameras}

    # Filter out already-configured cameras
    available_cameras = [
        cam for cam in discovered if cam.device_path not in existing_paths
    ]

    logger.info(
        "camera_discovery_completed",
        camera_type=camera_type,
        found=len(discovered),
        available=len(available_cameras),
        filtered=len(discovered) - len(available_cameras),
        existing_paths=list(existing_paths),
    )

    return [
        DiscoveredCameraResponse(
            name=cam.name,
            device_path=cam.device_path,
            camera_type=cam.camera_type,
            capabilities=cam.capabilities if cam.capabilities else None,
        )
        for cam in available_cameras
    ]


# =============================================================================
# Preview Endpoints
# =============================================================================


@router.post("/{camera_id}/preview/start", response_model=OperationResponse)
async def start_camera_preview(
    camera_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> OperationResponse:
    """Start preview stream for a camera.

    Args:
        camera_id: Camera ID
        session: Database session

    Returns:
        Preview start status

    Raises:
        HTTPException: 404 if camera not found
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("preview_start_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    # Start preview
    success, message = await preview_service.start_preview(
        camera_id=camera_id,
        device_path=camera.device_path,
        camera_type=camera.camera_type,
        port=8080 + camera_id,
    )

    if success:
        return OperationResponse(
            success=True,
            message=message,
            pid=preview_service.get_preview_pid(camera_id),
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        )


@router.post("/{camera_id}/preview/stop", response_model=OperationResponse)
async def stop_camera_preview(
    camera_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> OperationResponse:
    """Stop preview stream for a camera.

    Args:
        camera_id: Camera ID
        session: Database session

    Returns:
        Preview stop status

    Raises:
        HTTPException: 404 if camera not found
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("preview_stop_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    # Stop preview
    success, message = await preview_service.stop_preview(camera_id)

    if success:
        return OperationResponse(success=True, message=message)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )


@router.get("/{camera_id}/preview/status")
async def get_preview_status(
    camera_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict:
    """Get preview status for a camera.

    Args:
        camera_id: Camera ID
        session: Database session

    Returns:
        Preview status

    Raises:
        HTTPException: 404 if camera not found
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("preview_status_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    state = preview_service.get_preview_state(camera_id)
    port = preview_service.get_preview_port(camera_id)

    return {
        "camera_id": camera_id,
        "state": state.value if state else "idle",
        "port": port,
        "url": f"http://localhost:{port}" if port else None,
    }


@router.get("/{camera_id}/preview/stream")
async def stream_preview(
    camera_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> StreamingResponse:
    """Stream MJPEG preview from camera.

    This endpoint proxies the GStreamer TCP socket stream to HTTP,
    converting the raw multipart stream to browser-compatible MJPEG.

    GStreamer's multipartmux outputs raw boundaries without MIME headers.
    Browsers expect proper multipart format with Content-Type headers.

    Args:
        camera_id: Camera ID
        session: Database session

    Returns:
        StreamingResponse with MJPEG content

    Raises:
        HTTPException: 404 if camera not found, 503 if preview not running
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("preview_stream_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    # Check if preview is running
    port = preview_service.get_preview_port(camera_id)
    if port is None:
        logger.warning("preview_stream_not_running", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Preview not running. Start preview first.",
        )

    async def stream_generator() -> AsyncGenerator[bytes, None]:
        """Connect to GStreamer TCP socket and yield browser-compatible MJPEG."""
        reader = None
        writer = None
        boundary = b"--frame"
        frame_count = 0

        try:
            # Connect to GStreamer TCP server
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", port),
                timeout=5.0,
            )
            logger.info(
                "preview_stream_connected",
                camera_id=camera_id,
                port=port,
            )

            # Buffer for accumulating data
            buffer = b""

            while True:
                chunk = await reader.read(65536)
                if not chunk:
                    break

                buffer += chunk

                # Process complete frames from buffer
                while True:
                    # Find JPEG start marker (FFD8)
                    jpeg_start = buffer.find(b'\xff\xd8')
                    if jpeg_start == -1:
                        # No JPEG start found, clear buffer except last byte
                        buffer = buffer[-1:] if buffer else b""
                        break

                    # Find JPEG end marker (FFD9) after start
                    jpeg_end = buffer.find(b'\xff\xd9', jpeg_start)
                    if jpeg_end == -1:
                        # JPEG not complete, keep buffer from jpeg_start
                        buffer = buffer[jpeg_start:]
                        break

                    # Extract complete JPEG frame
                    jpeg_data = buffer[jpeg_start:jpeg_end + 2]

                    # Output browser-compatible MJPEG frame
                    yield boundary + b"\r\n"
                    yield b"Content-Type: image/jpeg\r\n"
                    yield f"Content-Length: {len(jpeg_data)}\r\n".encode()
                    yield b"\r\n"
                    yield jpeg_data
                    yield b"\r\n"

                    frame_count += 1
                    if frame_count == 1:
                        logger.info("preview_stream_first_frame", camera_id=camera_id)

                    # Remove processed frame from buffer
                    buffer = buffer[jpeg_end + 2:]

        except asyncio.TimeoutError:
            logger.error(
                "preview_stream_connection_timeout",
                camera_id=camera_id,
                port=port,
            )
        except ConnectionRefusedError:
            logger.error(
                "preview_stream_connection_refused",
                camera_id=camera_id,
                port=port,
            )
        except Exception as e:
            logger.error(
                "preview_stream_error",
                camera_id=camera_id,
                error=str(e),
            )
        finally:
            if writer:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
            logger.info(
                "preview_stream_disconnected",
                camera_id=camera_id,
                frames_sent=frame_count,
            )

    return StreamingResponse(
        stream_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
        },
    )


# =============================================================================
# Capture Endpoints
# =============================================================================


@router.post("/{camera_id}/capture", response_model=OperationResponse)
async def capture_image(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    filename: str | None = None,
) -> OperationResponse:
    """Capture a still image from a camera.

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

    # Capture image
    success, message, filepath = await capture_service.capture_image(
        camera_id=camera_id,
        device_path=camera.device_path,
        camera_type=camera.camera_type,
        filename=filename,
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


# =============================================================================
# Recording Endpoints
# =============================================================================


@router.post("/{camera_id}/recording/start", response_model=OperationResponse)
async def start_recording(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    request: StartRecordingRequest | None = None,
) -> OperationResponse:
    """Start recording from a camera.

    Args:
        camera_id: Camera ID
        session: Database session
        request: Recording start parameters

    Returns:
        Recording start status with job ID

    Raises:
        HTTPException: 404 if camera not found
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("recording_start_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    # Start recording with Job tracking
    duration_seconds = request.duration_seconds if request else None
    filename = request.filename if request else None

    success, message, job_id = await recording_service.start_recording(
        camera_id=camera_id,
        device_path=camera.device_path,
        camera_type=camera.camera_type,
        session=session,
        duration_seconds=duration_seconds,
        filename=filename,
    )

    if success:
        return OperationResponse(
            success=True,
            message=message,
            job_id=job_id,
            pid=recording_service.get_recording_pid(camera_id),
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        )


@router.post("/{camera_id}/recording/stop", response_model=OperationResponse)
async def stop_recording(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    force: bool = False,
) -> OperationResponse:
    """Stop recording for a camera.

    Args:
        camera_id: Camera ID
        session: Database session
        force: Skip EOS and immediately terminate

    Returns:
        Recording stop status with file path

    Raises:
        HTTPException: 404 if camera not found
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("recording_stop_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    # Stop recording with Job tracking
    success, message, filepath = await recording_service.stop_recording(
        camera_id, session=session, force=force
    )

    if success:
        return OperationResponse(
            success=True,
            message=message,
            filepath=filepath,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )


@router.get("/{camera_id}/recording/status", response_model=RecordingStatusResponse)
async def get_recording_status(
    camera_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> RecordingStatusResponse:
    """Get recording status for a camera.

    Args:
        camera_id: Camera ID
        session: Database session

    Returns:
        Recording status with PID, uptime, and job ID

    Raises:
        HTTPException: 404 if camera not found
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("recording_status_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    state = recording_service.get_recording_state(camera_id)
    pid = recording_service.get_recording_pid(camera_id)
    uptime = recording_service.get_recording_uptime(camera_id)
    job_id = recording_service.get_recording_job_id(camera_id)

    return RecordingStatusResponse(
        camera_id=camera_id,
        state=state.value if state else "idle",
        pid=pid,
        uptime_seconds=uptime,
        job_id=job_id,
    )


# =============================================================================
# Timelapse Endpoints
# =============================================================================


@router.post("/{camera_id}/timelapse/start", response_model=OperationResponse)
async def start_timelapse(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    request: StartTimelapseRequest | None = None,
) -> OperationResponse:
    """Start timelapse capture for a camera.

    Args:
        camera_id: Camera ID
        session: Database session
        request: Timelapse configuration

    Returns:
        Timelapse start status with job ID

    Raises:
        HTTPException: 404 if camera not found
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("timelapse_start_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    # Build timelapse config
    if request and request.config:
        config = TimelapseConfig(
            camera_id=camera_id,
            interval_seconds=request.config.interval_seconds,
            total_frames=request.config.total_frames,
            duration_hours=request.config.duration_hours,
            quality=request.config.quality,
            resolution=(request.config.resolution_width, request.config.resolution_height),
            output_fps=request.config.output_fps,
        )
    else:
        config = TimelapseConfig(camera_id=camera_id)

    # Start timelapse with Job tracking
    success, message, job_id = await timelapse_service.start_timelapse(
        camera_id=camera_id,
        device_path=camera.device_path,
        camera_type=camera.camera_type,
        config=config,
        session=session,
    )

    if success:
        return OperationResponse(
            success=True,
            message=message,
            job_id=job_id,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        )


@router.post("/{camera_id}/timelapse/stop", response_model=OperationResponse)
async def stop_timelapse(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    request: StopTimelapseRequest | None = None,
) -> OperationResponse:
    """Stop timelapse capture for a camera.

    Args:
        camera_id: Camera ID
        session: Database session
        request: Stop options (whether to assemble video)

    Returns:
        Timelapse stop status with output path

    Raises:
        HTTPException: 404 if camera not found
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("timelapse_stop_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    # Stop timelapse with Job tracking
    assemble_video = request.assemble_video if request else True
    success, message, output_path = await timelapse_service.stop_timelapse(
        camera_id, session=session, assemble_video=assemble_video
    )

    if success:
        return OperationResponse(
            success=True,
            message=message,
            filepath=output_path,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )


@router.get("/{camera_id}/timelapse/status", response_model=TimelapseStatusResponse)
async def get_timelapse_status(
    camera_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> TimelapseStatusResponse:
    """Get timelapse status for a camera.

    Args:
        camera_id: Camera ID
        session: Database session

    Returns:
        Timelapse status with progress and job ID

    Raises:
        HTTPException: 404 if camera not found
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("timelapse_status_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    is_running = timelapse_service.is_running(camera_id)
    progress = timelapse_service.get_timelapse_progress(camera_id)
    job_id = timelapse_service.get_timelapse_job_id(camera_id)

    current_frame = progress[0] if progress else 0
    total_frames = progress[1] if progress else None

    return TimelapseStatusResponse(
        camera_id=camera_id,
        is_running=is_running,
        current_frame=current_frame,
        total_frames=total_frames,
        job_id=job_id,
    )


@router.get("/{camera_id}/timelapse/interrupted")
async def check_interrupted_timelapse(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Check for interrupted timelapse on this camera.

    Args:
        camera_id: Camera ID
        session: Database session

    Returns:
        Interrupted timelapse info or has_interrupted=False

    Raises:
        HTTPException: 404 if camera not found
    """
    from app.db.repositories.job import JobRepository

    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("timelapse_interrupted_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    job_repo = JobRepository(session)
    interrupted_job = await job_repo.get_interrupted_timelapse(camera_id)

    if not interrupted_job:
        return {"has_interrupted": False}

    # Get frame info from filesystem
    frame_info = await timelapse_service.get_interrupted_frame_info(
        interrupted_job.id, interrupted_job.timelapse_dir or ""
    )

    return {
        "has_interrupted": True,
        "job_id": interrupted_job.id,
        "frame_count": frame_info["frame_count"],
        "frames_directory": frame_info["directory"],
        "disk_usage_bytes": frame_info["disk_usage_bytes"],
        "disk_usage_human": frame_info["disk_usage_human"],
        "started_at": interrupted_job.started_at.isoformat() if interrupted_job.started_at else None,
        "interrupted_at": interrupted_job.completed_at.isoformat() if interrupted_job.completed_at else None,
        "original_config": interrupted_job.timelapse_config,
    }


@router.post("/{camera_id}/timelapse/resume", response_model=OperationResponse)
async def resume_timelapse(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OperationResponse:
    """Resume an interrupted timelapse.

    Args:
        camera_id: Camera ID
        session: Database session

    Returns:
        Resume status with job ID

    Raises:
        HTTPException: 404 if camera or interrupted timelapse not found,
                       409 if another timelapse is running
    """
    from app.db.repositories.job import JobRepository

    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("timelapse_resume_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    # Check for interrupted timelapse
    job_repo = JobRepository(session)
    interrupted_job = await job_repo.get_interrupted_timelapse(camera_id)

    if not interrupted_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No interrupted timelapse found",
        )

    # Resume using the service
    success, message = await timelapse_service.resume_timelapse(
        job_id=interrupted_job.id,
        device_path=camera.device_path,
        camera_type=camera.camera_type,
        session=session,
    )

    if not success:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in message.lower()
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(status_code=status_code, detail=message)

    return OperationResponse(
        success=True,
        message=message,
        job_id=interrupted_job.id,
    )


@router.post("/{camera_id}/timelapse/finalize", response_model=OperationResponse)
async def finalize_timelapse(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    output_fps: int = 30,
) -> OperationResponse:
    """Generate video from interrupted timelapse frames.

    Args:
        camera_id: Camera ID
        session: Database session
        output_fps: Output video FPS (default 30)

    Returns:
        Finalize status with job ID

    Raises:
        HTTPException: 404 if camera not found, 400 if no frames
    """
    repo = CameraRepository(session)
    camera = await repo.get(camera_id)

    if camera is None:
        logger.warning("timelapse_finalize_camera_not_found", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {camera_id} not found",
        )

    success, message, job_id = await timelapse_service.finalize_interrupted(
        camera_id=camera_id,
        session=session,
        output_fps=output_fps,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return OperationResponse(
        success=True,
        message=message,
        job_id=job_id,
    )


@router.delete("/{camera_id}/timelapse/cleanup", response_model=OperationResponse)
async def cleanup_timelapse(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Delete frames from interrupted timelapse.

    Args:
        camera_id: Camera ID
        session: Database session

    Returns:
        Cleanup stats with frames deleted and space freed

    Raises:
        HTTPException: 404 if no interrupted timelapse found
    """
    success, message, stats = await timelapse_service.cleanup_interrupted(
        camera_id=camera_id,
        session=session,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    return {
        "success": True,
        "message": message,
        **stats,
    }

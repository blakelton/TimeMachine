"""Camera management API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
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
from app.services.camera import (
    CameraDiscovery,
    preview_service,
    capture_service,
    recording_service,
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
async def discover_cameras() -> list[DiscoveredCameraResponse]:
    """Discover all available cameras (CSI and USB).

    Returns:
        List of discovered cameras with capabilities
    """
    discovered = await CameraDiscovery.discover_all()

    logger.info("camera_discovery_requested", found=len(discovered))

    return [
        DiscoveredCameraResponse(
            name=cam.name,
            device_path=cam.device_path,
            camera_type=cam.camera_type,
            capabilities=cam.capabilities.__dict__ if cam.capabilities else None,
        )
        for cam in discovered
    ]


@router.post("/{camera_id}/preview/start")
async def start_camera_preview(
    camera_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict:
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
        return {
            "success": True,
            "message": message,
            "port": 8080 + camera_id,
            "url": f"http://localhost:{8080 + camera_id}",
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        )


@router.post("/{camera_id}/preview/stop")
async def stop_camera_preview(
    camera_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict:
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
        return {"success": True, "message": message}
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


@router.post("/{camera_id}/capture")
async def capture_image(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    filename: str | None = None,
) -> dict:
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
        return {
            "success": True,
            "message": message,
            "filepath": filepath,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        )


@router.post("/{camera_id}/recording/start")
async def start_recording(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    duration_seconds: int | None = None,
    filename: str | None = None,
) -> dict:
    """Start recording from a camera.

    Args:
        camera_id: Camera ID
        session: Database session
        duration_seconds: Optional duration limit in seconds
        filename: Optional custom filename (without extension)

    Returns:
        Recording start status

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

    # Start recording
    success, message = await recording_service.start_recording(
        camera_id=camera_id,
        device_path=camera.device_path,
        camera_type=camera.camera_type,
        duration_seconds=duration_seconds,
        filename=filename,
    )

    if success:
        return {
            "success": True,
            "message": message,
            "pid": recording_service.get_recording_pid(camera_id),
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        )


@router.post("/{camera_id}/recording/stop")
async def stop_recording(
    camera_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict:
    """Stop recording for a camera.

    Args:
        camera_id: Camera ID
        session: Database session

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

    # Stop recording
    success, message, filepath = await recording_service.stop_recording(camera_id)

    if success:
        return {
            "success": True,
            "message": message,
            "filepath": filepath,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )


@router.get("/{camera_id}/recording/status")
async def get_recording_status(
    camera_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict:
    """Get recording status for a camera.

    Args:
        camera_id: Camera ID
        session: Database session

    Returns:
        Recording status with PID and uptime

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

    return {
        "camera_id": camera_id,
        "state": state.value if state else "idle",
        "pid": pid,
        "uptime_seconds": uptime,
    }

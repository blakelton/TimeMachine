"""Camera CRUD operations."""

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
)
from app.services.camera.validation import get_camera_or_404, require_camera_available

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=CameraListResponse)
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


@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
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

    # Check if hardware_id already exists (preferred unique identifier)
    if camera_data.hardware_id:
        existing_hw = await repo.get_by_hardware_id(camera_data.hardware_id)
        if existing_hw:
            logger.warning(
                "camera_creation_conflict_hardware_id",
                hardware_id=camera_data.hardware_id,
                existing_id=existing_hw.id,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Camera with hardware ID '{camera_data.hardware_id}' already exists",
            )

    # Check if device_path already exists (fallback check)
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
        HTTPException: 404 if camera not found, 409 if camera is in use
    """
    repo = CameraRepository(session)

    # Check if camera exists and is available
    await get_camera_or_404(camera_id, session, operation="update")
    await require_camera_available(camera_id, session, operation="edit camera")

    # Validate camera_type if provided
    if camera_data.camera_type is not None:
        if camera_data.camera_type not in ("csi", "usb"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="camera_type must be 'csi' or 'usb'",
            )

    # Validate device_path if provided - check for duplicates (excluding self)
    if camera_data.device_path is not None:
        existing = await repo.get_by_device_path(camera_data.device_path)
        if existing and existing.id != camera_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Device path '{camera_data.device_path}' is already assigned to camera '{existing.name}'",
            )

    # Convert Pydantic model to dict, excluding unset fields
    update_data = camera_data.model_dump(exclude_unset=True)
    if camera_data.default_settings:
        update_data["default_settings"] = camera_data.default_settings.model_dump()

    camera = await repo.update(camera_id, **update_data)

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
        HTTPException: 404 if camera not found, 409 if camera is in use
    """
    repo = CameraRepository(session)

    # Check if camera exists and is available
    await get_camera_or_404(camera_id, session, operation="delete")
    await require_camera_available(camera_id, session, operation="delete camera")

    deleted = await repo.delete(camera_id)

    if not deleted:
        logger.warning("camera_delete_failed", camera_id=camera_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete camera {camera_id}",
        )

    logger.info("camera_deleted", camera_id=camera_id)

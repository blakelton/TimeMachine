"""Camera recording endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.camera import CameraRepository
from app.db.session import get_session
from app.schemas.job import (
    OperationResponse,
    RecordingStatusResponse,
    StartRecordingRequest,
)
from app.services.camera import recording_service

router = APIRouter()
logger = get_logger(__name__)


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

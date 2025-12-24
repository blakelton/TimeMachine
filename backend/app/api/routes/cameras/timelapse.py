"""Camera timelapse endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.camera import CameraRepository
from app.db.session import get_session
from app.schemas.job import (
    OperationResponse,
    StartTimelapseRequest,
    StopTimelapseRequest,
    TimelapseStatusResponse,
)
from app.services.camera import TimelapseConfig, timelapse_service

router = APIRouter()
logger = get_logger(__name__)


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

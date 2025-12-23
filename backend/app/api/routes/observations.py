"""Observation management API endpoints."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.camera import CameraRepository
from app.db.repositories.observation import ObservationRepository
from app.db.session import get_session
from app.schemas.observation import (
    ActiveObservationResponse,
    CompletedObservationListResponse,
    CompletedObservationResponse,
    ObservationListResponse,
    ObservationResponse,
    ObservationStatusResponse,
    StartObservationRequest,
    StartObservationResponse,
    StopObservationRequest,
    StopObservationResponse,
    UpdateObservationNotesRequest,
)
from app.services.observation import observation_service
from app.services.thumbnail import thumbnail_service

router = APIRouter(prefix="/observations", tags=["observations"])
logger = get_logger(__name__)


def _format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


@router.post("/start", response_model=StartObservationResponse)
async def start_observation(
    request: StartObservationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StartObservationResponse:
    """Start a new observation.

    Args:
        request: Start observation request
        session: Database session

    Returns:
        Start observation response with created observation
    """
    success, message, observation = await observation_service.start_observation(
        request, session
    )

    logger.info(
        "observation_start_requested",
        camera_id=request.camera_id,
        observation_type=request.observation_type,
        success=success,
    )

    return StartObservationResponse(
        success=success,
        message=message,
        observation=ObservationResponse.model_validate(observation) if observation else None,
    )


@router.get("", response_model=ObservationListResponse)
async def list_observations(
    session: Annotated[AsyncSession, Depends(get_session)],
    camera_id: int | None = None,
    observation_type: str | None = None,
    status_filter: str | None = None,
    limit: int = 50,
) -> ObservationListResponse:
    """List observations with optional filtering.

    Args:
        session: Database session
        camera_id: Filter by camera ID
        observation_type: Filter by type ('timelapse', 'recording')
        status_filter: Filter by status
        limit: Maximum number of results

    Returns:
        List of observations
    """
    repo = ObservationRepository(session)

    if observation_type:
        observations = await repo.get_by_type(
            observation_type, camera_id, status_filter
        )
    elif camera_id:
        observations = await repo.get_by_camera(camera_id, limit)
    else:
        observations = await repo.get_recent(limit, camera_id)

    # Apply status filter if provided and not already filtered
    if status_filter and not observation_type:
        observations = [o for o in observations if o.status == status_filter]

    logger.info(
        "observations_listed",
        count=len(observations),
        camera_id=camera_id,
        observation_type=observation_type,
    )

    return ObservationListResponse(
        observations=[ObservationResponse.model_validate(o) for o in observations],
        total=len(observations),
    )


@router.get("/active", response_model=ObservationListResponse)
async def list_active_observations(
    session: Annotated[AsyncSession, Depends(get_session)],
    camera_id: int | None = None,
) -> ObservationListResponse:
    """List all active (running) observations.

    Args:
        session: Database session
        camera_id: Optional camera ID filter

    Returns:
        List of active observations
    """
    repo = ObservationRepository(session)
    observations = await repo.get_active(camera_id)

    logger.info("active_observations_listed", count=len(observations))

    return ObservationListResponse(
        observations=[ObservationResponse.model_validate(o) for o in observations],
        total=len(observations),
    )


@router.get("/completed", response_model=CompletedObservationListResponse)
async def list_completed_observations(
    session: Annotated[AsyncSession, Depends(get_session)],
    camera_id: int | None = Query(None, description="Filter by camera ID"),
    observation_type: str | None = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> CompletedObservationListResponse:
    """List completed observations for the browser.

    Returns observations that are completed, stopped, or failed (not running).
    Includes thumbnail and media URLs for display.

    Args:
        session: Database session
        camera_id: Optional filter by camera
        observation_type: Optional filter by type (timelapse, recording, still)
        limit: Maximum results to return
        offset: Pagination offset

    Returns:
        List of completed observations with media URLs
    """
    obs_repo = ObservationRepository(session)
    camera_repo = CameraRepository(session)

    # Get completed observations (not running)
    observations = await obs_repo.get_completed(
        camera_id=camera_id,
        observation_type=observation_type,
        limit=limit + 1,  # Fetch one extra to check if more exist
        offset=offset,
    )

    # Check if there are more results
    has_more = len(observations) > limit
    if has_more:
        observations = observations[:limit]

    # Get total count for pagination
    total = await obs_repo.count_completed(
        camera_id=camera_id,
        observation_type=observation_type,
    )

    # Build response with camera names and URLs
    result_observations = []
    for obs in observations:
        # Get camera name
        camera = await camera_repo.get(obs.camera_id)
        camera_name = camera.name if camera else f"Camera {obs.camera_id}"

        # Calculate duration
        if obs.completed_at and obs.started_at:
            duration = (obs.completed_at - obs.started_at).total_seconds()
        else:
            duration = 0.0

        # Get frame count for timelapses
        frame_count = None
        if obs.observation_type == "timelapse":
            frame_count = obs.progress_current

        result_observations.append(
            CompletedObservationResponse(
                id=obs.id,
                camera_id=obs.camera_id,
                camera_name=camera_name,
                observation_type=obs.observation_type,
                status=obs.status,
                started_at=obs.started_at,
                completed_at=obs.completed_at,
                duration_seconds=duration,
                frame_count=frame_count,
                size_bytes=obs.size_bytes,
                size_display=_format_size(obs.size_bytes),
                notes=obs.notes,
                thumbnail_url=f"/api/v1/observations/{obs.id}/thumbnail",
                media_url=f"/api/v1/observations/{obs.id}/media",
            )
        )

    logger.info(
        "completed_observations_listed",
        count=len(result_observations),
        total=total,
        camera_id=camera_id,
        observation_type=observation_type,
    )

    return CompletedObservationListResponse(
        observations=result_observations,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{observation_id}", response_model=ObservationResponse)
async def get_observation(
    observation_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ObservationResponse:
    """Get observation details.

    Args:
        observation_id: Observation ID
        session: Database session

    Returns:
        Observation details

    Raises:
        HTTPException: 404 if not found
    """
    repo = ObservationRepository(session)
    observation = await repo.get(observation_id)

    if not observation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation {observation_id} not found",
        )

    return ObservationResponse.model_validate(observation)


@router.get("/{observation_id}/status", response_model=ObservationStatusResponse)
async def get_observation_status(
    observation_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ObservationStatusResponse:
    """Get real-time status of an observation.

    Args:
        observation_id: Observation ID
        session: Database session

    Returns:
        Real-time observation status

    Raises:
        HTTPException: 404 if not found
    """
    status_data = await observation_service.get_observation_status(
        observation_id, session
    )

    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation {observation_id} not found",
        )

    return ObservationStatusResponse(**status_data)


@router.post("/{observation_id}/stop", response_model=StopObservationResponse)
async def stop_observation(
    observation_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    request: StopObservationRequest | None = None,
) -> StopObservationResponse:
    """Stop an active observation.

    Args:
        observation_id: Observation ID
        session: Database session
        request: Optional stop options

    Returns:
        Stop response with updated observation
    """
    assemble_video = request.assemble_video if request else True

    success, message, output_path = await observation_service.stop_observation(
        observation_id, session, assemble_video
    )

    # Get updated observation
    repo = ObservationRepository(session)
    observation = await repo.get(observation_id)

    logger.info(
        "observation_stop_requested",
        observation_id=observation_id,
        success=success,
        output_path=output_path,
    )

    return StopObservationResponse(
        success=success,
        message=message,
        observation=ObservationResponse.model_validate(observation) if observation else None,
        output_path=output_path,
    )


@router.get("/{observation_id}/preview")
async def get_observation_preview(
    observation_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FileResponse:
    """Get timelapse preview video.

    Args:
        observation_id: Observation ID
        session: Database session

    Returns:
        Preview video file

    Raises:
        HTTPException: 404 if not found or no preview available
    """
    from pathlib import Path

    repo = ObservationRepository(session)
    observation = await repo.get(observation_id)

    if not observation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation {observation_id} not found",
        )

    if observation.observation_type != "timelapse":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preview is only available for timelapse observations",
        )

    preview_path = Path(observation.folder_path) / "preview.mp4"
    if not preview_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preview not yet available",
        )

    return FileResponse(
        path=preview_path,
        media_type="video/mp4",
        filename="preview.mp4",
    )


@router.put("/{observation_id}/notes", response_model=ObservationResponse)
async def update_observation_notes(
    observation_id: int,
    request: UpdateObservationNotesRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ObservationResponse:
    """Update observation notes.

    Args:
        observation_id: Observation ID
        request: Notes update request
        session: Database session

    Returns:
        Updated observation

    Raises:
        HTTPException: 404 if not found
    """
    repo = ObservationRepository(session)
    observation = await repo.update_notes(observation_id, request.notes)

    if not observation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation {observation_id} not found",
        )

    await session.commit()

    logger.info("observation_notes_updated", observation_id=observation_id)

    return ObservationResponse.model_validate(observation)


@router.post("/{observation_id}/generate-preview")
async def generate_observation_preview(
    observation_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    max_frames: int = 60,
    fps: int = 10,
) -> dict:
    """Generate a preview video for a timelapse observation.

    Creates a low-resolution preview video from the captured frames.
    This is useful for monitoring timelapse progress without waiting
    for the full video assembly.

    Args:
        observation_id: Observation ID
        session: Database session
        max_frames: Maximum frames to include (default 60)
        fps: Output video FPS (default 10)

    Returns:
        Generation result with success status and preview path

    Raises:
        HTTPException: 404 if observation not found
    """
    success, message, preview_path = await observation_service.generate_timelapse_preview(
        observation_id, session, max_frames=max_frames, fps=fps
    )

    if not success and "not found" in message.lower():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    logger.info(
        "observation_preview_generated",
        observation_id=observation_id,
        success=success,
        preview_path=preview_path,
    )

    return {
        "success": success,
        "message": message,
        "preview_path": preview_path,
    }


# Camera-specific endpoint for getting active observation
@router.get("/camera/{camera_id}/active", response_model=ActiveObservationResponse)
async def get_camera_active_observation(
    camera_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ActiveObservationResponse:
    """Get active observation for a specific camera.

    Args:
        camera_id: Camera ID
        session: Database session

    Returns:
        Active observation response
    """
    observation = await observation_service.get_active_observation(camera_id, session)

    return ActiveObservationResponse(
        has_active=observation is not None,
        observation=ObservationResponse.model_validate(observation) if observation else None,
    )


@router.get("/{observation_id}/thumbnail")
async def get_observation_thumbnail(
    observation_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FileResponse:
    """Get thumbnail image for an observation.

    Generates thumbnail on-demand if not already cached.

    Args:
        observation_id: Observation ID
        session: Database session

    Returns:
        Thumbnail image file

    Raises:
        HTTPException: 404 if observation not found or thumbnail unavailable
    """
    obs_repo = ObservationRepository(session)
    observation = await obs_repo.get(observation_id)

    if not observation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation {observation_id} not found",
        )

    folder_path = Path(observation.folder_path)
    if not folder_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Observation folder not found",
        )

    # Get or generate thumbnail
    thumbnail_path = await thumbnail_service.get_or_generate_thumbnail(
        folder_path,
        observation.observation_type,
    )

    if not thumbnail_path or not thumbnail_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thumbnail not available",
        )

    return FileResponse(
        path=thumbnail_path,
        media_type="image/jpeg",
        filename=f"thumbnail_{observation_id}.jpg",
    )


@router.get("/{observation_id}/media")
async def get_observation_media(
    observation_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FileResponse:
    """Get the full media file for an observation.

    For timelapses: Returns the assembled video or preview.mp4
    For recordings: Returns the video file
    For stills: Returns the image file

    Args:
        observation_id: Observation ID
        session: Database session

    Returns:
        Media file

    Raises:
        HTTPException: 404 if observation or media not found
    """
    obs_repo = ObservationRepository(session)
    observation = await obs_repo.get(observation_id)

    if not observation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation {observation_id} not found",
        )

    folder_path = Path(observation.folder_path)
    if not folder_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Observation folder not found",
        )

    media_file = None
    media_type = "application/octet-stream"

    if observation.observation_type == "timelapse":
        # Look for assembled video or preview
        for name in ["output.mp4", "timelapse.mp4", "preview.mp4"]:
            candidate = folder_path / name
            if candidate.exists():
                media_file = candidate
                media_type = "video/mp4"
                break

    elif observation.observation_type == "recording":
        # Look for output video
        for ext in [".mp4", ".mkv", ".avi", ".webm"]:
            candidate = folder_path / f"output{ext}"
            if candidate.exists():
                media_file = candidate
                media_type = f"video/{ext[1:]}" if ext != ".mkv" else "video/x-matroska"
                break

        # Also check for files starting with "output"
        if not media_file:
            for f in folder_path.glob("output*"):
                if f.suffix in [".mp4", ".mkv", ".avi", ".webm"]:
                    media_file = f
                    ext = f.suffix
                    media_type = f"video/{ext[1:]}" if ext != ".mkv" else "video/x-matroska"
                    break

    elif observation.observation_type == "still":
        # Look for image file
        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            for f in folder_path.glob(f"*{ext}"):
                if f.name != "thumbnail.jpg":
                    media_file = f
                    media_type = f"image/{ext[1:]}" if ext != ".jpg" else "image/jpeg"
                    break
            if media_file:
                break

    if not media_file or not media_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found",
        )

    return FileResponse(
        path=media_file,
        media_type=media_type,
        filename=media_file.name,
    )


@router.delete("/{observation_id}")
async def delete_observation(
    observation_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Delete an observation and all its files.

    Only completed/stopped/failed observations can be deleted.
    Running observations must be stopped first.

    Args:
        observation_id: Observation ID
        session: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if not found, 400 if still running
    """
    import shutil

    obs_repo = ObservationRepository(session)
    observation = await obs_repo.get(observation_id)

    if not observation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation {observation_id} not found",
        )

    if observation.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete running observation. Stop it first.",
        )

    folder_path = Path(observation.folder_path)

    # Delete folder and contents
    deleted_files = False
    if folder_path.exists():
        try:
            shutil.rmtree(folder_path)
            deleted_files = True
            logger.info(
                "observation_folder_deleted",
                observation_id=observation_id,
                folder=str(folder_path),
            )
        except Exception as e:
            logger.error(
                "observation_folder_delete_failed",
                observation_id=observation_id,
                error=str(e),
            )

    # Delete database record
    await obs_repo.delete(observation_id)
    await session.commit()

    logger.info(
        "observation_deleted",
        observation_id=observation_id,
        deleted_files=deleted_files,
    )

    return {
        "success": True,
        "message": f"Observation {observation_id} deleted",
        "deleted_files": deleted_files,
    }


@router.post("/batch-delete")
async def batch_delete_observations(
    session: Annotated[AsyncSession, Depends(get_session)],
    observation_ids: list[int] = Query(..., description="List of observation IDs to delete"),
) -> dict:
    """Delete multiple observations and their files.

    Only completed/stopped/failed observations can be deleted.
    Running observations are skipped.

    Args:
        session: Database session
        observation_ids: List of observation IDs to delete

    Returns:
        Summary of deleted and skipped observations
    """
    import shutil

    obs_repo = ObservationRepository(session)

    deleted = []
    skipped = []
    errors = []

    for obs_id in observation_ids:
        observation = await obs_repo.get(obs_id)

        if not observation:
            skipped.append({"id": obs_id, "reason": "Not found"})
            continue

        if observation.status == "running":
            skipped.append({"id": obs_id, "reason": "Still running"})
            continue

        folder_path = Path(observation.folder_path)

        # Delete folder and contents
        deleted_files = False
        if folder_path.exists():
            try:
                shutil.rmtree(folder_path)
                deleted_files = True
            except Exception as e:
                errors.append({"id": obs_id, "error": str(e)})
                logger.error(
                    "batch_observation_folder_delete_failed",
                    observation_id=obs_id,
                    error=str(e),
                )

        # Delete database record
        try:
            await obs_repo.delete(obs_id)
            deleted.append({"id": obs_id, "deleted_files": deleted_files})
        except Exception as e:
            errors.append({"id": obs_id, "error": str(e)})

    await session.commit()

    logger.info(
        "batch_observations_deleted",
        deleted_count=len(deleted),
        skipped_count=len(skipped),
        error_count=len(errors),
    )

    return {
        "success": True,
        "deleted": deleted,
        "skipped": skipped,
        "errors": errors,
        "summary": {
            "deleted_count": len(deleted),
            "skipped_count": len(skipped),
            "error_count": len(errors),
        },
    }

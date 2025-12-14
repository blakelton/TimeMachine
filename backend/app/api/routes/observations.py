"""Observation management API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.observation import ObservationRepository
from app.db.session import get_session
from app.schemas.observation import (
    ActiveObservationResponse,
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

router = APIRouter(prefix="/observations", tags=["observations"])
logger = get_logger(__name__)


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

"""CRUD operations for observations (list, get, update)."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.camera import CameraRepository
from app.db.repositories.observation import ObservationRepository
from app.db.session import get_session
from app.schemas.observation import (
    CompletedObservationListResponse,
    CompletedObservationResponse,
    ObservationListResponse,
    ObservationResponse,
    UpdateObservationNotesRequest,
)

router = APIRouter()
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


@router.get("/", response_model=ObservationListResponse)
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

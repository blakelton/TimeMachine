"""Observation lifecycle operations (start, stop, status)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.observation import ObservationRepository
from app.db.session import get_session
from app.schemas.observation import (
    ActiveObservationResponse,
    ObservationResponse,
    ObservationStatusResponse,
    StartObservationRequest,
    StartObservationResponse,
    StopObservationRequest,
    StopObservationResponse,
)
from app.services.observation import observation_service

router = APIRouter()
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

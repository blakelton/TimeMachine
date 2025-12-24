"""Media endpoints for observations (preview, thumbnail, media files)."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.observation import ObservationRepository
from app.db.session import get_session
from app.services.observation import observation_service
from app.services.thumbnail import thumbnail_service

router = APIRouter()
logger = get_logger(__name__)


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
    from app.services.observation.media import find_observation_media

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

    media_file, media_type = await find_observation_media(
        folder_path, observation.observation_type
    )

    if not media_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found",
        )

    return FileResponse(
        path=media_file,
        media_type=media_type,
        filename=media_file.name,
    )

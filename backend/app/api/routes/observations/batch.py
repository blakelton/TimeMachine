"""Batch operations for observations (delete, bulk actions)."""

import shutil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.observation import ObservationRepository
from app.db.session import get_session

router = APIRouter()
logger = get_logger(__name__)


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

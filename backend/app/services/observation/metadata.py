"""Observation metadata and status management."""

import asyncio
import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ObservationStatus
from app.db.models.observation import Observation
from app.db.repositories.observation import ObservationRepository
from app.services.camera.recording import recording_service
from app.services.camera.timelapse import timelapse_service

from .utils import format_size, now


def write_observation_metadata(
    folder_path: Path,
    observation: Observation,
    camera_name: str,
) -> None:
    """Write observation.json metadata file."""
    metadata = {
        "id": observation.id,
        "camera_id": observation.camera_id,
        "camera_name": camera_name,
        "type": observation.observation_type,
        "started_at": observation.started_at.isoformat() if observation.started_at else None,
        "completed_at": observation.completed_at.isoformat() if observation.completed_at else None,
        "config": observation.config,
        "progress": {
            "current": observation.progress_current,
            "total": observation.progress_total,
        },
    }

    metadata_file = folder_path / "observation.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)


def update_observation_metadata(
    folder_path: Path,
    observation: Observation,
) -> None:
    """Update observation.json with current progress."""
    metadata_file = folder_path / "observation.json"
    if not metadata_file.exists():
        return

    with open(metadata_file, "r") as f:
        metadata = json.load(f)

    metadata["completed_at"] = (
        observation.completed_at.isoformat() if observation.completed_at else None
    )
    metadata["progress"] = {
        "current": observation.progress_current,
        "total": observation.progress_total,
    }
    metadata["status"] = observation.status
    metadata["size_bytes"] = observation.size_bytes

    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)


def calculate_folder_size_sync(folder_path: Path) -> int:
    """Calculate total size of folder contents (synchronous)."""
    total = 0
    try:
        for item in folder_path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
    except Exception:
        pass
    return total


async def calculate_folder_size(folder_path: Path) -> int:
    """Calculate total size of folder contents (async, runs in thread pool)."""
    return await asyncio.to_thread(calculate_folder_size_sync, folder_path)


async def get_observation_status(
    observation_id: int,
    session: AsyncSession,
) -> dict | None:
    """Get real-time status of an observation.

    Args:
        observation_id: Observation ID
        session: Database session

    Returns:
        Status dict or None if not found
    """
    obs_repo = ObservationRepository(session)
    observation = await obs_repo.get(observation_id)

    if not observation:
        return None

    folder_path = Path(observation.folder_path)

    # Get live progress from underlying service
    if observation.status == ObservationStatus.RUNNING:
        if observation.observation_type == "timelapse":
            progress = timelapse_service.get_timelapse_progress(observation.camera_id)
            if progress:
                observation.progress_current = progress[0]
        else:
            uptime = recording_service.get_recording_uptime(observation.camera_id)
            if uptime:
                observation.progress_current = int(uptime)

        # Update size (async to avoid blocking)
        observation.size_bytes = await calculate_folder_size(folder_path)

    # Check for preview availability (timelapse only)
    has_preview = False
    if observation.observation_type == "timelapse":
        preview_path = folder_path / "preview.mp4"
        has_preview = preview_path.exists()

    # Calculate elapsed time
    elapsed = (now() - observation.started_at).total_seconds()

    # Calculate progress percentage
    percentage = None
    if observation.progress_total and observation.progress_total > 0:
        percentage = (observation.progress_current / observation.progress_total) * 100

    return {
        "id": observation.id,
        "observation_type": observation.observation_type,
        "status": observation.status,
        "progress": {
            "current": observation.progress_current,
            "total": observation.progress_total,
            "percentage": percentage,
        },
        "size_bytes": observation.size_bytes,
        "size_formatted": format_size(observation.size_bytes),
        "elapsed_seconds": elapsed,
        "has_preview": has_preview,
    }

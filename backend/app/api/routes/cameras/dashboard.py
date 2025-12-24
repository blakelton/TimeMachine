"""Camera dashboard endpoint."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.camera import CameraRepository
from app.db.repositories.observation import ObservationRepository
from app.db.session import get_session
from app.schemas.camera import (
    CameraDashboardItem,
    CameraDashboardObservation,
    CameraDashboardResponse,
)
from app.services.camera import preview_service, recording_service, timelapse_service

router = APIRouter()
logger = get_logger(__name__)


@router.get("/dashboard", response_model=CameraDashboardResponse)
async def get_dashboard_data(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CameraDashboardResponse:
    """Get all camera data for dashboard display in a single request.

    Returns camera status, preview state, and active observation info
    for all cameras. Optimized for dashboard tile rendering.

    Args:
        session: Database session

    Returns:
        Dashboard data for all cameras
    """
    repo = CameraRepository(session)
    obs_repo = ObservationRepository(session)

    # Fetch all cameras and all active observations in just 2 queries (not N+1)
    cameras = await repo.get_all()
    all_active_obs = await obs_repo.get_active()
    obs_by_camera = {obs.camera_id: obs for obs in all_active_obs}

    dashboard_items: list[CameraDashboardItem] = []

    for camera in cameras:
        # Get preview state with error handling
        try:
            preview_state_enum = preview_service.get_preview_state(camera.id)
            preview_state = preview_state_enum.value if preview_state_enum else "idle"
            preview_port = preview_service.get_preview_port(camera.id)
        except Exception as e:
            logger.warning("preview_state_error", camera_id=camera.id, error=str(e))
            preview_state = "error"
            preview_port = None

        # Build preview URL - use the stream endpoint for proper MJPEG
        preview_url = None
        if preview_state == "running" and preview_port:
            preview_url = f"/api/v1/cameras/{camera.id}/preview/stream"

        # Check for active observation (from pre-fetched dict, no extra query)
        active_obs = obs_by_camera.get(camera.id)
        observation_data = None
        has_active_observation = active_obs is not None

        if active_obs:
            # Get live progress with error handling
            progress_current = active_obs.progress_current or 0
            progress_total = active_obs.progress_total

            try:
                if active_obs.observation_type == "timelapse":
                    progress = timelapse_service.get_timelapse_progress(camera.id)
                    if progress:
                        progress_current = progress[0]
                        progress_total = progress[1]
                else:
                    uptime = recording_service.get_recording_uptime(camera.id)
                    if uptime:
                        progress_current = int(uptime)
            except Exception as e:
                logger.warning("progress_fetch_error", camera_id=camera.id, error=str(e))

            # Check for preview.mp4 (async file check)
            has_preview = False
            preview_video_url = None
            if active_obs.folder_path:
                preview_path = Path(active_obs.folder_path) / "preview.mp4"
                try:
                    has_preview = await asyncio.to_thread(preview_path.exists)
                    if has_preview:
                        preview_video_url = f"/api/v1/observations/{active_obs.id}/preview"
                except Exception as e:
                    logger.warning("preview_check_error", obs_id=active_obs.id, error=str(e))

            observation_data = CameraDashboardObservation(
                id=active_obs.id,
                observation_type=active_obs.observation_type,
                progress_current=progress_current,
                progress_total=progress_total,
                has_preview=has_preview,
                preview_url=preview_video_url,
            )

        dashboard_items.append(
            CameraDashboardItem(
                camera_id=camera.id,
                name=camera.name,
                camera_type=camera.camera_type,
                enabled=camera.enabled,
                preview_state=preview_state,
                preview_url=preview_url,
                has_active_observation=has_active_observation,
                observation=observation_data,
            )
        )

    logger.info("dashboard_data_retrieved", camera_count=len(dashboard_items))

    return CameraDashboardResponse(
        cameras=dashboard_items,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

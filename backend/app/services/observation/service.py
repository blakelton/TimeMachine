"""Unified observation service for recordings and timelapses."""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models.observation import Observation
from app.db.repositories.camera import CameraRepository
from app.db.repositories.job import JobRepository
from app.db.repositories.observation import ObservationRepository
from app.db.repositories.output_config import OutputConfigRepository
from app.schemas.observation import (
    RecordingObservationConfig,
    StartObservationRequest,
    TimelapseObservationConfig,
)
from app.services.camera.preview import preview_service
from app.services.camera.pipeline import PipelineState
from app.services.camera.recording import recording_service
from app.services.camera.timelapse import TimelapseConfig, timelapse_service

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


def _interval_to_seconds(value: int, unit: str) -> int:
    """Convert interval value and unit to seconds."""
    if unit == "hours":
        return value * 3600
    elif unit == "minutes":
        return value * 60
    else:
        return value


def _calculate_end_datetime(
    end_mode: str,
    end_datetime: datetime | None,
    duration_value: int | None,
    duration_unit: str | None,
) -> datetime | None:
    """Calculate the end datetime from config."""
    if end_mode == "datetime" and end_datetime:
        return end_datetime
    elif end_mode == "duration" and duration_value and duration_unit:
        delta_seconds = _interval_to_seconds(duration_value, duration_unit)
        return datetime.utcnow() + timedelta(seconds=delta_seconds)
    return None


def _calculate_total_frames(
    interval_seconds: int,
    end_mode: str,
    end_datetime: datetime | None,
    duration_value: int | None,
    duration_unit: str | None,
) -> int | None:
    """Calculate total frames for timelapse."""
    target_end = _calculate_end_datetime(
        end_mode, end_datetime, duration_value, duration_unit
    )
    if target_end:
        duration_seconds = (target_end - datetime.utcnow()).total_seconds()
        if duration_seconds > 0:
            return int(duration_seconds / interval_seconds)
    return None


class ObservationService:
    """Service for managing unified observations (recordings and timelapses).

    Observations are stored in organized folders with metadata files,
    notes, and media output.

    For USB cameras running timelapse observations, this service automatically
    stops the preview stream to allow frame capture, and restarts it when
    the observation stops.
    """

    def __init__(self):
        self._active_observations: Dict[int, int] = {}  # camera_id -> observation_id
        self._progress_tasks: Dict[int, asyncio.Task] = {}  # observation_id -> task
        # Track cameras whose preview was stopped for observation
        self._preview_stopped_for: Dict[int, dict] = {}  # camera_id -> {port, device_path, camera_type}
        # Track live preview generation tasks for timelapse observations
        self._preview_gen_tasks: Dict[int, asyncio.Task] = {}  # observation_id -> task

    def _get_observations_base_path(self) -> Path:
        """Get the base path for observations."""
        return Path(settings.media_path) / "observations"

    def _create_observation_folder(self, camera_id: int) -> Path:
        """Create a new observation folder with proper structure."""
        base_path = self._get_observations_base_path()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        folder_name = f"camera{camera_id}_{timestamp}"
        folder_path = base_path / folder_name

        # Create folder structure
        folder_path.mkdir(parents=True, exist_ok=True)
        (folder_path / "notes").mkdir(exist_ok=True)
        (folder_path / "notes" / ".gitkeep").touch()

        return folder_path

    def _write_observation_metadata(
        self,
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

    def _update_observation_metadata(
        self,
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

    def _calculate_folder_size_sync(self, folder_path: Path) -> int:
        """Calculate total size of folder contents (synchronous)."""
        total = 0
        try:
            for item in folder_path.rglob("*"):
                if item.is_file():
                    total += item.stat().st_size
        except Exception:
            pass
        return total

    async def _calculate_folder_size(self, folder_path: Path) -> int:
        """Calculate total size of folder contents (async, runs in thread pool)."""
        return await asyncio.to_thread(self._calculate_folder_size_sync, folder_path)

    async def start_observation(
        self,
        request: StartObservationRequest,
        session: AsyncSession,
    ) -> tuple[bool, str, Observation | None]:
        """Start a new observation.

        Args:
            request: Start observation request
            session: Database session

        Returns:
            Tuple of (success, message, observation)
        """
        camera_id = request.camera_id

        # Check if camera already has an active observation (in memory)
        if camera_id in self._active_observations:
            return False, f"Camera {camera_id} already has an active observation", None

        # Also check database for active observations (handles restart scenarios)
        obs_repo = ObservationRepository(session)
        existing_active = await obs_repo.get_active_by_camera(camera_id)
        if existing_active:
            return False, f"Camera {camera_id} already has an active observation (ID: {existing_active.id})", None

        # Get camera info
        camera_repo = CameraRepository(session)
        camera = await camera_repo.get(camera_id)
        if not camera:
            return False, f"Camera {camera_id} not found", None

        if not camera.enabled:
            return False, f"Camera {camera_id} is disabled", None

        # Create observation folder
        folder_path = self._create_observation_folder(camera_id)

        try:
            if request.observation_type == "timelapse":
                return await self._start_timelapse_observation(
                    camera, folder_path, request.timelapse_config, session
                )
            else:
                return await self._start_recording_observation(
                    camera, folder_path, request.recording_config, session
                )
        except Exception as e:
            logger.error(
                "observation_start_error",
                camera_id=camera_id,
                error=str(e),
            )
            # Clean up folder on error
            try:
                import shutil
                shutil.rmtree(folder_path)
            except Exception:
                pass
            return False, f"Failed to start observation: {str(e)}", None

    async def _start_timelapse_observation(
        self,
        camera,
        folder_path: Path,
        config: TimelapseObservationConfig | None,
        session: AsyncSession,
    ) -> tuple[bool, str, Observation | None]:
        """Start a timelapse observation."""
        if not config:
            config = TimelapseObservationConfig()

        # Calculate interval in seconds
        interval_seconds = _interval_to_seconds(config.interval_value, config.interval_unit)

        # Calculate total frames and target end time
        total_frames = _calculate_total_frames(
            interval_seconds,
            config.end_mode,
            config.end_datetime,
            config.duration_value,
            config.duration_unit,
        )
        target_end_at = _calculate_end_datetime(
            config.end_mode,
            config.end_datetime,
            config.duration_value,
            config.duration_unit,
        )

        # Create frames directory within observation folder
        frames_dir = folder_path / "frames"
        frames_dir.mkdir(exist_ok=True)

        # Create timelapse config for existing service
        tl_config = TimelapseConfig(
            camera_id=camera.id,
            interval_seconds=interval_seconds,
            total_frames=total_frames,
            quality=config.quality,
            resolution=(config.resolution_width, config.resolution_height),
            output_fps=config.output_fps,
        )

        # For USB cameras, stop the preview stream to free the device for capture
        # The preview will be restarted when the observation stops
        if camera.camera_type == "usb":
            preview_state = preview_service.get_preview_state(camera.id)
            if preview_state == PipelineState.RUNNING:
                preview_port = preview_service.get_preview_port(camera.id)
                # Get FPS from output config for later restart
                config_repo = OutputConfigRepository(session)
                output_config = await config_repo.get_current()
                preview_fps = output_config.dashboard_preview_fps if output_config else 10

                logger.info(
                    "observation_stopping_preview",
                    camera_id=camera.id,
                    reason="timelapse_capture_requires_device",
                )
                await preview_service.stop_preview(camera.id)
                # Track so we can restart when observation stops
                self._preview_stopped_for[camera.id] = {
                    "port": preview_port,
                    "device_path": camera.device_path,
                    "camera_type": camera.camera_type,
                    "fps": preview_fps,
                }
                # Give the device time to be released
                await asyncio.sleep(0.5)

        # Create observation record first
        obs_repo = ObservationRepository(session)
        observation = await obs_repo.create(
            camera_id=camera.id,
            observation_type="timelapse",
            status="running",
            folder_path=str(folder_path),
            config=config.model_dump(),
            progress_current=0,
            progress_total=total_frames,
            size_bytes=0,
            target_end_at=target_end_at,
        )
        await session.commit()

        # Write initial metadata
        self._write_observation_metadata(folder_path, observation, camera.name)

        # Start the timelapse using existing service
        # Pass our frames directory to store frames in the observation folder
        success, message, job_id = await timelapse_service.start_timelapse(
            camera_id=camera.id,
            device_path=camera.device_path,
            camera_type=camera.camera_type,
            config=tl_config,
            session=session,
            frames_dir=frames_dir,
        )

        if not success:
            # Mark observation as failed
            await obs_repo.mark_failed(observation.id, message)
            await session.commit()
            # Restart preview if we stopped it
            await self._restart_preview_if_stopped(camera.id)
            return False, message, None

        # Link job to observation
        observation = await obs_repo.update(observation.id, job_id=job_id)
        await session.commit()

        # Track active observation
        self._active_observations[camera.id] = observation.id

        # Wait briefly and verify the timelapse is running
        await asyncio.sleep(0.5)
        progress = timelapse_service.get_timelapse_progress(camera.id)
        if progress is None:
            # Timelapse failed immediately
            logger.warning(
                "timelapse_immediate_failure",
                observation_id=observation.id,
                camera_id=camera.id,
            )
            await obs_repo.mark_failed(
                observation.id,
                "Timelapse failed to start - check camera connection",
            )
            await session.commit()
            del self._active_observations[camera.id]
            await self._restart_preview_if_stopped(camera.id)
            return False, "Timelapse failed to start - check camera connection", None

        # Start progress tracking task (watchdog for crash detection)
        self._start_progress_tracker(observation.id, camera.id, "timelapse")

        # Start live preview generator for real-time timelapse preview
        # Generate preview every 2 seconds (fast enough to feel responsive)
        self._start_live_preview_generator(observation.id, folder_path, interval_seconds=2.0)

        logger.info(
            "timelapse_observation_started",
            observation_id=observation.id,
            camera_id=camera.id,
            folder=str(folder_path),
            interval=interval_seconds,
            total_frames=total_frames,
            preview_stopped=camera.id in self._preview_stopped_for,
        )

        return True, "Timelapse observation started", observation

    async def _start_recording_observation(
        self,
        camera,
        folder_path: Path,
        config: RecordingObservationConfig | None,
        session: AsyncSession,
    ) -> tuple[bool, str, Observation | None]:
        """Start a recording observation."""
        if not config:
            config = RecordingObservationConfig()

        # Calculate duration and target end
        duration_seconds: int | None = None
        target_end_at: datetime | None = None

        if config.end_mode == "duration" and config.duration_value and config.duration_unit:
            duration_seconds = _interval_to_seconds(config.duration_value, config.duration_unit)
            target_end_at = datetime.utcnow() + timedelta(seconds=duration_seconds)
        elif config.end_mode == "datetime" and config.end_datetime:
            target_end_at = config.end_datetime
            duration_seconds = int((target_end_at - datetime.utcnow()).total_seconds())

        # For USB cameras, stop the preview stream to free the device for recording
        # The preview will be restarted when the observation stops
        if camera.camera_type == "usb":
            preview_state = preview_service.get_preview_state(camera.id)
            if preview_state == PipelineState.RUNNING:
                preview_port = preview_service.get_preview_port(camera.id)
                # Get FPS from output config for later restart
                config_repo = OutputConfigRepository(session)
                output_config = await config_repo.get_current()
                preview_fps = output_config.dashboard_preview_fps if output_config else 10

                logger.info(
                    "observation_stopping_preview",
                    camera_id=camera.id,
                    reason="recording_requires_device",
                )
                await preview_service.stop_preview(camera.id)
                # Track so we can restart when observation stops
                self._preview_stopped_for[camera.id] = {
                    "port": preview_port,
                    "device_path": camera.device_path,
                    "camera_type": camera.camera_type,
                    "fps": preview_fps,
                }
                # Give the device time to be released
                await asyncio.sleep(0.5)

        # Create observation record
        obs_repo = ObservationRepository(session)
        observation = await obs_repo.create(
            camera_id=camera.id,
            observation_type="recording",
            status="running",
            folder_path=str(folder_path),
            config=config.model_dump(),
            progress_current=0,
            progress_total=duration_seconds,
            size_bytes=0,
            target_end_at=target_end_at,
        )
        await session.commit()

        # Write initial metadata
        self._write_observation_metadata(folder_path, observation, camera.name)

        # Output file goes in observation folder
        output_file = folder_path / "output"

        # Start recording using existing service
        success, message, job_id = await recording_service.start_recording(
            camera_id=camera.id,
            device_path=camera.device_path,
            camera_type=camera.camera_type,
            session=session,
            duration_seconds=duration_seconds,
            filename=str(output_file),
        )

        if not success:
            await obs_repo.mark_failed(observation.id, message)
            await session.commit()
            # Restart preview if we stopped it
            await self._restart_preview_if_stopped(camera.id)
            return False, message, None

        # Link job to observation
        observation = await obs_repo.update(observation.id, job_id=job_id)
        await session.commit()

        # Track active observation
        self._active_observations[camera.id] = observation.id

        # Wait briefly and verify the pipeline is still running
        # GStreamer pipelines can crash immediately if codec/resolution is unsupported
        await asyncio.sleep(0.5)
        pipeline_state = recording_service.get_recording_state(camera.id)
        if pipeline_state != PipelineState.RUNNING:
            # Pipeline crashed immediately after starting
            logger.warning(
                "recording_pipeline_immediate_crash",
                observation_id=observation.id,
                camera_id=camera.id,
                pipeline_state=pipeline_state.value if pipeline_state else "none",
            )
            await obs_repo.mark_failed(
                observation.id,
                "Recording failed to start - camera may not support h264 encoding at this resolution",
            )
            await session.commit()
            del self._active_observations[camera.id]
            await self._restart_preview_if_stopped(camera.id)
            return False, "Recording failed - camera may not support h264 encoding at this resolution", None

        # Start progress tracking task (watchdog for crash detection)
        self._start_progress_tracker(observation.id, camera.id, "recording")

        logger.info(
            "recording_observation_started",
            observation_id=observation.id,
            camera_id=camera.id,
            folder=str(folder_path),
            duration=duration_seconds,
            preview_stopped=camera.id in self._preview_stopped_for,
        )

        return True, "Recording observation started", observation

    async def stop_observation(
        self,
        observation_id: int,
        session: AsyncSession,
        assemble_video: bool = True,
    ) -> tuple[bool, str, str | None]:
        """Stop an observation.

        Args:
            observation_id: Observation ID
            session: Database session
            assemble_video: Whether to assemble timelapse frames into video

        Returns:
            Tuple of (success, message, output_path)
        """
        obs_repo = ObservationRepository(session)
        observation = await obs_repo.get(observation_id)

        if not observation:
            return False, f"Observation {observation_id} not found", None

        if observation.status != "running":
            return False, f"Observation {observation_id} is not running", None

        camera_id = observation.camera_id
        folder_path = Path(observation.folder_path)

        # Stop progress tracker
        self._stop_progress_tracker(observation_id)

        # Stop live preview generator if running
        self._stop_live_preview_generator(observation_id)

        # Stop underlying service
        if observation.observation_type == "timelapse":
            success, message, output_path = await timelapse_service.stop_timelapse(
                camera_id, session, assemble_video
            )
        else:
            success, message, output_path = await recording_service.stop_recording(
                camera_id, session
            )

        # Calculate final size (async to avoid blocking)
        size_bytes = await self._calculate_folder_size(folder_path)

        # Update observation status
        if success:
            await obs_repo.mark_stopped(observation_id, size_bytes)
        else:
            await obs_repo.mark_failed(observation_id, message)
        await session.commit()

        # Refresh observation for metadata update
        observation = await obs_repo.get(observation_id)
        if observation:
            self._update_observation_metadata(folder_path, observation)

        # Remove from active tracking
        if camera_id in self._active_observations:
            del self._active_observations[camera_id]

        # Restart preview if we stopped it for this observation
        await self._restart_preview_if_stopped(camera_id)

        logger.info(
            "observation_stopped",
            observation_id=observation_id,
            camera_id=camera_id,
            success=success,
            output_path=output_path,
        )

        return success, message, output_path

    async def _restart_preview_if_stopped(self, camera_id: int) -> None:
        """Restart preview stream if it was stopped for observation.

        Args:
            camera_id: Camera ID to check and restart preview for
        """
        if camera_id not in self._preview_stopped_for:
            return

        preview_info = self._preview_stopped_for.pop(camera_id)
        try:
            # Small delay to ensure capture process has fully released the device
            await asyncio.sleep(0.3)

            # Get FPS from stored info (defaults to 10 if not set)
            fps = preview_info.get("fps", 10)

            logger.info(
                "observation_restarting_preview",
                camera_id=camera_id,
                port=preview_info["port"],
                fps=fps,
            )

            await preview_service.start_preview(
                camera_id=camera_id,
                device_path=preview_info["device_path"],
                camera_type=preview_info["camera_type"],
                port=preview_info["port"],
                fps=fps,
            )

            logger.info(
                "observation_preview_restarted",
                camera_id=camera_id,
                port=preview_info["port"],
                fps=fps,
            )
        except Exception as e:
            logger.error(
                "observation_preview_restart_failed",
                camera_id=camera_id,
                error=str(e),
            )

    async def get_observation_status(
        self,
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
        if observation.status == "running":
            if observation.observation_type == "timelapse":
                progress = timelapse_service.get_timelapse_progress(observation.camera_id)
                if progress:
                    observation.progress_current = progress[0]
            else:
                uptime = recording_service.get_recording_uptime(observation.camera_id)
                if uptime:
                    observation.progress_current = int(uptime)

            # Update size (async to avoid blocking)
            observation.size_bytes = await self._calculate_folder_size(folder_path)

        # Check for preview availability (timelapse only)
        has_preview = False
        if observation.observation_type == "timelapse":
            preview_path = folder_path / "preview.mp4"
            has_preview = preview_path.exists()

        # Calculate elapsed time
        elapsed = (datetime.utcnow() - observation.started_at).total_seconds()

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
            "size_formatted": _format_size(observation.size_bytes),
            "elapsed_seconds": elapsed,
            "has_preview": has_preview,
        }

    async def get_active_observation(
        self,
        camera_id: int,
        session: AsyncSession,
    ) -> Observation | None:
        """Get active observation for a camera.

        Args:
            camera_id: Camera ID
            session: Database session

        Returns:
            Active observation or None
        """
        obs_repo = ObservationRepository(session)
        return await obs_repo.get_active_by_camera(camera_id)

    def _start_progress_tracker(
        self,
        observation_id: int,
        camera_id: int,
        observation_type: str,
    ) -> None:
        """Start background task to track progress and detect crashes.

        This watchdog task:
        1. Periodically checks if the underlying pipeline is still running
        2. Marks observation as failed if pipeline has crashed
        3. Restarts preview if it was stopped for this observation

        Args:
            observation_id: Observation ID
            camera_id: Camera ID
            observation_type: "timelapse" or "recording"
        """
        if observation_id in self._progress_tasks:
            return  # Already tracking

        task = asyncio.create_task(
            self._progress_tracker_loop(observation_id, camera_id, observation_type)
        )
        self._progress_tasks[observation_id] = task
        logger.debug(
            "progress_tracker_started",
            observation_id=observation_id,
            camera_id=camera_id,
            observation_type=observation_type,
        )

    async def _progress_tracker_loop(
        self,
        observation_id: int,
        camera_id: int,
        observation_type: str,
    ) -> None:
        """Background loop that monitors observation health.

        Detects when the underlying pipeline has crashed and updates
        the observation status accordingly.
        """
        from app.db.session import SessionFactory

        check_interval = 3.0  # Check every 3 seconds
        # Allow a grace period for pipeline to start
        await asyncio.sleep(2.0)

        while True:
            try:
                # Check if pipeline is still running
                is_running = False

                if observation_type == "timelapse":
                    progress = timelapse_service.get_timelapse_progress(camera_id)
                    is_running = progress is not None
                else:  # recording
                    state = recording_service.get_recording_state(camera_id)
                    is_running = state == PipelineState.RUNNING

                if not is_running:
                    # Pipeline has stopped unexpectedly
                    logger.warning(
                        "observation_pipeline_crashed",
                        observation_id=observation_id,
                        camera_id=camera_id,
                        observation_type=observation_type,
                    )

                    # Mark observation as failed in a new session
                    async with SessionFactory() as session:
                        obs_repo = ObservationRepository(session)
                        await obs_repo.mark_failed(
                            observation_id,
                            "Pipeline stopped unexpectedly",
                        )
                        await session.commit()

                    # Clean up tracking
                    if camera_id in self._active_observations:
                        del self._active_observations[camera_id]

                    # Restart preview if we stopped it
                    await self._restart_preview_if_stopped(camera_id)

                    break

                await asyncio.sleep(check_interval)

            except asyncio.CancelledError:
                logger.debug(
                    "progress_tracker_cancelled",
                    observation_id=observation_id,
                )
                break
            except Exception as e:
                logger.error(
                    "progress_tracker_error",
                    observation_id=observation_id,
                    error=str(e),
                )
                await asyncio.sleep(check_interval)

    def _stop_progress_tracker(self, observation_id: int) -> None:
        """Stop progress tracking task."""
        if observation_id in self._progress_tasks:
            self._progress_tasks[observation_id].cancel()
            del self._progress_tasks[observation_id]

    def _start_live_preview_generator(
        self,
        observation_id: int,
        folder_path: Path,
        interval_seconds: float = 2.0,
    ) -> None:
        """Start background task to generate live preview video during timelapse.

        The preview video is regenerated periodically from the latest captured frames,
        allowing users to see the timelapse progress in real-time.

        Args:
            observation_id: Observation ID
            folder_path: Path to observation folder
            interval_seconds: How often to regenerate preview (default 2s)
        """
        if observation_id in self._preview_gen_tasks:
            # Already running
            return

        task = asyncio.create_task(
            self._live_preview_loop(observation_id, folder_path, interval_seconds)
        )
        self._preview_gen_tasks[observation_id] = task
        logger.info(
            "live_preview_generator_started",
            observation_id=observation_id,
            interval=interval_seconds,
        )

    def _stop_live_preview_generator(self, observation_id: int) -> None:
        """Stop the live preview generation task."""
        if observation_id in self._preview_gen_tasks:
            self._preview_gen_tasks[observation_id].cancel()
            del self._preview_gen_tasks[observation_id]
            logger.info("live_preview_generator_stopped", observation_id=observation_id)

    async def _live_preview_loop(
        self,
        observation_id: int,
        folder_path: Path,
        interval_seconds: float,
    ) -> None:
        """Background loop that regenerates preview video from timelapse frames.

        Args:
            observation_id: Observation ID
            folder_path: Path to observation folder
            interval_seconds: How often to regenerate
        """
        frames_dir = folder_path / "frames"
        preview_path = folder_path / "preview.mp4"
        last_frame_count = 0

        # Wait a bit for first frames to be captured
        await asyncio.sleep(3.0)

        while True:
            try:
                # Check how many frames we have
                frames = sorted(frames_dir.glob("frame_*.jpg"))
                frame_count = len(frames)

                # Only regenerate if we have new frames (and at least 2 frames)
                if frame_count >= 2 and frame_count > last_frame_count:
                    await self._generate_quick_preview(
                        frames_dir, preview_path, frames, max_frames=30, fps=10
                    )
                    last_frame_count = frame_count

                await asyncio.sleep(interval_seconds)

            except asyncio.CancelledError:
                logger.debug("live_preview_loop_cancelled", observation_id=observation_id)
                break
            except Exception as e:
                logger.warning(
                    "live_preview_loop_error",
                    observation_id=observation_id,
                    error=str(e),
                )
                await asyncio.sleep(interval_seconds)

    async def _generate_quick_preview(
        self,
        frames_dir: Path,
        preview_path: Path,
        frames: list,
        max_frames: int = 30,
        fps: int = 10,
    ) -> bool:
        """Generate a quick preview video from the latest frames.

        Uses the last N frames to create a short preview video.
        Optimized for speed over quality.

        Args:
            frames_dir: Directory containing frame images
            preview_path: Output path for preview video
            frames: Sorted list of frame files
            max_frames: Maximum frames to include
            fps: Output video FPS

        Returns:
            True if successful
        """
        # Use the last N frames for preview
        preview_frames = frames[-max_frames:] if len(frames) > max_frames else frames

        # Create temporary concat file
        concat_file = frames_dir / ".preview_frames.txt"
        temp_output = preview_path.with_suffix(".tmp.mp4")

        try:
            # Write frame list for ffmpeg concat demuxer
            with open(concat_file, "w") as f:
                for frame in preview_frames:
                    f.write(f"file '{frame.name}'\n")

            # Build fast ffmpeg command (ultrafast preset, low quality for speed)
            cmd = (
                f"ffmpeg -y -f concat -safe 0 -i '{concat_file}' "
                f"-framerate {fps} "
                f"-vf 'scale=640:360:force_original_aspect_ratio=decrease,"
                f"pad=640:360:(ow-iw)/2:(oh-ih)/2' "
                f"-c:v libx264 -preset ultrafast -crf 35 "
                f"-pix_fmt yuv420p "
                f"-movflags +faststart "
                f"'{temp_output}' 2>/dev/null"
            )

            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=str(frames_dir),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )

            await asyncio.wait_for(proc.communicate(), timeout=30.0)

            if proc.returncode == 0 and temp_output.exists():
                # Atomic rename to avoid partial reads
                temp_output.rename(preview_path)
                return True
            else:
                if temp_output.exists():
                    temp_output.unlink()
                return False

        except asyncio.TimeoutError:
            logger.warning("quick_preview_timeout")
            return False
        except Exception as e:
            logger.warning("quick_preview_error", error=str(e))
            return False
        finally:
            # Clean up temp files
            try:
                if concat_file.exists():
                    concat_file.unlink()
                if temp_output.exists():
                    temp_output.unlink()
            except Exception:
                pass

    async def generate_timelapse_preview(
        self,
        observation_id: int,
        session: AsyncSession,
        max_frames: int = 60,
        fps: int = 10,
        resolution: tuple[int, int] = (640, 360),
    ) -> tuple[bool, str, str | None]:
        """Generate a preview video from timelapse frames.

        Creates a low-resolution preview video using the latest captured frames.
        This is useful for monitoring timelapse progress without waiting for
        the full video assembly.

        Args:
            observation_id: Observation ID
            session: Database session
            max_frames: Maximum frames to include (default 60 = 6s at 10fps)
            fps: Output video FPS (default 10)
            resolution: Output resolution as (width, height) (default 640x360)

        Returns:
            Tuple of (success, message, preview_path)
        """
        obs_repo = ObservationRepository(session)
        observation = await obs_repo.get(observation_id)

        if not observation:
            return False, f"Observation {observation_id} not found", None

        if observation.observation_type != "timelapse":
            return False, "Preview generation only available for timelapses", None

        folder_path = Path(observation.folder_path)
        frames_dir = folder_path / "frames"

        if not frames_dir.exists():
            return False, "Frames directory not found", None

        # Get list of frame files sorted by name
        frames = sorted(frames_dir.glob("frame_*.jpg"))
        if len(frames) < 2:
            return False, "Not enough frames for preview (need at least 2)", None

        # Use the last N frames for preview
        preview_frames = frames[-max_frames:] if len(frames) > max_frames else frames
        preview_path = folder_path / "preview.mp4"

        # Build ffmpeg command for preview generation
        # Using a temporary file list for ffmpeg input
        concat_file = folder_path / "preview_frames.txt"
        try:
            # Write frame list for ffmpeg concat demuxer
            with open(concat_file, "w") as f:
                for frame in preview_frames:
                    # Use relative path and escape single quotes
                    f.write(f"file '{frame.name}'\n")

            width, height = resolution
            cmd = (
                f"ffmpeg -y -f concat -safe 0 -i '{concat_file}' "
                f"-framerate {fps} "
                f"-vf 'scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2' "
                f"-c:v libx264 -preset ultrafast -crf 28 "
                f"-pix_fmt yuv420p "
                f"-movflags +faststart "
                f"'{preview_path}'"
            )

            logger.info(
                "timelapse_preview_generating",
                observation_id=observation_id,
                frame_count=len(preview_frames),
                output=str(preview_path),
            )

            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=str(frames_dir),  # Run in frames directory for relative paths
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)

            if proc.returncode == 0 and preview_path.exists():
                file_size_kb = preview_path.stat().st_size / 1024
                logger.info(
                    "timelapse_preview_success",
                    observation_id=observation_id,
                    output=str(preview_path),
                    size_kb=file_size_kb,
                )
                return True, "Preview generated", str(preview_path)
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(
                    "timelapse_preview_failed",
                    observation_id=observation_id,
                    returncode=proc.returncode,
                    error=error_msg,
                )
                return False, f"Preview generation failed: {error_msg[:200]}", None

        except asyncio.TimeoutError:
            logger.error("timelapse_preview_timeout", observation_id=observation_id)
            return False, "Preview generation timed out", None
        except Exception as e:
            logger.error(
                "timelapse_preview_exception",
                observation_id=observation_id,
                error=str(e),
            )
            return False, f"Preview error: {str(e)}", None
        finally:
            # Clean up temporary file
            try:
                if concat_file.exists():
                    concat_file.unlink()
            except Exception:
                pass

    async def cleanup_stale_observations(self, session: AsyncSession) -> int:
        """Mark all running observations as failed (for startup cleanup).

        Args:
            session: Database session

        Returns:
            Number of observations cleaned up
        """
        obs_repo = ObservationRepository(session)
        count = await obs_repo.cleanup_stale_running()
        await session.commit()

        if count > 0:
            logger.info("stale_observations_cleaned", count=count)

        return count


# Global observation service instance
observation_service = ObservationService()

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
from app.schemas.observation import (
    RecordingObservationConfig,
    StartObservationRequest,
    TimelapseObservationConfig,
)
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
    """

    def __init__(self):
        self._active_observations: Dict[int, int] = {}  # camera_id -> observation_id
        self._progress_tasks: Dict[int, asyncio.Task] = {}  # observation_id -> task

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
            return False, message, None

        # Link job to observation
        observation = await obs_repo.update(observation.id, job_id=job_id)
        await session.commit()

        # Track active observation
        self._active_observations[camera.id] = observation.id

        # Start progress tracking task
        self._start_progress_tracker(observation.id, camera.id, session)

        logger.info(
            "timelapse_observation_started",
            observation_id=observation.id,
            camera_id=camera.id,
            folder=str(folder_path),
            interval=interval_seconds,
            total_frames=total_frames,
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
            return False, message, None

        # Link job to observation
        observation = await obs_repo.update(observation.id, job_id=job_id)
        await session.commit()

        # Track active observation
        self._active_observations[camera.id] = observation.id

        # Start progress tracking task
        self._start_progress_tracker(observation.id, camera.id, session)

        logger.info(
            "recording_observation_started",
            observation_id=observation.id,
            camera_id=camera.id,
            folder=str(folder_path),
            duration=duration_seconds,
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

        logger.info(
            "observation_stopped",
            observation_id=observation_id,
            camera_id=camera_id,
            success=success,
            output_path=output_path,
        )

        return success, message, output_path

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
        session: AsyncSession,
    ) -> None:
        """Start background task to track progress."""
        # Note: In production, this would need to be handled differently
        # as the session may not be valid for long-running async tasks
        pass

    def _stop_progress_tracker(self, observation_id: int) -> None:
        """Stop progress tracking task."""
        if observation_id in self._progress_tasks:
            self._progress_tasks[observation_id].cancel()
            del self._progress_tasks[observation_id]

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

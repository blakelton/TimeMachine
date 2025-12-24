"""Unified observation service for recordings and timelapses."""

import asyncio
from pathlib import Path
from typing import Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models.observation import Observation
from app.db.repositories.camera import CameraRepository
from app.db.repositories.observation import ObservationRepository
from app.schemas.observation import StartObservationRequest
from app.services.camera.recording import recording_service
from app.services.camera.timelapse import timelapse_service

# Import from sub-modules
from .completion import CompletionReason, CompletionResult
from .utils import now
from . import lifecycle
from . import metadata as metadata_module
from . import progress as progress_module
from . import preview as preview_module

logger = get_logger(__name__)

# Re-export for backward compatibility
__all__ = [
    "ObservationService",
    "observation_service",
    "CompletionReason",
    "CompletionResult",
]


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
        timestamp = now().strftime("%Y%m%d_%H%M%S")
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
        metadata_module.write_observation_metadata(folder_path, observation, camera_name)

    def _update_observation_metadata(
        self,
        folder_path: Path,
        observation: Observation,
    ) -> None:
        """Update observation.json with current progress."""
        metadata_module.update_observation_metadata(folder_path, observation)

    async def _calculate_folder_size(self, folder_path: Path) -> int:
        """Calculate total size of folder contents (async, runs in thread pool)."""
        return await metadata_module.calculate_folder_size(folder_path)

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
                success, message, observation = await lifecycle.start_timelapse_observation(
                    camera=camera,
                    folder_path=folder_path,
                    config=request.timelapse_config,
                    session=session,
                    active_observations=self._active_observations,
                    preview_stopped_for=self._preview_stopped_for,
                    start_progress_tracker_fn=self._start_progress_tracker,
                    start_live_preview_generator_fn=self._start_live_preview_generator,
                )
                if success:
                    # Write initial metadata
                    self._write_observation_metadata(folder_path, observation, camera.name)
                else:
                    # Restart preview if we stopped it
                    await self._restart_preview_if_stopped(camera_id)
                return success, message, observation
            else:
                success, message, observation = await lifecycle.start_recording_observation(
                    camera=camera,
                    folder_path=folder_path,
                    config=request.recording_config,
                    session=session,
                    active_observations=self._active_observations,
                    preview_stopped_for=self._preview_stopped_for,
                    start_progress_tracker_fn=self._start_progress_tracker,
                )
                if success:
                    # Write initial metadata
                    self._write_observation_metadata(folder_path, observation, camera.name)
                else:
                    # Restart preview if we stopped it
                    await self._restart_preview_if_stopped(camera_id)
                return success, message, observation
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
        return await lifecycle.stop_observation(
            observation_id=observation_id,
            session=session,
            assemble_video=assemble_video,
            active_observations=self._active_observations,
            stop_progress_tracker_fn=self._stop_progress_tracker,
            stop_live_preview_generator_fn=self._stop_live_preview_generator,
            calculate_folder_size_fn=self._calculate_folder_size,
            restart_preview_if_stopped_fn=self._restart_preview_if_stopped,
            update_observation_metadata_fn=self._update_observation_metadata,
        )

    async def _restart_preview_if_stopped(self, camera_id: int) -> None:
        """Restart preview stream if it was stopped for observation.

        Args:
            camera_id: Camera ID to check and restart preview for
        """
        if camera_id not in self._preview_stopped_for:
            return

        from app.services.camera.preview import preview_service

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
        return await metadata_module.get_observation_status(observation_id, session)

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
            progress_module.progress_tracker_loop(
                observation_id=observation_id,
                camera_id=camera_id,
                observation_type=observation_type,
                handle_successful_completion_fn=self._handle_successful_completion,
                handle_failed_completion_fn=self._handle_failed_completion,
                cleanup_after_completion_fn=self._cleanup_after_completion,
            )
        )
        self._progress_tasks[observation_id] = task
        logger.debug(
            "progress_tracker_started",
            observation_id=observation_id,
            camera_id=camera_id,
            observation_type=observation_type,
        )

    async def _handle_successful_completion(
        self,
        observation_id: int,
        camera_id: int,
        observation: Observation,
        result: CompletionResult,
        session: AsyncSession,
    ) -> None:
        """Handle successful observation completion."""
        await progress_module.handle_successful_completion(
            observation_id=observation_id,
            camera_id=camera_id,
            observation=observation,
            result=result,
            session=session,
            assemble_timelapse_fn=self._assemble_timelapse_video,
            get_observation_size_fn=self._get_observation_size,
        )

    async def _handle_failed_completion(
        self,
        observation_id: int,
        camera_id: int,
        observation: Observation,
        result: CompletionResult,
        session: AsyncSession,
    ) -> None:
        """Handle observation that stopped unexpectedly."""
        await progress_module.handle_failed_completion(
            observation_id=observation_id,
            camera_id=camera_id,
            observation=observation,
            result=result,
            session=session,
            assemble_timelapse_fn=self._assemble_timelapse_video,
        )

    async def _assemble_timelapse_video(
        self,
        observation_id: int,
        camera_id: int,
        session: AsyncSession,
        partial: bool = False,
    ) -> None:
        """Assemble timelapse frames into video."""
        success, msg, output_path = await timelapse_service.stop_timelapse(
            camera_id, session, assemble_video=True
        )
        log_event = "observation_timelapse_partial_assembly" if partial else "observation_timelapse_assembly_result"
        logger.info(
            log_event,
            observation_id=observation_id,
            success=success,
            output_path=output_path,
        )

    async def _get_observation_size(self, folder_path: str | None) -> int | None:
        """Calculate observation folder size."""
        if not folder_path:
            return None
        path = Path(folder_path)
        if path.exists():
            return await self._calculate_folder_size(path)
        return None

    async def _cleanup_after_completion(self, camera_id: int) -> None:
        """Clean up tracking state after observation completes."""
        if camera_id in self._active_observations:
            del self._active_observations[camera_id]
        await self._restart_preview_if_stopped(camera_id)

    def _stop_progress_tracker(self, observation_id: int) -> None:
        """Stop progress tracking task."""
        if observation_id in self._progress_tasks:
            self._progress_tasks[observation_id].cancel()
            del self._progress_tasks[observation_id]

    def _start_live_preview_generator(
        self,
        observation_id: int,
        folder_path: Path,
        output_fps: int = 15,
    ) -> None:
        """Start background task to generate live preview video during timelapse.

        The preview video is regenerated:
        1. Initially after the first frame
        2. Then every output_fps frames (i.e., every "1 second of footage")

        This means if output_fps=15, the preview updates after frames 1, 15, 30, 45, etc.

        Args:
            observation_id: Observation ID
            folder_path: Path to observation folder
            output_fps: Output video FPS (preview generated every fps frames)
        """
        if observation_id in self._preview_gen_tasks:
            # Already running
            return

        task = asyncio.create_task(
            preview_module.live_preview_loop(observation_id, folder_path, output_fps)
        )
        self._preview_gen_tasks[observation_id] = task
        logger.info(
            "live_preview_generator_started",
            observation_id=observation_id,
            output_fps=output_fps,
        )

    def _stop_live_preview_generator(self, observation_id: int) -> None:
        """Stop the live preview generation task."""
        if observation_id in self._preview_gen_tasks:
            self._preview_gen_tasks[observation_id].cancel()
            del self._preview_gen_tasks[observation_id]
            logger.info("live_preview_generator_stopped", observation_id=observation_id)

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
        return await preview_module.generate_timelapse_preview(
            observation_id=observation_id,
            session=session,
            max_frames=max_frames,
            fps=fps,
            resolution=resolution,
        )

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

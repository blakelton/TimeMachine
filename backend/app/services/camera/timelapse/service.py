"""Timelapse service for managing capture and assembly.

Features:
- Interval-based still image capture
- Job tracking with progress updates
- Resume support for interrupted timelapses
- Video assembly from frames using ffmpeg
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from app.services.environment.polling import EnvironmentPollingService

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import JobStatus
from app.core.logging import get_logger
from app.core.paths import media_paths
from app.core.resources import check_resources_available
from app.db.repositories.job import JobRepository

from .assembly import assemble_video, format_size
from .config import TimelapseConfig
from .session import TimelapseSession

logger = get_logger(__name__)


class TimelapseService:
    """Service for managing timelapse capture and assembly.

    Features:
    - Interval-based still image capture
    - Job tracking with progress updates
    - Resume support for interrupted timelapses
    - Video assembly from frames using ffmpeg
    """

    def __init__(self):
        self._sessions: Dict[int, TimelapseSession] = {}

    async def start_timelapse(
        self,
        camera_id: int,
        device_path: str,
        camera_type: str,
        config: TimelapseConfig,
        session: AsyncSession | None = None,
        frames_dir: Path | str | None = None,
        hardware_id: str | None = None,
        target_end_time: datetime | None = None,
        polling_service: "EnvironmentPollingService | None" = None,
    ) -> tuple[bool, str, int | None]:
        """Start a new timelapse capture session.

        Args:
            camera_id: Camera database ID
            device_path: Camera device path
            camera_type: Camera type ('csi' or 'usb')
            config: Timelapse configuration
            session: Database session for Job creation (optional)
            frames_dir: Optional custom directory for storing frames.
                        If not provided, creates a new directory in media_path/timelapses/
            hardware_id: Hardware ID for USB camera recovery (optional)
            target_end_time: When the timelapse should end (for timeout during recovery)
            polling_service: Environment polling service for overlay (optional)

        Returns:
            Tuple of (success: bool, message: str, job_id: int | None)
        """
        # Check if already capturing
        if camera_id in self._sessions and self._sessions[camera_id].is_running:
            return False, f"Timelapse already running for camera {camera_id}", None

        # Check initial resources
        resources_ok, reason = await check_resources_available(
            f"timelapse_camera_{camera_id}", min_memory_mb=50, min_disk_mb=500
        )
        if not resources_ok:
            return False, reason, None

        job_id: int | None = None
        try:
            # Use custom frames directory or create default timelapse directory
            if frames_dir:
                timelapse_dir = Path(frames_dir) if isinstance(frames_dir, str) else frames_dir
                timelapse_dir.mkdir(parents=True, exist_ok=True)
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                timelapse_dir = media_paths.timelapse_dir(camera_id, timestamp)
                timelapse_dir.mkdir(parents=True, exist_ok=True)

            # Create Job record if session provided
            if session:
                job_repo = JobRepository(session)
                job = await job_repo.create(
                    camera_id=camera_id,
                    job_type="timelapse",
                    status=JobStatus.RUNNING,
                    timelapse_config=config.to_dict(),
                    timelapse_progress=0,
                    timelapse_dir=str(timelapse_dir),
                )
                job_id = job.id
                await session.commit()

            # Import resolver for recovery (lazy import to avoid circular deps)
            from app.services.camera.resolver import resolve_hardware_id

            # Create callback for WebSocket progress updates
            async def on_frame_captured(
                current_frame: int,
                total_frames: Optional[int],
                job_id: Optional[int],
            ) -> None:
                """Broadcast frame capture progress via WebSocket."""
                if job_id is None:
                    return
                from app.services.websocket.manager import ws_manager
                await ws_manager.broadcast_job_update(
                    job_id=job_id,
                    camera_id=camera_id,
                    job_type="timelapse",
                    status="running",
                    current_frame=current_frame,
                    total_frames=total_frames,
                )

            # Create and start session with recovery support for USB cameras
            timelapse_session = TimelapseSession(
                config=config,
                device_path=device_path,
                camera_type=camera_type,
                job_id=job_id,
                timelapse_dir=timelapse_dir,
                hardware_id=hardware_id if camera_type == "usb" else None,
                device_resolver=resolve_hardware_id if camera_type == "usb" and hardware_id else None,
                target_end_time=target_end_time,
                polling_service=polling_service,
                on_frame_captured=on_frame_captured,
            )

            # Pre-load graph history from database if overlay with graph is configured
            if timelapse_session._overlay_service and config.env_overlay_show_graph:
                try:
                    from app.db.session import SessionFactory
                    await timelapse_session._overlay_service.load_history_from_database(
                        SessionFactory
                    )
                except Exception as e:
                    logger.warning(
                        "timelapse_overlay_history_load_failed",
                        camera_id=camera_id,
                        error=str(e),
                    )

            success = await timelapse_session.start()
            if success:
                self._sessions[camera_id] = timelapse_session
                logger.info(
                    "timelapse_started",
                    camera_id=camera_id,
                    job_id=job_id,
                    directory=str(timelapse_dir),
                    interval=config.interval_seconds,
                    total_frames=config.total_frames,
                )
                return True, f"Timelapse started: {timelapse_dir}", job_id
            else:
                # Mark job as failed
                if session and job_id:
                    job_repo = JobRepository(session)
                    await job_repo.mark_failed(job_id, "Failed to start capture loop")
                    await session.commit()
                return False, "Failed to start timelapse capture", None

        except Exception as e:
            # Mark job as failed
            if session and job_id:
                try:
                    job_repo = JobRepository(session)
                    await job_repo.mark_failed(job_id, str(e))
                    await session.commit()
                except Exception:
                    pass
            logger.error("timelapse_start_exception", camera_id=camera_id, error=str(e))
            return False, f"Timelapse error: {str(e)}", None

    async def stop_timelapse(
        self,
        camera_id: int,
        session: AsyncSession | None = None,
        assemble_video_flag: bool = True,
    ) -> tuple[bool, str, str | None]:
        """Stop a timelapse capture and optionally assemble video.

        Args:
            camera_id: Camera database ID
            session: Database session for Job update (optional)
            assemble_video_flag: Whether to assemble frames into video

        Returns:
            Tuple of (success: bool, message: str, output_path: str | None)
        """
        if camera_id not in self._sessions:
            return False, f"No timelapse active for camera {camera_id}", None

        timelapse_session = self._sessions[camera_id]
        job_id = timelapse_session.job_id
        timelapse_dir = timelapse_session.timelapse_dir
        config = timelapse_session.config

        # Stop capture
        frame_count = await timelapse_session.stop()
        del self._sessions[camera_id]

        output_path: str | None = None
        if assemble_video_flag and frame_count > 0:
            # Assemble video from frames
            output_path = await assemble_video(
                timelapse_dir=timelapse_dir,
                fps=config.output_fps,
                camera_id=camera_id,
            )

        # Update job status
        # User intentionally stopped the timelapse, so mark as completed (not interrupted)
        # Interrupted status is reserved for system crashes/unexpected termination
        if session and job_id:
            job_repo = JobRepository(session)
            if output_path:
                await job_repo.mark_completed(job_id, output_path)
            elif frame_count > 0:
                await job_repo.mark_completed(job_id, str(timelapse_dir))
            else:
                # User stopped with 0 frames - still mark as completed with no output
                await job_repo.mark_completed(job_id, None)
            await session.commit()

        if output_path:
            return True, f"Timelapse completed: {frame_count} frames, video: {output_path}", output_path
        elif frame_count > 0:
            return True, f"Timelapse stopped: {frame_count} frames in {timelapse_dir}", str(timelapse_dir)
        else:
            return True, "Timelapse stopped (no frames captured)", None

    async def resume_timelapse(
        self,
        job_id: int,
        device_path: str,
        camera_type: str,
        session: AsyncSession,
    ) -> tuple[bool, str]:
        """Resume an interrupted timelapse job.

        Args:
            job_id: Job ID to resume
            device_path: Camera device path
            camera_type: Camera type
            session: Database session

        Returns:
            Tuple of (success: bool, message: str)
        """
        job_repo = JobRepository(session)
        job = await job_repo.get(job_id)

        if not job:
            return False, f"Job {job_id} not found"

        if job.status != JobStatus.INTERRUPTED:
            return False, f"Job {job_id} is not in interrupted state"

        if job.job_type != "timelapse":
            return False, f"Job {job_id} is not a timelapse job"

        if not job.timelapse_dir:
            return False, "Job has no timelapse directory"

        # Check if already running (defensive - clean up stale sessions)
        camera_id = job.camera_id
        if camera_id in self._sessions:
            existing_session = self._sessions[camera_id]
            if existing_session.is_running:
                return False, f"Timelapse already running for camera {camera_id}"
            # Session exists but not running - clean it up
            del self._sessions[camera_id]

        # Restore config
        config = TimelapseConfig.from_dict(camera_id, job.timelapse_config or {})

        # Count existing frames by finding highest frame number
        # This handles gaps in sequence (if frames were deleted)
        timelapse_dir = Path(job.timelapse_dir)
        if not timelapse_dir.exists():
            return False, "Timelapse directory no longer exists"

        frame_files = sorted(timelapse_dir.glob("frame_*.jpg"))
        if frame_files:
            # Extract frame number from last file: frame_000042.jpg -> 43 (next frame)
            last_frame_name = frame_files[-1].stem  # "frame_000042"
            try:
                existing_frames = int(last_frame_name.split("_")[1]) + 1
            except (IndexError, ValueError):
                # Fallback to count if parsing fails
                existing_frames = len(frame_files)
        else:
            existing_frames = 0

        logger.debug(
            "timelapse_resume_frame_count",
            camera_id=camera_id,
            job_id=job_id,
            directory=str(timelapse_dir),
            existing_frames=existing_frames,
            frame_files_count=len(frame_files) if frame_files else 0,
        )

        # Adjust remaining frames
        if config.total_frames:
            remaining = config.total_frames - existing_frames
            if remaining <= 0:
                return False, "Timelapse already completed"
            config.total_frames = remaining

        # Create callback for WebSocket progress updates
        async def on_frame_captured(
            current_frame: int,
            total_frames: Optional[int],
            cb_job_id: Optional[int],
        ) -> None:
            """Broadcast frame capture progress via WebSocket."""
            if cb_job_id is None:
                return
            from app.services.websocket.manager import ws_manager
            await ws_manager.broadcast_job_update(
                job_id=cb_job_id,
                camera_id=camera_id,
                job_type="timelapse",
                status="running",
                current_frame=current_frame,
                total_frames=total_frames,
            )

        # Create new session starting from existing frame count
        timelapse_session = TimelapseSession(
            config=config,
            device_path=device_path,
            camera_type=camera_type,
            job_id=job_id,
            timelapse_dir=timelapse_dir,
            on_frame_captured=on_frame_captured,
        )
        timelapse_session.frame_count = existing_frames

        # Update job status
        await job_repo.update(job_id, status=JobStatus.RUNNING)
        await session.commit()

        # Start capture
        success = await timelapse_session.start()
        if success:
            self._sessions[camera_id] = timelapse_session
            logger.info(
                "timelapse_resumed",
                camera_id=camera_id,
                job_id=job_id,
                existing_frames=existing_frames,
            )
            return True, f"Timelapse resumed with {existing_frames} existing frames"
        else:
            await job_repo.mark_failed(job_id, "Failed to resume capture loop")
            await session.commit()
            return False, "Failed to resume timelapse"

    def get_timelapse_progress(self, camera_id: int) -> tuple[int, int | None] | None:
        """Get timelapse capture progress.

        Args:
            camera_id: Camera database ID

        Returns:
            Tuple of (current_frame, total_frames) or None if not running
        """
        if camera_id in self._sessions:
            return self._sessions[camera_id].get_progress()
        return None

    def get_timelapse_job_id(self, camera_id: int) -> int | None:
        """Get the Job ID for an active timelapse.

        Args:
            camera_id: Camera database ID

        Returns:
            Job ID or None
        """
        if camera_id in self._sessions:
            return self._sessions[camera_id].job_id
        return None

    def is_running(self, camera_id: int) -> bool:
        """Check if timelapse is running for a camera.

        Args:
            camera_id: Camera database ID

        Returns:
            True if running
        """
        return camera_id in self._sessions and self._sessions[camera_id].is_running

    def get_timelapse_events(self, camera_id: int) -> list[dict]:
        """Get events logged during timelapse capture.

        Args:
            camera_id: Camera database ID

        Returns:
            List of event dictionaries
        """
        if camera_id in self._sessions:
            return self._sessions[camera_id].get_events()
        return []

    def get_timelapse_health(self, camera_id: int) -> dict | None:
        """Get health status of a running timelapse.

        Args:
            camera_id: Camera database ID

        Returns:
            Health status dict or None if not running
        """
        if camera_id not in self._sessions:
            return None

        session = self._sessions[camera_id]
        return {
            "is_running": session.is_running,
            "frame_count": session.frame_count,
            "completed_by_duration": session._completed_by_duration,
            "frames_incomplete": session._frames_incomplete,
            "consecutive_failures": session._consecutive_failures,
            "total_failures": session._total_failures,
            "in_recovery_mode": session._in_recovery_mode,
            "recovery_attempts": session._recovery_attempts,
            "device_path": session.device_path,
            "hardware_id": session.hardware_id,
            "events_count": len(session._events),
        }

    async def get_interrupted_frame_info(self, job_id: int, timelapse_dir: str) -> dict:
        """Get information about frames from an interrupted timelapse.

        Args:
            job_id: Job ID
            timelapse_dir: Timelapse directory path

        Returns:
            Dict with frame_count, directory, disk_usage_bytes, disk_usage_human
        """
        frames_dir = Path(timelapse_dir)

        if not frames_dir.exists():
            return {
                "frame_count": 0,
                "directory": timelapse_dir,
                "disk_usage_bytes": 0,
                "disk_usage_human": "0 B",
            }

        frames = list(frames_dir.glob("frame_*.jpg"))
        total_size = sum(f.stat().st_size for f in frames)

        return {
            "frame_count": len(frames),
            "directory": timelapse_dir,
            "disk_usage_bytes": total_size,
            "disk_usage_human": format_size(total_size),
        }

    async def finalize_interrupted(
        self,
        camera_id: int,
        session: AsyncSession,
        output_fps: int = 30,
    ) -> tuple[bool, str, int | None]:
        """Generate video from interrupted timelapse frames.

        Args:
            camera_id: Camera database ID
            session: Database session
            output_fps: Output video FPS

        Returns:
            Tuple of (success: bool, message: str, job_id: int | None)
        """
        job_repo = JobRepository(session)
        interrupted_job = await job_repo.get_interrupted_timelapse(camera_id)

        if not interrupted_job:
            return False, "No interrupted timelapse found", None

        if not interrupted_job.timelapse_dir:
            return False, "Job has no timelapse directory", None

        timelapse_dir = Path(interrupted_job.timelapse_dir)
        if not timelapse_dir.exists():
            return False, "Timelapse directory no longer exists", None

        frame_info = await self.get_interrupted_frame_info(
            interrupted_job.id, interrupted_job.timelapse_dir
        )
        if frame_info["frame_count"] == 0:
            return False, "No frames to process", None

        # Generate video
        output_path = await assemble_video(
            timelapse_dir=timelapse_dir,
            fps=output_fps,
            camera_id=camera_id,
        )

        if output_path:
            # Mark original job as completed
            await job_repo.mark_completed(interrupted_job.id, output_path)
            await session.commit()
            return True, f"Video generated: {output_path}", interrupted_job.id
        else:
            return False, "Failed to generate video", interrupted_job.id

    async def cleanup_interrupted(
        self,
        camera_id: int,
        session: AsyncSession,
    ) -> tuple[bool, str, dict]:
        """Delete frames from interrupted timelapse.

        Args:
            camera_id: Camera database ID
            session: Database session

        Returns:
            Tuple of (success: bool, message: str, stats: dict)
        """
        job_repo = JobRepository(session)
        interrupted_job = await job_repo.get_interrupted_timelapse(camera_id)

        if not interrupted_job:
            return False, "No interrupted timelapse found", {}

        timelapse_dir = interrupted_job.timelapse_dir
        frame_info = await self.get_interrupted_frame_info(
            interrupted_job.id,
            timelapse_dir or "",
        )

        # Delete frames directory
        if timelapse_dir:
            frames_dir = Path(timelapse_dir)
            if frames_dir.exists():
                shutil.rmtree(frames_dir)

        # Mark job as failed/cleaned
        await job_repo.mark_failed(interrupted_job.id, "Cleaned up by user")
        await session.commit()

        logger.info(
            "timelapse_cleanup_completed",
            camera_id=camera_id,
            job_id=interrupted_job.id,
            frames_deleted=frame_info["frame_count"],
            space_freed=frame_info["disk_usage_human"],
        )

        return True, "Timelapse frames deleted", {
            "frames_deleted": frame_info["frame_count"],
            "space_freed_bytes": frame_info["disk_usage_bytes"],
            "space_freed_human": frame_info["disk_usage_human"],
        }

    async def stop_all_timelapses(
        self, session: AsyncSession | None = None
    ) -> list[tuple[int, bool, str | None]]:
        """Stop all active timelapse captures.

        Args:
            session: Database session for Job updates (optional)

        Returns:
            List of (camera_id, success, output_path) tuples
        """
        results = []
        camera_ids = list(self._sessions.keys())
        for camera_id in camera_ids:
            success, _, output_path = await self.stop_timelapse(
                camera_id, session, assemble_video_flag=True
            )
            results.append((camera_id, success, output_path))
        return results

    async def update_job_progress(
        self, camera_id: int, session: AsyncSession
    ) -> bool:
        """Update job progress in database.

        Args:
            camera_id: Camera database ID
            session: Database session

        Returns:
            True if updated successfully
        """
        if camera_id not in self._sessions:
            return False

        timelapse_session = self._sessions[camera_id]
        job_id = timelapse_session.job_id

        if not job_id:
            return False

        job_repo = JobRepository(session)
        await job_repo.update_timelapse_progress(job_id, timelapse_session.frame_count)
        await session.commit()
        return True

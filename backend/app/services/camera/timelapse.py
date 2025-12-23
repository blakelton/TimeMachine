"""Timelapse capture and assembly service with Job tracking."""

import asyncio
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.resources import check_resources_available, encoder_semaphore
from app.db.repositories.job import JobRepository
from app.services.camera.capture import CaptureService

logger = get_logger(__name__)


class TimelapseConfig:
    """Configuration for a timelapse capture session."""

    def __init__(
        self,
        camera_id: int,
        interval_seconds: int = 60,
        total_frames: int | None = None,
        duration_hours: float | None = None,
        quality: int = 95,
        resolution: tuple[int, int] = (1920, 1080),
        output_fps: int = 30,
    ):
        """Initialize timelapse configuration.

        Args:
            camera_id: Camera ID
            interval_seconds: Seconds between captures (default 60)
            total_frames: Total frames to capture (optional)
            duration_hours: Total duration in hours (optional)
            quality: JPEG quality 1-100 (default 95)
            resolution: Output resolution (default 1920x1080)
            output_fps: Output video FPS (default 30)
        """
        self.camera_id = camera_id
        self.interval_seconds = interval_seconds
        self.quality = quality
        self.resolution = resolution
        self.output_fps = output_fps

        # Calculate total frames from duration if provided
        if total_frames:
            self.total_frames = total_frames
        elif duration_hours:
            frames_per_hour = 3600 / interval_seconds
            self.total_frames = int(duration_hours * frames_per_hour)
        else:
            self.total_frames = None  # Unlimited until stopped

    def to_dict(self) -> dict:
        """Convert config to dictionary for database storage."""
        return {
            "interval_seconds": self.interval_seconds,
            "total_frames": self.total_frames,
            "quality": self.quality,
            "resolution": list(self.resolution),
            "output_fps": self.output_fps,
        }

    @classmethod
    def from_dict(cls, camera_id: int, data: dict) -> "TimelapseConfig":
        """Create config from dictionary."""
        return cls(
            camera_id=camera_id,
            interval_seconds=data.get("interval_seconds", 60),
            total_frames=data.get("total_frames"),
            quality=data.get("quality", 95),
            resolution=tuple(data.get("resolution", [1920, 1080])),
            output_fps=data.get("output_fps", 30),
        )


class TimelapseSession:
    """Active timelapse capture session."""

    def __init__(
        self,
        config: TimelapseConfig,
        device_path: str,
        camera_type: str,
        job_id: int | None,
        timelapse_dir: Path,
    ):
        self.config = config
        self.device_path = device_path
        self.camera_type = camera_type
        self.job_id = job_id
        self.timelapse_dir = timelapse_dir
        self.frame_count = 0
        self.started_at = datetime.utcnow()
        self._stop_event = asyncio.Event()
        self._capture_task: asyncio.Task | None = None
        self._capture_service = CaptureService()

    @property
    def is_running(self) -> bool:
        """Check if session is running."""
        return self._capture_task is not None and not self._capture_task.done()

    def get_progress(self) -> tuple[int, int | None]:
        """Get current progress.

        Returns:
            Tuple of (current_frame, total_frames or None if unlimited)
        """
        return self.frame_count, self.config.total_frames

    async def start(self) -> bool:
        """Start the timelapse capture loop.

        Returns:
            True if started successfully
        """
        if self.is_running:
            return False

        self._stop_event.clear()
        self._capture_task = asyncio.create_task(self._capture_loop())
        return True

    async def stop(self) -> int:
        """Stop the timelapse capture.

        Returns:
            Number of frames captured
        """
        self._stop_event.set()
        if self._capture_task:
            try:
                await asyncio.wait_for(self._capture_task, timeout=10.0)
            except asyncio.TimeoutError:
                self._capture_task.cancel()
                try:
                    await self._capture_task
                except asyncio.CancelledError:
                    pass
        return self.frame_count

    async def _capture_loop(self) -> None:
        """Main capture loop."""
        logger.info(
            "timelapse_capture_started",
            camera_id=self.config.camera_id,
            interval=self.config.interval_seconds,
            total_frames=self.config.total_frames,
        )

        while not self._stop_event.is_set():
            # Check if we've reached the target frame count
            if self.config.total_frames and self.frame_count >= self.config.total_frames:
                logger.info(
                    "timelapse_target_reached",
                    camera_id=self.config.camera_id,
                    frame_count=self.frame_count,
                )
                break

            # Check resources before each capture
            resources_ok, reason = await check_resources_available(
                f"timelapse_camera_{self.config.camera_id}",
                min_memory_mb=50,
                min_disk_mb=100,
            )
            if not resources_ok:
                logger.warning(
                    "timelapse_resource_issue",
                    camera_id=self.config.camera_id,
                    reason=reason,
                )
                # Wait and retry
                await asyncio.sleep(30)
                continue

            # Generate frame filename with zero-padded number
            frame_filename = f"frame_{self.frame_count:06d}"
            output_file = self.timelapse_dir / f"{frame_filename}.jpg"

            # Capture frame
            success, message, filepath = await self._capture_service.capture_image(
                camera_id=self.config.camera_id,
                device_path=self.device_path,
                camera_type=self.camera_type,
                filename=str(output_file.with_suffix("")),
            )

            if success:
                self.frame_count += 1
                logger.debug(
                    "timelapse_frame_captured",
                    camera_id=self.config.camera_id,
                    frame=self.frame_count,
                    filepath=filepath,
                )
            else:
                logger.warning(
                    "timelapse_frame_failed",
                    camera_id=self.config.camera_id,
                    frame=self.frame_count,
                    error=message,
                )

            # Wait for next capture interval
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.config.interval_seconds,
                )
                # If we get here, stop was requested
                break
            except asyncio.TimeoutError:
                # Normal timeout, continue to next capture
                pass

        logger.info(
            "timelapse_capture_stopped",
            camera_id=self.config.camera_id,
            frame_count=self.frame_count,
        )


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
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                timelapse_dir = Path(settings.media_path) / "timelapses" / f"camera{camera_id}_{timestamp}"
                timelapse_dir.mkdir(parents=True, exist_ok=True)

            # Create Job record if session provided
            if session:
                job_repo = JobRepository(session)
                job = await job_repo.create(
                    camera_id=camera_id,
                    job_type="timelapse",
                    status="running",
                    timelapse_config=config.to_dict(),
                    timelapse_progress=0,
                    timelapse_dir=str(timelapse_dir),
                )
                job_id = job.id
                await session.commit()

            # Create and start session
            timelapse_session = TimelapseSession(
                config=config,
                device_path=device_path,
                camera_type=camera_type,
                job_id=job_id,
                timelapse_dir=timelapse_dir,
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
        assemble_video: bool = True,
    ) -> tuple[bool, str, str | None]:
        """Stop a timelapse capture and optionally assemble video.

        Args:
            camera_id: Camera database ID
            session: Database session for Job update (optional)
            assemble_video: Whether to assemble frames into video

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
        if assemble_video and frame_count > 0:
            # Assemble video from frames
            output_path = await self._assemble_video(
                timelapse_dir=timelapse_dir,
                fps=config.output_fps,
                camera_id=camera_id,
            )

        # Update job status
        if session and job_id:
            job_repo = JobRepository(session)
            if output_path:
                await job_repo.mark_completed(job_id, output_path)
            elif frame_count > 0:
                await job_repo.mark_completed(job_id, str(timelapse_dir))
            else:
                await job_repo.mark_interrupted(job_id)
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

        if job.status != "interrupted":
            return False, f"Job {job_id} is not in interrupted state"

        if job.job_type != "timelapse":
            return False, f"Job {job_id} is not a timelapse job"

        if not job.timelapse_dir:
            return False, "Job has no timelapse directory"

        # Check if already running
        camera_id = job.camera_id
        if camera_id in self._sessions and self._sessions[camera_id].is_running:
            return False, f"Timelapse already running for camera {camera_id}"

        # Restore config
        config = TimelapseConfig.from_dict(camera_id, job.timelapse_config or {})

        # Count existing frames
        timelapse_dir = Path(job.timelapse_dir)
        if not timelapse_dir.exists():
            return False, "Timelapse directory no longer exists"

        existing_frames = len(list(timelapse_dir.glob("frame_*.jpg")))

        # Adjust remaining frames
        if config.total_frames:
            remaining = config.total_frames - existing_frames
            if remaining <= 0:
                return False, "Timelapse already completed"
            config.total_frames = remaining

        # Create new session starting from existing frame count
        timelapse_session = TimelapseSession(
            config=config,
            device_path=device_path,
            camera_type=camera_type,
            job_id=job_id,
            timelapse_dir=timelapse_dir,
        )
        timelapse_session.frame_count = existing_frames

        # Update job status
        await job_repo.update(job_id, status="running")
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
            "disk_usage_human": self._format_size(total_size),
        }

    def _format_size(self, size_bytes: int) -> str:
        """Format bytes as human-readable size.

        Args:
            size_bytes: Size in bytes

        Returns:
            Human-readable size string
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

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
        output_path = await self._assemble_video(
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
                camera_id, session, assemble_video=True
            )
            results.append((camera_id, success, output_path))
        return results

    async def _assemble_video(
        self,
        timelapse_dir: Path,
        fps: int,
        camera_id: int,
    ) -> str | None:
        """Assemble timelapse frames into video using ffmpeg.

        Args:
            timelapse_dir: Directory containing frame images
            fps: Output video frames per second
            camera_id: Camera ID for logging

        Returns:
            Output video path or None on failure
        """
        # Check for ffmpeg
        output_file = timelapse_dir.parent / f"{timelapse_dir.name}.mp4"

        # Acquire encoder for assembly
        owner_id = f"camera_{camera_id}_timelapse_assembly"
        acquired = await encoder_semaphore.acquire(owner_id)

        if not acquired:
            logger.warning(
                "timelapse_assembly_encoder_busy",
                camera_id=camera_id,
                current_owner=encoder_semaphore.current_owner(),
            )
            return None

        try:
            # Build ffmpeg command for image sequence to video
            # Using glob pattern for frame files
            cmd = (
                f"ffmpeg -y -framerate {fps} "
                f"-pattern_type glob -i '{timelapse_dir}/frame_*.jpg' "
                f"-c:v libx264 -preset medium -crf 23 "
                f"-pix_fmt yuv420p "
                f"'{output_file}'"
            )

            logger.info(
                "timelapse_assembly_starting",
                camera_id=camera_id,
                input_dir=str(timelapse_dir),
                output=str(output_file),
                fps=fps,
            )

            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600.0)

            if proc.returncode == 0 and output_file.exists():
                file_size_mb = output_file.stat().st_size / (1024 * 1024)
                logger.info(
                    "timelapse_assembly_success",
                    camera_id=camera_id,
                    output=str(output_file),
                    size_mb=file_size_mb,
                )
                return str(output_file)
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(
                    "timelapse_assembly_failed",
                    camera_id=camera_id,
                    returncode=proc.returncode,
                    error=error_msg,
                )
                return None

        except asyncio.TimeoutError:
            logger.error("timelapse_assembly_timeout", camera_id=camera_id)
            return None
        except Exception as e:
            logger.error("timelapse_assembly_exception", camera_id=camera_id, error=str(e))
            return None
        finally:
            encoder_semaphore.release(owner_id)

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


# Global timelapse service instance
timelapse_service = TimelapseService()

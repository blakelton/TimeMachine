"""Camera recording service with H.264 encoding and Job tracking."""

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import JobStatus
from app.core.logging import get_logger
from app.core.resources import check_resources_available, encoder_semaphore
from app.db.repositories.job import JobRepository
from app.services.camera.pipeline import ManagedPipeline, PipelineConfig, PipelineState

logger = get_logger(__name__)


class RecordingService:
    """Service for managing camera recordings.

    Uses H.264 hardware encoder (single instance via semaphore).
    Tracks recordings with PID and state management.
    Creates Job database records for tracking.
    Uses EOS signal for clean MP4 file finalization.
    """

    def __init__(self):
        self._recordings: Dict[int, ManagedPipeline] = {}
        self._recording_files: Dict[int, str] = {}
        self._job_ids: Dict[int, int] = {}  # camera_id -> job_id

    async def start_recording(
        self,
        camera_id: int,
        device_path: str,
        camera_type: str,
        session: AsyncSession | None = None,
        duration_seconds: int | None = None,
        filename: str | None = None,
    ) -> tuple[bool, str, int | None]:
        """Start recording from a camera.

        Args:
            camera_id: Camera database ID
            device_path: Camera device path
            camera_type: Camera type ('csi' or 'usb')
            session: Database session for Job creation (optional)
            duration_seconds: Optional duration limit
            filename: Optional custom filename (without extension)

        Returns:
            Tuple of (success: bool, message: str, job_id: int | None)
        """
        # Check if already recording
        if camera_id in self._recordings:
            pipeline = self._recordings[camera_id]
            if pipeline.get_state() == PipelineState.RUNNING:
                return False, f"Camera {camera_id} is already recording", None

        # Estimate disk space needed (rough estimate: 500KB/s for H.264 1080p)
        estimated_mb = 500  # Minimum
        if duration_seconds:
            estimated_mb = max(500, (duration_seconds * 500) // 1000)

        # Check system resources
        resources_ok, reason = await check_resources_available(
            f"recording_camera_{camera_id}", min_memory_mb=100, min_disk_mb=estimated_mb
        )
        if not resources_ok:
            return False, reason, None

        # Try to acquire encoder semaphore
        owner_id = f"camera_{camera_id}_recording"
        acquired = await encoder_semaphore.acquire(owner_id)

        if not acquired:
            current_owner = encoder_semaphore.current_owner()
            return (
                False,
                f"H.264 encoder busy (in use by {current_owner})",
                None,
            )

        job_id: int | None = None
        try:
            # Handle filename/path
            if not filename:
                # Generate default filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"camera{camera_id}_{timestamp}"
                recording_path = Path(settings.media_path) / "recordings"
                recording_path.mkdir(parents=True, exist_ok=True)
                output_file = recording_path / f"{filename}.mp4"
            elif filename.startswith("/"):
                # Absolute path provided - use it directly (ensure parent exists)
                output_file = Path(filename)
                if not output_file.suffix:
                    output_file = output_file.with_suffix(".mp4")
                output_file.parent.mkdir(parents=True, exist_ok=True)
            else:
                # Relative filename - put in recordings directory
                recording_path = Path(settings.media_path) / "recordings"
                recording_path.mkdir(parents=True, exist_ok=True)
                output_file = recording_path / f"{filename}.mp4"

            self._recording_files[camera_id] = str(output_file)

            # Create Job record if session provided
            if session:
                job_repo = JobRepository(session)
                job = await job_repo.create(
                    camera_id=camera_id,
                    job_type="recording",
                    status=JobStatus.RUNNING,
                    output_path=str(output_file),
                )
                job_id = job.id
                self._job_ids[camera_id] = job_id
                await session.commit()

            # Build GStreamer pipeline based on camera type
            if camera_type == "csi":
                pipeline_cmd = self._build_csi_recording_pipeline(
                    camera_id, device_path, str(output_file), duration_seconds
                )
            else:  # usb
                pipeline_cmd = self._build_usb_recording_pipeline(
                    camera_id, device_path, str(output_file), duration_seconds
                )

            # Create managed pipeline with EOS support for clean file finalization
            config = PipelineConfig(
                pipeline_cmd=pipeline_cmd,
                description=f"Recording for camera {camera_id}",
                camera_id=camera_id,
                restart_on_crash=False,  # Don't auto-restart recordings
                max_restarts=0,
                use_eos_on_stop=True,  # Send EOS for clean MP4 finalization
            )

            pipeline = ManagedPipeline(config)
            success = await pipeline.start()

            if success:
                self._recordings[camera_id] = pipeline
                logger.info(
                    "recording_started",
                    camera_id=camera_id,
                    device=device_path,
                    output=str(output_file),
                    duration=duration_seconds,
                    pid=pipeline.get_pid(),
                    job_id=job_id,
                )
                return True, f"Recording started: {output_file}", job_id
            else:
                # Release encoder if pipeline failed to start
                encoder_semaphore.release(owner_id)
                # Mark job as failed if created
                if session and job_id:
                    job_repo = JobRepository(session)
                    await job_repo.mark_failed(job_id, "Failed to start pipeline")
                    await session.commit()
                    del self._job_ids[camera_id]
                return False, "Failed to start recording pipeline", None

        except Exception as e:
            # Release encoder on exception
            encoder_semaphore.release(owner_id)
            # Mark job as failed if created
            if session and job_id:
                try:
                    job_repo = JobRepository(session)
                    await job_repo.mark_failed(job_id, str(e))
                    await session.commit()
                except Exception:
                    pass
                if camera_id in self._job_ids:
                    del self._job_ids[camera_id]
            logger.error(
                "recording_start_exception", camera_id=camera_id, error=str(e)
            )
            return False, f"Recording error: {str(e)}", None

    async def stop_recording(
        self, camera_id: int, session: AsyncSession | None = None, force: bool = False
    ) -> tuple[bool, str, str | None]:
        """Stop recording for a camera.

        Args:
            camera_id: Camera database ID
            session: Database session for Job update (optional)
            force: Skip EOS and immediately terminate

        Returns:
            Tuple of (success: bool, message: str, filepath: str | None)
        """
        if camera_id not in self._recordings:
            return False, f"No recording active for camera {camera_id}", None

        pipeline = self._recordings[camera_id]
        output_file = self._recording_files.get(camera_id)
        job_id = self._job_ids.get(camera_id)

        # Stop the pipeline (will use EOS if configured)
        success = await pipeline.stop(force=force)

        # Release encoder semaphore
        owner_id = f"camera_{camera_id}_recording"
        encoder_semaphore.release(owner_id)

        # Clean up tracking
        del self._recordings[camera_id]
        if camera_id in self._recording_files:
            del self._recording_files[camera_id]
        if camera_id in self._job_ids:
            del self._job_ids[camera_id]

        if success:
            # Check if file exists and get size
            if output_file and Path(output_file).exists():
                file_size_mb = Path(output_file).stat().st_size / (1024 * 1024)
                logger.info(
                    "recording_stopped",
                    camera_id=camera_id,
                    output=output_file,
                    size_mb=file_size_mb,
                    job_id=job_id,
                )
                # Update job status
                if session and job_id:
                    job_repo = JobRepository(session)
                    await job_repo.mark_completed(job_id, output_file)
                    await session.commit()
                return True, "Recording stopped", output_file
            else:
                logger.warning(
                    "recording_stopped_no_file", camera_id=camera_id, output=output_file
                )
                # Mark job as failed
                if session and job_id:
                    job_repo = JobRepository(session)
                    await job_repo.mark_failed(job_id, "Output file not created")
                    await session.commit()
                return True, "Recording stopped (file not found)", None
        else:
            # Mark job as interrupted
            if session and job_id:
                job_repo = JobRepository(session)
                await job_repo.mark_interrupted(job_id)
                await session.commit()
            return False, "Failed to stop recording", None

    def get_recording_state(self, camera_id: int) -> Optional[PipelineState]:
        """Get recording state for a camera.

        Args:
            camera_id: Camera database ID

        Returns:
            Pipeline state or None if not recording
        """
        if camera_id in self._recordings:
            return self._recordings[camera_id].get_state()
        return None

    def get_recording_pid(self, camera_id: int) -> Optional[int]:
        """Get recording process PID.

        Args:
            camera_id: Camera database ID

        Returns:
            PID or None
        """
        if camera_id in self._recordings:
            return self._recordings[camera_id].get_pid()
        return None

    def get_recording_uptime(self, camera_id: int) -> Optional[float]:
        """Get recording uptime in seconds.

        Args:
            camera_id: Camera database ID

        Returns:
            Uptime in seconds or None
        """
        if camera_id in self._recordings:
            return self._recordings[camera_id].get_uptime_seconds()
        return None

    def get_recording_job_id(self, camera_id: int) -> Optional[int]:
        """Get the Job ID for an active recording.

        Args:
            camera_id: Camera database ID

        Returns:
            Job ID or None
        """
        return self._job_ids.get(camera_id)

    def get_active_recordings(self) -> list[int]:
        """Get list of camera IDs with active recordings.

        Returns:
            List of camera IDs
        """
        return [
            cam_id
            for cam_id, pipeline in self._recordings.items()
            if pipeline.get_state() == PipelineState.RUNNING
        ]

    async def stop_all_recordings(
        self, session: AsyncSession | None = None
    ) -> list[tuple[int, bool, str | None]]:
        """Stop all active recordings.

        Args:
            session: Database session for Job updates (optional)

        Returns:
            List of (camera_id, success, filepath) tuples
        """
        results = []
        camera_ids = list(self._recordings.keys())
        for camera_id in camera_ids:
            success, _, filepath = await self.stop_recording(camera_id, session)
            results.append((camera_id, success, filepath))
        return results

    def _build_csi_recording_pipeline(
        self,
        camera_id: int,
        device_path: str,
        output_file: str,
        duration_seconds: int | None,
    ) -> str:
        """Build GStreamer pipeline for CSI camera recording.

        Args:
            camera_id: Camera ID
            device_path: Device path
            output_file: Output file path
            duration_seconds: Optional duration limit

        Returns:
            GStreamer pipeline command
        """
        # CSI camera with H.264 hardware encoder
        # Using -e flag for EOS handling
        cmd = (
            f"gst-launch-1.0 -e "
            f"libcamerasrc ! "
            f"video/x-raw,width=1920,height=1080,framerate=30/1 ! "
            f"v4l2h264enc extra-controls=\"controls,h264_profile=4,video_bitrate=4000000\" ! "
            f"h264parse ! "
            f"mp4mux ! "
            f"filesink location={output_file}"
        )

        # Add duration if specified (timeout will send SIGINT for EOS)
        if duration_seconds:
            cmd = f"timeout --signal=INT {duration_seconds} " + cmd

        return cmd

    def _build_usb_recording_pipeline(
        self,
        camera_id: int,
        device_path: str,
        output_file: str,
        duration_seconds: int | None,
    ) -> str:
        """Build GStreamer pipeline for USB camera recording.

        USB cameras typically don't support hardware h264 encoding, so we use
        software encoding (x264enc) at the camera's native resolution.

        Args:
            camera_id: Camera ID
            device_path: Device path
            output_file: Output file path
            duration_seconds: Optional duration limit

        Returns:
            GStreamer pipeline command
        """
        # USB camera with x264 software encoder at native resolution
        # Most USB webcams only support 640x480 or 1280x720 at best
        # Using videorate to ensure consistent framerate for encoding
        # x264enc produces widely compatible H.264 streams
        # Using -e flag for EOS handling
        cmd = (
            f"gst-launch-1.0 -e "
            f"v4l2src device={device_path} ! "
            f"video/x-raw,format=YUY2,width=640,height=480 ! "
            f"videorate ! video/x-raw,framerate=30/1 ! "
            f"videoconvert ! "
            f"x264enc tune=zerolatency speed-preset=ultrafast bitrate=2000 ! "
            f"h264parse ! "
            f"mp4mux ! "
            f"filesink location={output_file}"
        )

        # Add duration if specified (timeout will send SIGINT for EOS)
        if duration_seconds:
            cmd = f"timeout --signal=INT {duration_seconds} " + cmd

        return cmd

    @staticmethod
    def estimate_disk_usage_mb(duration_seconds: int, bitrate_kbps: int = 4000) -> int:
        """Estimate disk usage for a recording.

        Args:
            duration_seconds: Recording duration
            bitrate_kbps: Video bitrate in kbps (default 4000)

        Returns:
            Estimated file size in MB
        """
        # Convert bitrate from kbps to bytes per second
        bytes_per_second = (bitrate_kbps * 1000) / 8
        total_bytes = bytes_per_second * duration_seconds
        # Add 10% overhead for container, audio, etc.
        return int((total_bytes * 1.1) / (1024 * 1024))


# Global recording service instance
recording_service = RecordingService()

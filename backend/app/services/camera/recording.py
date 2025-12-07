"""Camera recording service with H.264 encoding."""

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.resources import check_resources_available, encoder_semaphore
from app.db.repositories.camera import CameraRepository
from app.services.camera.pipeline import ManagedPipeline, PipelineConfig, PipelineState

logger = get_logger(__name__)


class RecordingService:
    """Service for managing camera recordings.

    Uses H.264 hardware encoder (single instance via semaphore).
    Tracks recordings with PID and state management.
    """

    def __init__(self):
        self._recordings: Dict[int, ManagedPipeline] = {}
        self._recording_files: Dict[int, str] = {}

    async def start_recording(
        self,
        camera_id: int,
        device_path: str,
        camera_type: str,
        duration_seconds: int | None = None,
        filename: str | None = None,
    ) -> tuple[bool, str]:
        """Start recording from a camera.

        Args:
            camera_id: Camera database ID
            device_path: Camera device path
            camera_type: Camera type ('csi' or 'usb')
            duration_seconds: Optional duration limit
            filename: Optional custom filename (without extension)

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Check if already recording
        if camera_id in self._recordings:
            pipeline = self._recordings[camera_id]
            if pipeline.get_state() == PipelineState.RUNNING:
                return False, f"Camera {camera_id} is already recording"

        # Check system resources (recordings need more disk space)
        resources_ok, reason = await check_resources_available(
            f"recording_camera_{camera_id}", min_memory_mb=100, min_disk_mb=1000
        )
        if not resources_ok:
            return False, reason

        # Try to acquire encoder semaphore
        owner_id = f"camera_{camera_id}_recording"
        acquired = await encoder_semaphore.acquire(owner_id)

        if not acquired:
            current_owner = encoder_semaphore.current_owner()
            return (
                False,
                f"H.264 encoder busy (in use by {current_owner})",
            )

        try:
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"camera{camera_id}_{timestamp}"

            # Ensure recording base path exists
            recording_path = Path(settings.media_path) / "recordings"
            recording_path.mkdir(parents=True, exist_ok=True)

            # Full output path
            output_file = recording_path / f"{filename}.mp4"
            self._recording_files[camera_id] = str(output_file)

            # Build GStreamer pipeline based on camera type
            if camera_type == "csi":
                pipeline_cmd = self._build_csi_recording_pipeline(
                    camera_id, device_path, str(output_file), duration_seconds
                )
            else:  # usb
                pipeline_cmd = self._build_usb_recording_pipeline(
                    camera_id, device_path, str(output_file), duration_seconds
                )

            # Create managed pipeline
            config = PipelineConfig(
                pipeline_cmd=pipeline_cmd,
                description=f"Recording for camera {camera_id}",
                camera_id=camera_id,
                restart_on_crash=False,  # Don't auto-restart recordings
                max_restarts=0,
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
                )
                return True, f"Recording started: {output_file}"
            else:
                # Release encoder if pipeline failed to start
                encoder_semaphore.release(owner_id)
                return False, "Failed to start recording pipeline"

        except Exception as e:
            # Release encoder on exception
            encoder_semaphore.release(owner_id)
            logger.error(
                "recording_start_exception", camera_id=camera_id, error=str(e)
            )
            return False, f"Recording error: {str(e)}"

    async def stop_recording(self, camera_id: int) -> tuple[bool, str, str | None]:
        """Stop recording for a camera.

        Args:
            camera_id: Camera database ID

        Returns:
            Tuple of (success: bool, message: str, filepath: str | None)
        """
        if camera_id not in self._recordings:
            return False, f"No recording active for camera {camera_id}", None

        pipeline = self._recordings[camera_id]
        output_file = self._recording_files.get(camera_id)

        # Stop the pipeline
        success = await pipeline.stop()

        # Release encoder semaphore
        owner_id = f"camera_{camera_id}_recording"
        encoder_semaphore.release(owner_id)

        # Clean up tracking
        del self._recordings[camera_id]
        if camera_id in self._recording_files:
            del self._recording_files[camera_id]

        if success:
            # Check if file exists and get size
            if output_file and Path(output_file).exists():
                file_size_mb = Path(output_file).stat().st_size / (1024 * 1024)
                logger.info(
                    "recording_stopped",
                    camera_id=camera_id,
                    output=output_file,
                    size_mb=file_size_mb,
                )
                return True, "Recording stopped", output_file
            else:
                logger.warning(
                    "recording_stopped_no_file", camera_id=camera_id, output=output_file
                )
                return True, "Recording stopped (file not found)", None
        else:
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

    async def stop_all_recordings(self) -> None:
        """Stop all active recordings."""
        camera_ids = list(self._recordings.keys())
        for camera_id in camera_ids:
            await self.stop_recording(camera_id)

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
        cmd = (
            f"gst-launch-1.0 -e "
            f"libcamerasrc ! "
            f"video/x-raw,width=1920,height=1080,framerate=30/1 ! "
            f"v4l2h264enc extra-controls=\"controls,h264_profile=4,video_bitrate=4000000\" ! "
            f"h264parse ! "
            f"mp4mux ! "
            f"filesink location={output_file}"
        )

        # Add duration if specified
        if duration_seconds:
            # GStreamer uses nanoseconds
            duration_ns = duration_seconds * 1_000_000_000
            cmd = f"timeout {duration_seconds} " + cmd

        return cmd

    def _build_usb_recording_pipeline(
        self,
        camera_id: int,
        device_path: str,
        output_file: str,
        duration_seconds: int | None,
    ) -> str:
        """Build GStreamer pipeline for USB camera recording.

        Args:
            camera_id: Camera ID
            device_path: Device path
            output_file: Output file path
            duration_seconds: Optional duration limit

        Returns:
            GStreamer pipeline command
        """
        # USB camera with H.264 hardware encoder
        cmd = (
            f"gst-launch-1.0 -e "
            f"v4l2src device={device_path} ! "
            f"video/x-raw,width=1920,height=1080,framerate=30/1 ! "
            f"v4l2h264enc extra-controls=\"controls,h264_profile=4,video_bitrate=4000000\" ! "
            f"h264parse ! "
            f"mp4mux ! "
            f"filesink location={output_file}"
        )

        # Add duration if specified
        if duration_seconds:
            cmd = f"timeout {duration_seconds} " + cmd

        return cmd


# Global recording service instance
recording_service = RecordingService()

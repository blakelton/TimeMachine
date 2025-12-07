"""Camera preview service using GStreamer MJPEG streaming."""

from typing import Dict, Optional

from app.core.logging import get_logger
from app.core.resources import check_resources_available
from app.services.camera.pipeline import ManagedPipeline, PipelineConfig, PipelineState

logger = get_logger(__name__)


class PreviewService:
    """Service for managing camera preview streams.

    Uses GStreamer to generate MJPEG streams over HTTP.
    Each camera can have one active preview at a time.
    """

    def __init__(self):
        self._previews: Dict[int, ManagedPipeline] = {}

    async def start_preview(
        self, camera_id: int, device_path: str, camera_type: str, port: int = 8080
    ) -> tuple[bool, str]:
        """Start preview stream for a camera.

        Args:
            camera_id: Camera database ID
            device_path: Camera device path
            camera_type: Camera type ('csi' or 'usb')
            port: HTTP port for MJPEG stream

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Check if preview already running
        if camera_id in self._previews:
            pipeline = self._previews[camera_id]
            if pipeline.get_state() == PipelineState.RUNNING:
                return False, f"Preview already running for camera {camera_id}"

        # Check system resources
        resources_ok, reason = await check_resources_available(
            f"preview_camera_{camera_id}", min_memory_mb=100
        )
        if not resources_ok:
            return False, reason

        # Build GStreamer pipeline based on camera type
        if camera_type == "csi":
            pipeline_cmd = self._build_csi_preview_pipeline(
                camera_id, device_path, port
            )
        else:  # usb
            pipeline_cmd = self._build_usb_preview_pipeline(
                camera_id, device_path, port
            )

        # Create managed pipeline
        config = PipelineConfig(
            pipeline_cmd=pipeline_cmd,
            description=f"Preview for camera {camera_id}",
            camera_id=camera_id,
            restart_on_crash=True,
            max_restarts=3,
            restart_delay_seconds=5,
        )

        pipeline = ManagedPipeline(config)
        success = await pipeline.start()

        if success:
            self._previews[camera_id] = pipeline
            logger.info(
                "preview_started",
                camera_id=camera_id,
                device=device_path,
                port=port,
                pid=pipeline.get_pid(),
            )
            return True, f"Preview started on port {port}"
        else:
            return False, "Failed to start preview pipeline"

    async def stop_preview(self, camera_id: int) -> tuple[bool, str]:
        """Stop preview stream for a camera.

        Args:
            camera_id: Camera database ID

        Returns:
            Tuple of (success: bool, message: str)
        """
        if camera_id not in self._previews:
            return False, f"No preview running for camera {camera_id}"

        pipeline = self._previews[camera_id]
        success = await pipeline.stop()

        if success:
            del self._previews[camera_id]
            logger.info("preview_stopped", camera_id=camera_id)
            return True, "Preview stopped"
        else:
            return False, "Failed to stop preview"

    def get_preview_state(self, camera_id: int) -> Optional[PipelineState]:
        """Get preview state for a camera.

        Args:
            camera_id: Camera database ID

        Returns:
            Pipeline state or None if no preview
        """
        if camera_id in self._previews:
            return self._previews[camera_id].get_state()
        return None

    def get_preview_port(self, camera_id: int) -> Optional[int]:
        """Get preview port for a camera.

        Args:
            camera_id: Camera database ID

        Returns:
            Port number or None
        """
        # For now, return base port + camera_id
        # In production, track ports properly
        if camera_id in self._previews:
            return 8080 + camera_id
        return None

    async def stop_all_previews(self) -> None:
        """Stop all active previews."""
        camera_ids = list(self._previews.keys())
        for camera_id in camera_ids:
            await self.stop_preview(camera_id)

    def _build_csi_preview_pipeline(
        self, camera_id: int, device_path: str, port: int
    ) -> str:
        """Build GStreamer pipeline for CSI camera preview.

        Args:
            camera_id: Camera ID
            device_path: Device path
            port: HTTP port

        Returns:
            GStreamer pipeline command
        """
        # CSI camera using libcamerasrc
        # Output: MJPEG over HTTP
        return (
            f"gst-launch-1.0 -v "
            f"libcamerasrc ! "
            f"video/x-raw,width=1280,height=720,framerate=15/1 ! "
            f"videoconvert ! "
            f"jpegenc quality=50 ! "
            f"multipartmux boundary=--frame ! "
            f"tcpserversink host=0.0.0.0 port={port}"
        )

    def _build_usb_preview_pipeline(
        self, camera_id: int, device_path: str, port: int
    ) -> str:
        """Build GStreamer pipeline for USB camera preview.

        Args:
            camera_id: Camera ID
            device_path: Device path
            port: HTTP port

        Returns:
            GStreamer pipeline command
        """
        # USB camera using v4l2src
        # Try MJPEG first, fallback to YUV with jpegenc
        return (
            f"gst-launch-1.0 -v "
            f"v4l2src device={device_path} ! "
            f"image/jpeg,width=1280,height=720,framerate=15/1 ! "
            f"jpegdec ! "
            f"jpegenc quality=50 ! "
            f"multipartmux boundary=--frame ! "
            f"tcpserversink host=0.0.0.0 port={port}"
        )


# Global preview service instance
preview_service = PreviewService()

"""Camera capture service for still images."""

import asyncio
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.core.resources import check_resources_available

logger = get_logger(__name__)


class CaptureService:
    """Service for capturing still images from cameras.

    Note: For timelapse observations, the ObservationService is responsible
    for stopping/restarting the preview stream at the observation boundaries.
    This service does NOT automatically manage the preview - it assumes the
    caller has already ensured the device is available.
    """

    async def capture_image(
        self,
        camera_id: int,
        device_path: str,
        camera_type: str,
        filename: str | None = None,
        output_path: str | None = None,
    ) -> tuple[bool, str, str | None]:
        """Capture a still image from a camera.

        Args:
            camera_id: Camera database ID
            device_path: Camera device path
            camera_type: Camera type ('csi' or 'usb')
            filename: Optional custom filename (without extension), ignored if output_path set
            output_path: Optional full path for output file (with or without .jpg extension)

        Returns:
            Tuple of (success: bool, message: str, filepath: str | None)
        """
        # Check system resources
        resources_ok, reason = await check_resources_available(
            f"capture_camera_{camera_id}", min_memory_mb=50, min_disk_mb=100
        )
        if not resources_ok:
            return False, reason, None

        # Determine output file path
        if output_path:
            # Use provided path
            output_file = Path(output_path)
            if not output_file.suffix:
                output_file = output_file.with_suffix(".jpg")
            output_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            # Generate default path
            if not filename:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"camera{camera_id}_{timestamp}"

            # Ensure still base path exists
            still_path = Path(settings.media_path) / "stills"
            still_path.mkdir(parents=True, exist_ok=True)

            # Full output path
            output_file = still_path / f"{filename}.jpg"

        # Build capture command based on camera type
        if camera_type == "csi":
            cmd = self._build_csi_capture_command(device_path, str(output_file))
        else:  # usb
            cmd = self._build_usb_capture_command(device_path, str(output_file))

        logger.info(
            "capture_starting",
            camera_id=camera_id,
            device=device_path,
            output=str(output_file),
        )

        try:
            # Execute capture command
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10.0)

            if proc.returncode == 0 and output_file.exists():
                file_size_kb = output_file.stat().st_size / 1024

                logger.info(
                    "capture_success",
                    camera_id=camera_id,
                    output=str(output_file),
                    size_kb=file_size_kb,
                )

                return True, "Image captured successfully", str(output_file)
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(
                    "capture_failed",
                    camera_id=camera_id,
                    returncode=proc.returncode,
                    error=error_msg,
                )
                return False, f"Capture failed: {error_msg}", None

        except asyncio.TimeoutError:
            logger.error("capture_timeout", camera_id=camera_id)
            return False, "Capture timeout after 10 seconds", None
        except Exception as e:
            logger.error("capture_exception", camera_id=camera_id, error=str(e))
            return False, f"Capture error: {str(e)}", None

    def _build_csi_capture_command(self, device_path: str, output_file: str) -> str:
        """Build command for CSI camera capture.

        Args:
            device_path: Device path
            output_file: Output file path

        Returns:
            Command string
        """
        # Use libcamera-still for CSI cameras
        # --timeout is in ms: need 2000ms for sensor init + exposure + capture
        return (
            f"libcamera-still "
            f"--timeout 2000 "
            f"--width 1920 --height 1080 "
            f"--output {output_file} "
            f"--nopreview"
        )

    def _build_usb_capture_command(self, device_path: str, output_file: str) -> str:
        """Build command for USB camera capture.

        Args:
            device_path: Device path
            output_file: Output file path

        Returns:
            Command string
        """
        # Use GStreamer for USB cameras
        # Most USB cameras support YUYV - convert to JPEG for output
        # Use 640x480 which is commonly supported by USB cameras
        return (
            f"gst-launch-1.0 -q "
            f"v4l2src device={device_path} num-buffers=1 ! "
            f"video/x-raw,format=YUY2,width=640,height=480 ! "
            f"videoconvert ! "
            f"jpegenc quality=95 ! "
            f"filesink location={output_file}"
        )


# Global capture service instance
capture_service = CaptureService()

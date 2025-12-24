"""Camera preview service using GStreamer MJPEG streaming."""

import asyncio
import os
import signal
import socket
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
        # Track cameras that are in the middle of a capture operation
        # This prevents the dashboard watchdog from auto-starting previews
        self._capture_in_progress: set[int] = set()
        # Track cameras that are currently starting a preview
        # Prevents race conditions from concurrent start requests
        self._starting_preview: set[int] = set()

    def set_capture_in_progress(self, camera_id: int, in_progress: bool) -> None:
        """Mark a camera as having a capture in progress.

        When capture is in progress, preview will refuse to start.
        This prevents the dashboard watchdog from racing with capture.
        """
        if in_progress:
            self._capture_in_progress.add(camera_id)
            logger.debug("capture_lock_acquired", camera_id=camera_id)
        else:
            self._capture_in_progress.discard(camera_id)
            logger.debug("capture_lock_released", camera_id=camera_id)

    def is_capture_in_progress(self, camera_id: int) -> bool:
        """Check if a capture is in progress for a camera."""
        return camera_id in self._capture_in_progress

    async def start_preview(
        self,
        camera_id: int,
        device_path: str,
        camera_type: str,
        port: int = 8080,
        fps: int = 10,
    ) -> tuple[bool, str]:
        """Start preview stream for a camera.

        Args:
            camera_id: Camera database ID
            device_path: Camera device path
            camera_type: Camera type ('csi' or 'usb')
            port: HTTP port for MJPEG stream
            fps: Framerate for preview stream (1-30)

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Check if capture is in progress - refuse to start preview during capture
        if self.is_capture_in_progress(camera_id):
            logger.info(
                "preview_blocked_by_capture",
                camera_id=camera_id,
            )
            return False, f"Capture in progress for camera {camera_id}"

        # Check if another start is already in progress - prevent race conditions
        if camera_id in self._starting_preview:
            logger.info(
                "preview_start_already_in_progress",
                camera_id=camera_id,
            )
            return False, f"Preview start already in progress for camera {camera_id}"

        # Clamp FPS to valid range
        fps = max(1, min(30, fps))
        # Check if preview already exists
        if camera_id in self._previews:
            pipeline = self._previews[camera_id]
            state = pipeline.get_state()
            if state == PipelineState.RUNNING:
                return False, f"Preview already running for camera {camera_id}"
            # Clean up any existing pipeline that's not running (crashed, error, stopped)
            # This ensures we don't leave zombie processes behind
            logger.info(
                "preview_cleanup_before_start",
                camera_id=camera_id,
                old_state=state.value if state else "unknown",
            )
            await self._force_cleanup_preview(camera_id)
            # Brief wait to ensure processes are terminated
            await asyncio.sleep(0.3)

        # Mark that we're starting preview for this camera
        # This prevents concurrent start requests from racing
        self._starting_preview.add(camera_id)

        try:
            # Check system resources
            resources_ok, reason = await check_resources_available(
                f"preview_camera_{camera_id}", min_memory_mb=100
            )
            if not resources_ok:
                return False, reason

            # Build GStreamer pipeline based on camera type
            if camera_type == "csi":
                pipeline_cmd = self._build_csi_preview_pipeline(
                    camera_id, device_path, port, fps
                )
            else:  # usb
                pipeline_cmd = self._build_usb_preview_pipeline(
                    camera_id, device_path, port, fps
                )

            # Create managed pipeline
            # Note: restart_on_crash=False because the dashboard watchdog handles
            # preview recovery. Having both would cause race conditions.
            config = PipelineConfig(
                pipeline_cmd=pipeline_cmd,
                description=f"Preview for camera {camera_id}",
                camera_id=camera_id,
                restart_on_crash=False,
                max_restarts=0,
                restart_delay_seconds=5,
            )

            pipeline = ManagedPipeline(config)
            success = await pipeline.start()

            if not success:
                return False, "Failed to start preview pipeline - check camera device and GStreamer"

            # Store pipeline reference
            self._previews[camera_id] = pipeline

            # Wait for port to be ready - CSI cameras need longer due to rpicam initialization
            # USB cameras are quick (~0.5s), CSI cameras need ~2s for libcamera init
            port_timeout = 2.5 if camera_type == "csi" else 0.8
            port_ready = await self._wait_for_port(port, timeout=port_timeout)

            logger.info(
                "preview_started",
                camera_id=camera_id,
                device=device_path,
                port=port,
                pid=pipeline.get_pid(),
                port_ready=port_ready,
            )
            return True, f"Preview started on port {port}"
        finally:
            # Always release the lock
            self._starting_preview.discard(camera_id)

    async def _wait_for_port(self, port: int, timeout: float = 3.0) -> bool:
        """Wait for TCP port to be ready.

        Args:
            port: Port number to check
            timeout: Maximum time to wait

        Returns:
            True if port is ready, False if timeout
        """
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                # Try to connect to the port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)
                result = sock.connect_ex(("127.0.0.1", port))
                sock.close()
                if result == 0:
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.1)
        return False

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

    def get_preview_pid(self, camera_id: int) -> Optional[int]:
        """Get preview pipeline PID for a camera.

        Args:
            camera_id: Camera database ID

        Returns:
            PID or None
        """
        if camera_id in self._previews:
            return self._previews[camera_id].get_pid()
        return None

    async def stop_all_previews(self) -> None:
        """Stop all active previews."""
        camera_ids = list(self._previews.keys())
        for camera_id in camera_ids:
            await self.stop_preview(camera_id)

    async def _force_cleanup_preview(self, camera_id: int) -> None:
        """Force cleanup of a preview pipeline, including zombie processes.

        This is more aggressive than stop_preview() and handles cases where
        the pipeline is in an error/crashed state but processes are still running.

        Args:
            camera_id: Camera database ID
        """
        if camera_id not in self._previews:
            return

        pipeline = self._previews[camera_id]
        pid = pipeline.get_pid()

        # Try graceful stop first (handles the asyncio monitoring task)
        try:
            await pipeline.stop(force=True)
        except Exception as e:
            logger.warning(
                "preview_cleanup_stop_failed",
                camera_id=camera_id,
                error=str(e),
            )

        # If we have a PID, also kill the process group directly
        # This catches cases where the shell process group wasn't properly terminated
        if pid:
            try:
                # Kill the entire process group to catch piped children
                os.killpg(os.getpgid(pid), signal.SIGKILL)
                logger.info(
                    "preview_cleanup_killed_process_group",
                    camera_id=camera_id,
                    pid=pid,
                )
            except (ProcessLookupError, PermissionError, OSError):
                # Process already gone or not a process group leader
                pass

        # Also clean up any lingering rpicam-vid processes for this camera's port
        # This handles the case where rpicam-vid survives when GStreamer dies
        port = 8080 + camera_id
        await self._kill_processes_on_port(port)

        # Remove from tracking
        del self._previews[camera_id]
        logger.info("preview_cleanup_complete", camera_id=camera_id)

    async def _kill_processes_on_port(self, port: int) -> None:
        """Kill any processes listening on a specific port.

        Args:
            port: TCP port number
        """
        try:
            # Find processes using this port
            proc = await asyncio.create_subprocess_shell(
                f"lsof -t -i:{port} 2>/dev/null",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            pids = stdout.decode().strip().split()

            for pid_str in pids:
                if pid_str:
                    try:
                        pid = int(pid_str)
                        os.kill(pid, signal.SIGKILL)
                        logger.debug(
                            "preview_cleanup_killed_port_process",
                            port=port,
                            pid=pid,
                        )
                    except (ValueError, ProcessLookupError, PermissionError):
                        pass
        except Exception as e:
            logger.debug(
                "preview_cleanup_port_check_failed",
                port=port,
                error=str(e),
            )

    def _build_csi_preview_pipeline(
        self, camera_id: int, device_path: str, port: int, fps: int = 10
    ) -> str:
        """Build pipeline for CSI camera preview using rpicam-vid.

        Uses rpicam-vid which properly handles libcamera integration,
        then pipes MJPEG output to a GStreamer pipeline for TCP serving.

        Args:
            camera_id: Camera ID
            device_path: Device path (not used for CSI, libcamera auto-detects)
            port: HTTP port
            fps: Framerate (1-30)

        Returns:
            Shell command to start the preview pipeline
        """
        # Use rpicam-vid for CSI cameras - it handles libcamera properly
        # Output MJPEG to stdout, pipe to GStreamer for TCP serving
        # The -n flag disables preview window, -t 0 runs indefinitely
        return (
            f"rpicam-vid -n -t 0 --width 640 --height 480 --framerate {fps} "
            f"--codec mjpeg -o - 2>/dev/null | "
            f"gst-launch-1.0 -v fdsrc ! jpegparse ! "
            f"multipartmux boundary=--frame ! "
            f"tcpserversink host=0.0.0.0 port={port}"
        )

    def _build_usb_preview_pipeline(
        self, camera_id: int, device_path: str, port: int, fps: int = 10
    ) -> str:
        """Build GStreamer pipeline for USB camera preview.

        Args:
            camera_id: Camera ID
            device_path: Device path
            port: HTTP port
            fps: Framerate (1-30)

        Returns:
            GStreamer pipeline command
        """
        # USB camera using v4l2src
        # Most USB cameras support YUYV - convert to JPEG for streaming
        # Use 640x480 resolution, apply framerate control via videorate
        return (
            f"gst-launch-1.0 -v "
            f"v4l2src device={device_path} ! "
            f"video/x-raw,format=YUY2,width=640,height=480 ! "
            f"videorate ! video/x-raw,framerate={fps}/1 ! "
            f"videoconvert ! "
            f"jpegenc quality=50 ! "
            f"multipartmux boundary=--frame ! "
            f"tcpserversink host=0.0.0.0 port={port}"
        )


# Global preview service instance
preview_service = PreviewService()

"""Camera device path resolution service.

Resolves stable hardware_id to current device_path at runtime.
USB camera device paths (/dev/videoN) can change between reboots,
but the by-path symlinks remain stable based on physical USB port.
"""

import asyncio
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


class CameraResolver:
    """Resolves hardware identifiers to current device paths."""

    @staticmethod
    async def resolve_hardware_id(hardware_id: str) -> str | None:
        """Resolve a hardware_id to its current device path.

        Args:
            hardware_id: Stable identifier (by-path name for USB, libcamera:N for CSI)

        Returns:
            Current device path or None if camera not available
        """
        if not hardware_id:
            return None

        if hardware_id.startswith("libcamera:"):
            # CSI cameras - verify libcamera can see it
            return await CameraResolver._resolve_csi(hardware_id)
        else:
            # USB cameras - resolve by-path symlink
            return await CameraResolver._resolve_usb_by_path(hardware_id)

    @staticmethod
    async def _resolve_csi(hardware_id: str) -> str | None:
        """Resolve CSI camera hardware_id.

        For CSI cameras, hardware_id IS the device path (libcamera:N).
        We verify the camera is still available by checking rpicam-hello output.
        """
        try:
            # Try rpicam-hello first, then libcamera-hello
            for cmd in ["rpicam-hello", "libcamera-hello"]:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        cmd,
                        "--list-cameras",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
                    output = stdout.decode() if stdout else ""

                    # Check if our camera index is in the output
                    camera_index = hardware_id.split(":")[1]
                    if f"{camera_index} :" in output or f" {camera_index}:" in output:
                        return hardware_id
                except FileNotFoundError:
                    continue

            logger.debug("csi_camera_not_found", hardware_id=hardware_id)
            return None

        except asyncio.TimeoutError:
            logger.warning("csi_resolution_timeout", hardware_id=hardware_id)
            return None
        except Exception as e:
            logger.warning("csi_resolution_failed", hardware_id=hardware_id, error=str(e))
            return None

    @staticmethod
    async def _resolve_usb_by_path(hardware_id: str) -> str | None:
        """Resolve USB camera by-path identifier to current device.

        The hardware_id is the name of a symlink in /dev/v4l/by-path/
        that points to the current /dev/videoN device.
        """
        by_path = Path("/dev/v4l/by-path") / hardware_id

        if not by_path.exists():
            logger.debug("usb_by_path_not_found", hardware_id=hardware_id, path=str(by_path))
            return None

        if not by_path.is_symlink():
            logger.warning("usb_by_path_not_symlink", hardware_id=hardware_id)
            return None

        try:
            # Resolve symlink to get /dev/videoN
            device_path = str(by_path.resolve())

            # Verify device is accessible
            if not Path(device_path).exists():
                logger.debug("usb_device_not_accessible", hardware_id=hardware_id, device_path=device_path)
                return None

            logger.debug("usb_hardware_id_resolved", hardware_id=hardware_id, device_path=device_path)
            return device_path

        except Exception as e:
            logger.warning("usb_resolution_failed", hardware_id=hardware_id, error=str(e))
            return None

    @staticmethod
    async def resolve_all_cameras(cameras: list) -> dict[int, str | None]:
        """Resolve hardware_ids for multiple cameras in parallel.

        Args:
            cameras: List of camera objects with id and hardware_id attributes

        Returns:
            Dict mapping camera_id to resolved device_path (or None if unavailable)
        """
        async def resolve_one(camera):
            if camera.hardware_id:
                return camera.id, await CameraResolver.resolve_hardware_id(camera.hardware_id)
            return camera.id, None

        results = await asyncio.gather(*[resolve_one(c) for c in cameras])
        return dict(results)


async def resolve_hardware_id(hardware_id: str) -> str | None:
    """Convenience function to resolve a hardware_id."""
    return await CameraResolver.resolve_hardware_id(hardware_id)

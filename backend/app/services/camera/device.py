"""Shared device utilities for camera operations."""

import asyncio

from app.core.logging import get_logger

logger = get_logger(__name__)


async def wait_for_device_release(
    device_path: str,
    camera_id: int,
    camera_type: str,
    operation: str = "capture",
) -> bool:
    """Wait for camera device to be released after stopping a process.

    For USB cameras, uses fuser to verify the device is no longer in use.
    For CSI cameras, uses a fixed delay since libcamera manages access.

    Args:
        device_path: Path to the camera device (e.g., /dev/video2)
        camera_id: Camera database ID for logging
        camera_type: Camera type ('csi' or 'usb')
        operation: Description of the operation requiring device access

    Returns:
        True if device was released, False if still busy after timeout
    """
    if camera_type == "usb":
        return await _wait_for_usb_device_release(device_path, camera_id, operation)
    else:
        # CSI: libcamera needs ~1s to release pipeline
        await asyncio.sleep(1.0)
        logger.info(
            f"{operation}_csi_device_released",
            camera_id=camera_id,
        )
        return True


async def _wait_for_usb_device_release(
    device_path: str,
    camera_id: int,
    operation: str,
) -> bool:
    """Wait for USB device to be released by checking fuser.

    Args:
        device_path: Path to the camera device
        camera_id: Camera database ID for logging
        operation: Description of the operation

    Returns:
        True if device was released, False if still busy after timeout
    """
    max_attempts = 10  # 10 attempts × 0.5s = 5 seconds max
    for attempt in range(max_attempts):
        await asyncio.sleep(0.5)
        try:
            proc = await asyncio.create_subprocess_exec(
                "fuser", device_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2.0)
            if not stdout.decode().strip():
                logger.info(
                    f"{operation}_device_released",
                    camera_id=camera_id,
                    device_path=device_path,
                    attempts=attempt + 1,
                )
                return True
        except asyncio.TimeoutError:
            logger.debug(
                f"{operation}_device_check_timeout",
                camera_id=camera_id,
                attempt=attempt + 1,
            )
        except Exception as e:
            logger.warning(
                f"{operation}_device_check_failed",
                camera_id=camera_id,
                error=str(e),
            )

    logger.warning(
        f"{operation}_device_still_busy",
        camera_id=camera_id,
        device_path=device_path,
        message="Proceeding anyway after 5s wait",
    )
    return False

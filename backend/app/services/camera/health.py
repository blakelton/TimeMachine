"""Camera health checking service.

Provides camera health diagnostics and hardware-level checks for both
CSI and USB cameras. Extracted from the cameras route to reduce complexity.
"""

import asyncio
import os
import subprocess
from dataclasses import dataclass
from typing import Protocol

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a camera health check."""

    healthy: bool
    device_exists: bool
    device_accessible: bool
    error: str | None
    details: dict


class CameraHealthChecker(Protocol):
    """Protocol for camera-specific health checkers."""

    async def check(self, device_path: str) -> tuple[str | None, dict]:
        """Check camera health.

        Args:
            device_path: Path to camera device

        Returns:
            Tuple of (error_message, details_dict)
        """
        ...


class CSIHealthChecker:
    """Health checker for CSI cameras using rpicam-hello and dmesg."""

    async def check(self, device_path: str) -> tuple[str | None, dict]:
        """Check CSI camera using rpicam-hello and dmesg.

        Args:
            device_path: Path to camera device (not used for CSI)

        Returns:
            Tuple of (error_message, details_dict)
        """
        details: dict = {}
        error: str | None = None

        # Check rpicam availability and camera detection
        error, rpicam_details = await self._check_rpicam()
        details.update(rpicam_details)

        # Check for I2C errors even if rpicam check passed
        if not error:
            i2c_error, i2c_details = await self._check_i2c_errors()
            details.update(i2c_details)
            if i2c_error:
                error = i2c_error

        return error, details

    async def _check_rpicam(self) -> tuple[str | None, dict]:
        """Check rpicam-hello availability and camera detection.

        Returns:
            Tuple of (error_message, details_dict)
        """
        details: dict = {}
        error: str | None = None

        try:
            # Run rpicam-hello in a thread to avoid blocking
            result = await asyncio.to_thread(
                subprocess.run,
                ["rpicam-hello", "--list-cameras"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            details["rpicam_available"] = result.returncode == 0

            if result.returncode == 0:
                # Parse output to check if camera is listed
                stdout_lower = result.stdout.lower()
                if "ov5647" in stdout_lower or "imx" in stdout_lower:
                    details["csi_camera_detected"] = True
                else:
                    details["csi_camera_detected"] = False
                    error = "CSI camera not detected by libcamera"
            else:
                error = f"rpicam-hello failed: {result.stderr[:200]}"

        except subprocess.TimeoutExpired:
            error = "Camera check timed out - camera may be hung"
            details["timeout"] = True
        except FileNotFoundError:
            details["rpicam_available"] = False
            error = "rpicam-hello not installed"
        except Exception as e:
            error = f"Health check failed: {str(e)}"

        return error, details

    async def _check_i2c_errors(self) -> tuple[str | None, dict]:
        """Check dmesg for I2C communication errors.

        Returns:
            Tuple of (error_message, details_dict)
        """
        details: dict = {}
        error: str | None = None

        try:
            # Run dmesg in a thread to avoid blocking
            dmesg_result = await asyncio.to_thread(
                subprocess.run,
                ["dmesg"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if dmesg_result.returncode == 0:
                # Check last 100 lines for I2C errors
                recent_lines = dmesg_result.stdout.split("\n")[-100:]
                i2c_errors = [
                    line
                    for line in recent_lines
                    if "i2c" in line.lower()
                    and ("error" in line.lower() or "-110" in line)
                ]

                if i2c_errors:
                    details["i2c_errors_detected"] = True
                    details["i2c_error_sample"] = (
                        i2c_errors[-1][:200] if i2c_errors else None
                    )
                    error = "I2C communication errors detected - check CSI cable connection"

        except subprocess.TimeoutExpired:
            logger.warning("dmesg check timed out")
        except FileNotFoundError:
            logger.warning("dmesg command not found")
        except Exception as e:
            logger.warning("dmesg check failed", error=str(e))

        return error, details


class USBHealthChecker:
    """Health checker for USB cameras using v4l2-ctl."""

    async def check(self, device_path: str) -> tuple[str | None, dict]:
        """Check USB camera using v4l2-ctl.

        Args:
            device_path: Path to camera device

        Returns:
            Tuple of (error_message, details_dict)
        """
        details: dict = {}
        error: str | None = None

        try:
            # Run v4l2-ctl in a thread to avoid blocking
            result = await asyncio.to_thread(
                subprocess.run,
                ["v4l2-ctl", "-d", device_path, "--all"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                details["v4l2_accessible"] = True

                # Extract driver info from output
                for line in result.stdout.split("\n"):
                    if "Driver name" in line:
                        details["driver"] = line.split(":")[-1].strip()
                    elif "Card type" in line:
                        details["card_type"] = line.split(":")[-1].strip()
            else:
                details["v4l2_accessible"] = False
                error = f"v4l2-ctl failed: {result.stderr[:100]}"

        except subprocess.TimeoutExpired:
            error = "v4l2-ctl timed out - device may be busy"
        except FileNotFoundError:
            details["v4l2_available"] = False
        except Exception as e:
            error = f"USB camera check failed: {str(e)}"

        return error, details


async def check_device_exists(device_path: str) -> tuple[bool, dict]:
    """Check if device path exists.

    Args:
        device_path: Path to device

    Returns:
        Tuple of (exists, details_dict)
    """
    exists = os.path.exists(device_path)
    return exists, {"device_exists": exists}


async def check_device_accessible(device_path: str) -> tuple[bool, dict]:
    """Check if device is readable.

    Args:
        device_path: Path to device

    Returns:
        Tuple of (accessible, details_dict)
    """
    details: dict = {}
    accessible = False

    try:
        accessible = os.access(device_path, os.R_OK)
        details["device_readable"] = accessible
    except Exception as e:
        details["access_error"] = str(e)

    return accessible, details


def get_health_checker(camera_type: str) -> CameraHealthChecker:
    """Factory function to get appropriate health checker.

    Args:
        camera_type: Type of camera ("csi" or "usb")

    Returns:
        Health checker instance
    """
    checkers = {
        "csi": CSIHealthChecker(),
        "usb": USBHealthChecker(),
    }
    return checkers.get(camera_type, USBHealthChecker())


async def check_camera_health(
    device_path: str,
    camera_type: str,
) -> HealthCheckResult:
    """Check camera health and accessibility.

    This is the main entry point for health checks. Performs hardware-level
    checks to detect issues like missing device files, I2C communication
    failures (CSI cameras), permission issues, and hardware disconnection.

    Args:
        device_path: Path to camera device
        camera_type: Type of camera ("csi" or "usb")

    Returns:
        HealthCheckResult with status and diagnostic details
    """
    details: dict = {}

    # Check device existence
    device_exists, exist_details = await check_device_exists(device_path)
    details.update(exist_details)

    # Check device accessibility if it exists
    device_accessible = False
    if device_exists:
        device_accessible, access_details = await check_device_accessible(device_path)
        details.update(access_details)

    # Run camera-type-specific checks
    error: str | None = None
    if device_exists and device_accessible:
        checker = get_health_checker(camera_type)
        error, type_details = await checker.check(device_path)
        details.update(type_details)
    elif not device_exists:
        error = f"Device {device_path} does not exist"
    elif not device_accessible:
        error = f"Device {device_path} is not accessible"

    # Determine overall health
    healthy = device_exists and device_accessible and error is None

    return HealthCheckResult(
        healthy=healthy,
        device_exists=device_exists,
        device_accessible=device_accessible,
        error=error,
        details=details,
    )

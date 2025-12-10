"""Camera discovery service for CSI and USB cameras."""

import asyncio
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CameraInfo:
    """Detected camera information."""

    device_path: str
    camera_type: str  # "csi" or "usb"
    name: str
    capabilities: dict | None = None


class CameraDiscovery:
    """Service for discovering available cameras on the system."""

    @staticmethod
    async def discover_csi_cameras() -> list[CameraInfo]:
        """Discover CSI cameras using libcamera.

        Returns:
            List of detected CSI cameras.
        """
        cameras = []

        try:
            # Run libcamera-hello to list cameras
            proc = await asyncio.create_subprocess_exec(
                "libcamera-hello",
                "--list-cameras",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            output = stdout.decode() if stdout else stderr.decode()

            # Parse output for camera info
            # Example: "0 : imx219 [3280x2464] (/base/soc/i2c0mux/i2c@1/imx219@10)"
            camera_pattern = re.compile(r"(\d+)\s*:\s*(\w+)")

            for match in camera_pattern.finditer(output):
                camera_id = match.group(1)
                sensor_name = match.group(2)
                device_path = f"/dev/video{camera_id}"

                # Make name specific: include sensor model and device path
                camera = CameraInfo(
                    device_path=device_path,
                    camera_type="csi",
                    name=f"CSI {sensor_name.upper()} - {device_path}",
                    capabilities={"sensor": sensor_name},
                )
                cameras.append(camera)
                logger.info(
                    "csi_camera_discovered",
                    device=camera.device_path,
                    sensor=sensor_name,
                )

        except FileNotFoundError:
            logger.warning("libcamera_not_found", message="libcamera-hello not installed")
        except asyncio.TimeoutError:
            logger.warning("libcamera_timeout", message="libcamera-hello timed out")
        except Exception as e:
            logger.error("csi_discovery_error", error=str(e))

        return cameras

    @staticmethod
    async def discover_usb_cameras() -> list[CameraInfo]:
        """Discover USB cameras using V4L2.

        Returns:
            List of detected USB cameras.
        """
        cameras = []

        try:
            # List all video devices
            video_devices = list(Path("/dev").glob("video*"))

            for device_path in video_devices:
                device_str = str(device_path)

                # Skip devices that are part of CSI camera (usually video10+)
                device_num = int(re.search(r"\d+", device_str).group())
                if device_num >= 10:
                    continue

                # Use v4l2-ctl to get camera info
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "v4l2-ctl",
                        "--device",
                        device_str,
                        "--info",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )

                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(), timeout=3.0
                    )
                    output = stdout.decode() if stdout else ""

                    # Extract camera name from output
                    # Example: "Card type      : HD Pro Webcam C920"
                    card_match = re.search(
                        r"Card type\s*:\s*(.+)", output, re.IGNORECASE
                    )
                    card_name = (
                        card_match.group(1).strip() if card_match else "Unknown USB Camera"
                    )

                    # Get capabilities
                    capabilities = await CameraDiscovery._get_v4l2_capabilities(
                        device_str
                    )

                    # Make name specific: include model and device path
                    camera = CameraInfo(
                        device_path=device_str,
                        camera_type="usb",
                        name=f"USB {card_name} - {device_str}",
                        capabilities=capabilities,
                    )
                    cameras.append(camera)
                    logger.info(
                        "usb_camera_discovered", device=device_str, name=card_name
                    )

                except FileNotFoundError:
                    logger.warning("v4l2_not_found", message="v4l2-ctl not installed")
                    break
                except asyncio.TimeoutError:
                    logger.warning("v4l2_timeout", device=device_str)
                except Exception as e:
                    logger.debug(
                        "usb_device_check_failed", device=device_str, error=str(e)
                    )

        except Exception as e:
            logger.error("usb_discovery_error", error=str(e))

        return cameras

    @staticmethod
    async def _get_v4l2_capabilities(device_path: str) -> dict:
        """Get camera capabilities using v4l2-ctl.

        Args:
            device_path: Path to video device.

        Returns:
            Dictionary of capabilities.
        """
        capabilities = {}

        try:
            # Get supported formats
            proc = await asyncio.create_subprocess_exec(
                "v4l2-ctl",
                "--device",
                device_path,
                "--list-formats-ext",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
            output = stdout.decode() if stdout else ""

            # Parse resolutions
            resolutions = set()
            res_pattern = re.compile(r"Size:\s*Discrete\s+(\d+)x(\d+)")

            for match in res_pattern.finditer(output):
                width, height = match.groups()
                resolutions.add(f"{width}x{height}")

            if resolutions:
                capabilities["resolutions"] = sorted(resolutions, reverse=True)

            # Parse frame rates
            fps_pattern = re.compile(r"\((\d+\.\d+)\s*fps\)")
            fps_values = {float(m.group(1)) for m in fps_pattern.finditer(output)}

            if fps_values:
                capabilities["max_fps"] = int(max(fps_values))

        except Exception as e:
            logger.debug("capabilities_check_failed", device=device_path, error=str(e))

        return capabilities

    @staticmethod
    async def discover_all() -> list[CameraInfo]:
        """Discover all available cameras (CSI and USB).

        Returns:
            List of all detected cameras.
        """
        # Run both discoveries in parallel
        csi_cameras, usb_cameras = await asyncio.gather(
            CameraDiscovery.discover_csi_cameras(),
            CameraDiscovery.discover_usb_cameras(),
            return_exceptions=True,
        )

        all_cameras = []

        if isinstance(csi_cameras, list):
            all_cameras.extend(csi_cameras)
        else:
            logger.error("csi_discovery_failed", error=str(csi_cameras))

        if isinstance(usb_cameras, list):
            all_cameras.extend(usb_cameras)
        else:
            logger.error("usb_discovery_failed", error=str(usb_cameras))

        logger.info("camera_discovery_complete", total_found=len(all_cameras))
        return all_cameras


async def discover_cameras() -> list[CameraInfo]:
    """Convenience function to discover all cameras.

    Returns:
        List of detected cameras.
    """
    return await CameraDiscovery.discover_all()

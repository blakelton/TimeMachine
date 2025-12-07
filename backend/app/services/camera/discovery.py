"""Camera discovery service for CSI and USB cameras."""

import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CameraCapabilities:
    """Camera capabilities information."""

    resolutions: list[str]
    formats: list[str]
    framerates: list[int]


@dataclass
class CameraInfo:
    """Discovered camera information."""

    name: str
    device_path: str
    camera_type: str  # "csi" or "usb"
    capabilities: CameraCapabilities | None = None


class CameraDiscovery:
    """Service for discovering CSI and USB cameras."""

    @staticmethod
    async def discover_all() -> list[CameraInfo]:
        """Discover all available cameras (CSI and USB).

        Returns:
            List of discovered cameras
        """
        cameras: list[CameraInfo] = []

        # Discover CSI cameras
        csi_cameras = await CameraDiscovery._discover_csi()
        cameras.extend(csi_cameras)

        # Discover USB cameras
        usb_cameras = await CameraDiscovery._discover_usb()
        cameras.extend(usb_cameras)

        logger.info(
            "camera_discovery_complete",
            total=len(cameras),
            csi_count=len(csi_cameras),
            usb_count=len(usb_cameras),
        )

        return cameras

    @staticmethod
    async def _discover_csi() -> list[CameraInfo]:
        """Discover CSI cameras using libcamera.

        Returns:
            List of CSI cameras
        """
        cameras: list[CameraInfo] = []

        try:
            # Try to detect CSI camera using libcamera-hello
            # This will succeed if a CSI camera is connected
            proc = await asyncio.create_subprocess_exec(
                "libcamera-hello",
                "--list-cameras",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode == 0 and stdout:
                output = stdout.decode()

                # Parse libcamera output to extract camera info
                # Example output: "0 : imx219 [3280x2464] (/base/soc/i2c0mux/i2c@1/imx219@10)"
                for line in output.split("\n"):
                    if ":" in line and "[" in line:
                        # Extract camera index and name
                        parts = line.split(":")
                        if len(parts) >= 2:
                            camera_name = parts[1].split("[")[0].strip()
                            camera_index = parts[0].strip()

                            # CSI cameras use index-based paths
                            device_path = f"/dev/video{camera_index}"

                            capabilities = await CameraDiscovery._get_csi_capabilities()

                            cameras.append(
                                CameraInfo(
                                    name=f"CSI Camera ({camera_name})",
                                    device_path=device_path,
                                    camera_type="csi",
                                    capabilities=capabilities,
                                )
                            )

            logger.info("csi_discovery_complete", count=len(cameras))

        except FileNotFoundError:
            logger.warning(
                "libcamera_not_found",
                message="libcamera-hello not found, CSI camera detection disabled",
            )
        except Exception as e:
            logger.error("csi_discovery_error", error=str(e))

        return cameras

    @staticmethod
    async def _discover_usb() -> list[CameraInfo]:
        """Discover USB UVC cameras using V4L2.

        Returns:
            List of USB cameras
        """
        cameras: list[CameraInfo] = []

        try:
            # Find all video devices
            video_devices = list(Path("/dev").glob("video*"))

            for device_path in video_devices:
                # Skip virtual devices (usually even-numbered devices)
                # Real cameras are typically odd-numbered
                device_num = device_path.name.replace("video", "")
                if device_num.isdigit() and int(device_num) % 2 == 0:
                    continue

                # Check if it's a real camera by querying capabilities
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "v4l2-ctl",
                        "--device",
                        str(device_path),
                        "--info",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )

                    stdout, stderr = await proc.communicate()

                    if proc.returncode == 0 and stdout:
                        output = stdout.decode()

                        # Extract camera name from card info
                        camera_name = "USB Camera"
                        for line in output.split("\n"):
                            if "Card type" in line or "card" in line.lower():
                                parts = line.split(":")
                                if len(parts) >= 2:
                                    camera_name = parts[1].strip()
                                break

                        # Get capabilities for this camera
                        capabilities = await CameraDiscovery._get_usb_capabilities(
                            str(device_path)
                        )

                        cameras.append(
                            CameraInfo(
                                name=camera_name,
                                device_path=str(device_path),
                                camera_type="usb",
                                capabilities=capabilities,
                            )
                        )

                        logger.debug(
                            "usb_camera_found",
                            device=str(device_path),
                            name=camera_name,
                        )

                except FileNotFoundError:
                    logger.warning(
                        "v4l2_not_found",
                        message="v4l2-ctl not found, USB camera capabilities detection disabled",
                    )
                    break
                except Exception as e:
                    logger.debug(
                        "device_check_failed", device=str(device_path), error=str(e)
                    )
                    continue

            logger.info("usb_discovery_complete", count=len(cameras))

        except Exception as e:
            logger.error("usb_discovery_error", error=str(e))

        return cameras

    @staticmethod
    async def _get_csi_capabilities() -> CameraCapabilities | None:
        """Get CSI camera capabilities using libcamera.

        Returns:
            Camera capabilities or None
        """
        try:
            # Common CSI camera capabilities (e.g., IMX219, OV5647)
            # In production, parse libcamera output for actual capabilities
            return CameraCapabilities(
                resolutions=["1920x1080", "1280x720", "640x480"],
                formats=["H264", "MJPEG", "YUV420"],
                framerates=[30, 25, 15, 10, 5],
            )
        except Exception as e:
            logger.error("csi_capabilities_error", error=str(e))
            return None

    @staticmethod
    async def _get_usb_capabilities(device_path: str) -> CameraCapabilities | None:
        """Get USB camera capabilities using V4L2.

        Args:
            device_path: Path to video device

        Returns:
            Camera capabilities or None
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "v4l2-ctl",
                "--device",
                device_path,
                "--list-formats-ext",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode != 0 or not stdout:
                return None

            output = stdout.decode()

            # Parse formats and resolutions
            formats: set[str] = set()
            resolutions: set[str] = set()
            framerates: set[int] = set()

            current_format = None
            for line in output.split("\n"):
                line = line.strip()

                # Format line: [0]: 'MJPG' (Motion-JPEG, compressed)
                if line.startswith("[") and "]:" in line:
                    parts = line.split("'")
                    if len(parts) >= 2:
                        current_format = parts[1]
                        formats.add(current_format)

                # Size line: Size: Discrete 1920x1080
                if "Size:" in line and "Discrete" in line:
                    parts = line.split()
                    for part in parts:
                        if "x" in part and part.replace("x", "").replace("0", "").replace("1", "").replace("2", "").replace("3", "").replace("4", "").replace("5", "").replace("6", "").replace("7", "").replace("8", "").replace("9", "") == "":
                            resolutions.add(part)

                # Framerate line: Interval: Discrete 0.033s (30.000 fps)
                if "fps)" in line:
                    parts = line.split("(")
                    if len(parts) >= 2:
                        fps_part = parts[1].split()[0]
                        try:
                            fps = int(float(fps_part))
                            framerates.add(fps)
                        except ValueError:
                            pass

            return CameraCapabilities(
                resolutions=sorted(list(resolutions), reverse=True),
                formats=sorted(list(formats)),
                framerates=sorted(list(framerates), reverse=True),
            )

        except Exception as e:
            logger.error(
                "usb_capabilities_error", device=device_path, error=str(e)
            )
            return None

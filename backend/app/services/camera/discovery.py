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
        """Discover CSI cameras using libcamera or v4l2 fallback.

        Returns:
            List of detected CSI cameras.
        """
        cameras = []

        try:
            # Try libcamera-hello first
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
            logger.info("libcamera_not_found", message="Trying v4l2 fallback for CSI detection")
            # Fallback: detect CSI camera via v4l2 unicam driver
            cameras = await CameraDiscovery._discover_csi_via_v4l2()
        except asyncio.TimeoutError:
            logger.warning("libcamera_timeout", message="libcamera-hello timed out")
        except Exception as e:
            logger.error("csi_discovery_error", error=str(e))

        return cameras

    @staticmethod
    async def _discover_csi_via_v4l2() -> list[CameraInfo]:
        """Fallback method to discover CSI cameras via v4l2 unicam driver.

        Returns:
            List of detected CSI cameras.
        """
        cameras = []
        video_devices = list(Path("/dev").glob("video*"))

        for device_path in video_devices:
            device_str = str(device_path)
            device_num = int(re.search(r"\d+", device_str).group())

            # Only check devices 0-9
            if device_num >= 10:
                continue

            try:
                proc = await asyncio.create_subprocess_exec(
                    "v4l2-ctl",
                    "--device",
                    device_str,
                    "--info",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
                output = stdout.decode() if stdout else ""

                # Check for unicam driver (CSI camera)
                # Note: Use non-greedy match and stop at newline
                driver_match = re.search(r"Driver name\s*:\s*(.+?)(?:\n|$)", output, re.IGNORECASE)
                driver_name = driver_match.group(1).strip() if driver_match else ""

                if driver_name == "unicam":
                    # Extract card type for sensor name
                    card_match = re.search(r"Card type\s*:\s*(.+?)(?:\n|$)", output, re.IGNORECASE)
                    card_name = card_match.group(1).strip() if card_match else "CSI Camera"

                    camera = CameraInfo(
                        device_path=device_str,
                        camera_type="csi",
                        name=f"CSI {card_name.upper()} - {device_str}",
                        capabilities={"driver": driver_name},
                    )
                    cameras.append(camera)
                    logger.info(
                        "csi_camera_discovered_v4l2",
                        device=device_str,
                        driver=driver_name,
                    )

            except Exception as e:
                logger.debug("csi_v4l2_check_failed", device=device_str, error=str(e))

        return cameras

    @staticmethod
    async def discover_usb_cameras() -> list[CameraInfo]:
        """Discover USB cameras using V4L2.

        Returns:
            List of detected USB cameras (deduplicated by card name).
        """
        cameras = []
        seen_cameras = set()  # Track camera names to deduplicate multiple video nodes

        try:
            # List all video devices
            video_devices = list(Path("/dev").glob("video*"))

            logger.info(
                "usb_discovery_scan_starting",
                total_devices=len(video_devices),
                devices=[str(d) for d in video_devices],
            )

            for device_path in video_devices:
                device_str = str(device_path)

                # Skip devices >= 10 (codec/ISP devices)
                device_num = int(re.search(r"\d+", device_str).group())
                if device_num >= 10:
                    logger.debug("usb_device_skipped_high_number", device=device_str, device_num=device_num)
                    continue

                logger.debug("usb_device_checking", device=device_str, device_num=device_num)

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

                    if not output:
                        logger.warning(
                            "usb_device_no_output",
                            device=device_str,
                            stderr=stderr.decode() if stderr else "",
                            returncode=proc.returncode,
                        )
                        continue

                    # Extract driver name to identify camera type
                    # Note: Use non-greedy match and stop at newline to avoid capturing extra whitespace
                    driver_match = re.search(
                        r"Driver name\s*:\s*(.+?)(?:\n|$)", output, re.IGNORECASE
                    )
                    driver_name = driver_match.group(1).strip() if driver_match else ""

                    # Skip non-USB cameras (unicam is CSI, bcm2835 is codec/ISP)
                    if driver_name in ["unicam", "bcm2835-codec", "bcm2835-isp"]:
                        logger.debug("usb_device_skipped_non_usb", device=device_str, driver=driver_name)
                        continue

                    # Only process uvcvideo (USB cameras)
                    if driver_name != "uvcvideo":
                        logger.debug("usb_device_skipped_not_uvcvideo", device=device_str, driver=driver_name)
                        continue

                    # Check if device has actual video capture formats
                    # USB cameras create multiple video nodes - metadata nodes have no formats
                    has_formats = await CameraDiscovery._device_has_capture_formats(device_str)
                    if not has_formats:
                        logger.debug(
                            "usb_device_skipped_no_formats",
                            device=device_str,
                            message="Device has no capture formats (metadata-only node)",
                        )
                        continue

                    # Extract camera name from output
                    # Note: Use non-greedy match and stop at newline
                    card_match = re.search(
                        r"Card type\s*:\s*(.+?)(?:\n|$)", output, re.IGNORECASE
                    )
                    card_name = (
                        card_match.group(1).strip() if card_match else "Unknown USB Camera"
                    )

                    # Extract bus info to distinguish physical cameras with same model
                    # Bus info example: "usb-3f980000.usb-1.3.1" (unique per USB port)
                    bus_match = re.search(
                        r"Bus info\s*:\s*(.+?)(?:\n|$)", output, re.IGNORECASE
                    )
                    bus_info = bus_match.group(1).strip() if bus_match else ""

                    # Deduplicate: USB cameras often create multiple video nodes
                    # Use bus_info to distinguish between physical cameras with same model
                    # Only add the first video node per unique physical camera (bus_info)
                    if bus_info and bus_info in seen_cameras:
                        logger.debug(
                            "usb_camera_duplicate_skipped",
                            device=device_str,
                            name=card_name,
                            bus_info=bus_info,
                            message="Skipping duplicate video node for same physical camera",
                        )
                        continue

                    if bus_info:
                        seen_cameras.add(bus_info)

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
                    logger.error("v4l2_not_found", message="v4l2-ctl command not found")
                    break
                except asyncio.TimeoutError:
                    logger.warning("v4l2_timeout", device=device_str, message="v4l2-ctl timed out after 3 seconds")
                except Exception as e:
                    logger.warning(
                        "usb_device_check_failed",
                        device=device_str,
                        error=str(e),
                        error_type=type(e).__name__,
                    )

        except Exception as e:
            logger.error("usb_discovery_error", error=str(e), error_type=type(e).__name__)

        logger.info("usb_discovery_complete", cameras_found=len(cameras))
        return cameras

    @staticmethod
    async def _device_has_capture_formats(device_path: str) -> bool:
        """Check if a device has actual video capture formats.

        USB cameras create multiple video nodes. The main capture node has formats
        like YUYV, MJPG, etc. Metadata-only nodes have no formats listed.

        Args:
            device_path: Path to video device.

        Returns:
            True if device has capture formats, False otherwise.
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "v4l2-ctl",
                "--device",
                device_path,
                "--list-formats",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
            output = stdout.decode() if stdout else ""

            # Look for format entries like "[0]: 'YUYV'" or "[0]: 'MJPG'"
            format_pattern = re.compile(r"\[\d+\]:\s*'[A-Z0-9]+'")
            has_formats = bool(format_pattern.search(output))

            logger.debug(
                "device_format_check",
                device=device_path,
                has_formats=has_formats,
                output_preview=output[:200] if output else "empty",
            )

            return has_formats

        except Exception as e:
            logger.debug("format_check_failed", device=device_path, error=str(e))
            return False

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

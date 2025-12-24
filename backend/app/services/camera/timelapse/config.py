"""Timelapse configuration models."""


class TimelapseConfig:
    """Configuration for a timelapse capture session."""

    def __init__(
        self,
        camera_id: int,
        interval_seconds: int = 60,
        total_frames: int | None = None,
        duration_hours: float | None = None,
        quality: int = 95,
        resolution: tuple[int, int] = (1920, 1080),
        output_fps: int = 30,
        env_overlay_device_id: int | None = None,
        env_overlay_position: str = "br",
        env_overlay_show_graph: bool = False,
        env_overlay_device_type: str | None = None,
        env_overlay_temp_unit: str = "C",
    ):
        """Initialize timelapse configuration.

        Args:
            camera_id: Camera ID
            interval_seconds: Seconds between captures (default 60)
            total_frames: Total frames to capture (optional)
            duration_hours: Total duration in hours (optional)
            quality: JPEG quality 1-100 (default 95)
            resolution: Output resolution (default 1920x1080)
            output_fps: Output video FPS (default 30)
            env_overlay_device_id: Environment device ID for overlay (optional)
            env_overlay_position: Overlay position - tl, tr, bl, br (default: br)
            env_overlay_show_graph: Whether to show temperature graph
            env_overlay_device_type: Sensor type (dht22, bme280, etc.)
            env_overlay_temp_unit: Temperature unit (C or F)
        """
        self.camera_id = camera_id
        self.interval_seconds = interval_seconds
        self.quality = quality
        self.resolution = resolution
        self.output_fps = output_fps

        # Environment overlay settings
        self.env_overlay_device_id = env_overlay_device_id
        self.env_overlay_position = env_overlay_position
        self.env_overlay_show_graph = env_overlay_show_graph
        self.env_overlay_device_type = env_overlay_device_type
        self.env_overlay_temp_unit = env_overlay_temp_unit

        # Calculate total frames from duration if provided
        if total_frames:
            self.total_frames = total_frames
        elif duration_hours:
            frames_per_hour = 3600 / interval_seconds
            self.total_frames = int(duration_hours * frames_per_hour)
        else:
            self.total_frames = None  # Unlimited until stopped

    def to_dict(self) -> dict:
        """Convert config to dictionary for database storage."""
        result = {
            "interval_seconds": self.interval_seconds,
            "total_frames": self.total_frames,
            "quality": self.quality,
            "resolution": list(self.resolution),
            "output_fps": self.output_fps,
        }

        # Include overlay settings if configured
        if self.env_overlay_device_id is not None:
            result["env_overlay_device_id"] = self.env_overlay_device_id
            result["env_overlay_position"] = self.env_overlay_position
            result["env_overlay_show_graph"] = self.env_overlay_show_graph
            result["env_overlay_device_type"] = self.env_overlay_device_type
            result["env_overlay_temp_unit"] = self.env_overlay_temp_unit

        return result

    @classmethod
    def from_dict(cls, camera_id: int, data: dict) -> "TimelapseConfig":
        """Create config from dictionary."""
        return cls(
            camera_id=camera_id,
            interval_seconds=data.get("interval_seconds", 60),
            total_frames=data.get("total_frames"),
            quality=data.get("quality", 95),
            resolution=tuple(data.get("resolution", [1920, 1080])),
            output_fps=data.get("output_fps", 30),
            env_overlay_device_id=data.get("env_overlay_device_id"),
            env_overlay_position=data.get("env_overlay_position", "br"),
            env_overlay_show_graph=data.get("env_overlay_show_graph", False),
            env_overlay_device_type=data.get("env_overlay_device_type"),
            env_overlay_temp_unit=data.get("env_overlay_temp_unit", "C"),
        )

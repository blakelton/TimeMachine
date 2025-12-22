"""Camera API schemas."""

from pydantic import BaseModel, Field


class CameraCapabilities(BaseModel):
    """Camera capabilities information."""

    resolutions: list[str] = Field(
        default_factory=list, description="Supported resolutions (e.g., '1920x1080')"
    )
    formats: list[str] = Field(
        default_factory=list, description="Supported formats (e.g., 'H264', 'MJPEG')"
    )
    framerates: list[int] = Field(
        default_factory=list, description="Supported framerates (fps)"
    )


class CameraSettings(BaseModel):
    """Default camera settings."""

    resolution: str | None = Field(None, description="Default resolution")
    framerate: int | None = Field(None, description="Default framerate (fps)")
    format: str | None = Field(None, description="Default format")
    brightness: int | None = Field(None, ge=0, le=100, description="Brightness (0-100)")
    contrast: int | None = Field(None, ge=0, le=100, description="Contrast (0-100)")
    saturation: int | None = Field(
        None, ge=0, le=100, description="Saturation (0-100)"
    )


class CameraBase(BaseModel):
    """Base camera schema with common fields."""

    name: str = Field(..., min_length=1, max_length=100, description="Camera name")
    device_path: str = Field(
        ..., min_length=1, max_length=255, description="Device path (e.g., /dev/video0)"
    )
    camera_type: str = Field(..., description="Camera type: 'csi' or 'usb'")
    enabled: bool = Field(True, description="Whether camera is enabled")


class CameraCreate(CameraBase):
    """Schema for creating a camera."""

    hardware_id: str | None = Field(
        None,
        max_length=500,
        description="Stable hardware identifier (by-path for USB, libcamera:N for CSI)",
    )
    capabilities: CameraCapabilities | None = Field(
        None, description="Camera capabilities"
    )
    default_settings: CameraSettings | None = Field(
        None, description="Default camera settings"
    )


class CameraUpdate(BaseModel):
    """Schema for updating a camera (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=100)
    device_path: str | None = Field(
        None, min_length=1, max_length=255, description="Device path (e.g., /dev/video0)"
    )
    enabled: bool | None = None
    default_settings: CameraSettings | None = None


class CameraResponse(CameraBase):
    """Schema for camera response."""

    id: int = Field(..., description="Camera ID")
    hardware_id: str | None = Field(
        None, description="Stable hardware identifier for persistent camera identification"
    )
    capabilities: CameraCapabilities | None = None
    default_settings: CameraSettings | None = None

    model_config = {"from_attributes": True}


class CameraListResponse(BaseModel):
    """Schema for camera list response."""

    cameras: list[CameraResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total number of cameras")


class DiscoveredCameraResponse(BaseModel):
    """Schema for discovered camera response."""

    name: str = Field(..., description="Camera name")
    device_path: str = Field(..., description="Device path")
    camera_type: str = Field(..., description="Camera type: 'csi' or 'usb'")
    hardware_id: str | None = Field(
        None, description="Stable hardware identifier for persistent identification"
    )
    capabilities: dict | None = Field(None, description="Camera capabilities")


class CameraHealthResponse(BaseModel):
    """Schema for camera health check response."""

    camera_id: int = Field(..., description="Camera ID")
    name: str = Field(..., description="Camera name")
    device_path: str = Field(..., description="Device path")
    camera_type: str = Field(..., description="Camera type")
    healthy: bool = Field(..., description="Whether camera is healthy and accessible")
    device_exists: bool = Field(..., description="Whether device path exists")
    device_accessible: bool = Field(..., description="Whether device is accessible")
    error: str | None = Field(None, description="Error message if unhealthy")
    details: dict | None = Field(None, description="Additional diagnostic details")

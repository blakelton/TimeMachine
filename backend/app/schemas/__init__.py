"""API schemas."""

from app.schemas.camera import (
    CameraBase,
    CameraCapabilities,
    CameraCreate,
    CameraListResponse,
    CameraResponse,
    CameraSettings,
    CameraUpdate,
    DiscoveredCameraResponse,
)
from app.schemas.job import (
    JobListResponse,
    JobResponse,
    OperationResponse,
    RecordingStatusResponse,
    StartRecordingRequest,
    StartTimelapseRequest,
    StopTimelapseRequest,
    TimelapseConfigSchema,
    TimelapseStatusResponse,
)
from app.schemas.output_config import (
    OutputConfigCreate,
    OutputConfigListResponse,
    OutputConfigResponse,
    OutputConfigUpdate,
)

__all__ = [
    # Camera
    "CameraBase",
    "CameraCapabilities",
    "CameraCreate",
    "CameraListResponse",
    "CameraResponse",
    "CameraSettings",
    "CameraUpdate",
    "DiscoveredCameraResponse",
    # Job
    "JobListResponse",
    "JobResponse",
    "OperationResponse",
    "RecordingStatusResponse",
    "StartRecordingRequest",
    "StartTimelapseRequest",
    "StopTimelapseRequest",
    "TimelapseConfigSchema",
    "TimelapseStatusResponse",
    # OutputConfig
    "OutputConfigCreate",
    "OutputConfigListResponse",
    "OutputConfigResponse",
    "OutputConfigUpdate",
]

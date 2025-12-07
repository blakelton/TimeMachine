"""Camera services package."""

from app.services.camera.discovery import CameraDiscovery, discover_cameras
from app.services.camera.pipeline import ManagedPipeline, PipelineConfig, PipelineState
from app.services.camera.preview import PreviewService, preview_service
from app.services.camera.capture import CaptureService, capture_service
from app.services.camera.recording import RecordingService, recording_service
from app.services.camera.timelapse import (
    TimelapseConfig,
    TimelapseService,
    TimelapseSession,
    timelapse_service,
)

__all__ = [
    # Discovery
    "CameraDiscovery",
    "discover_cameras",
    # Pipeline
    "ManagedPipeline",
    "PipelineConfig",
    "PipelineState",
    # Services
    "PreviewService",
    "preview_service",
    "CaptureService",
    "capture_service",
    "RecordingService",
    "recording_service",
    "TimelapseConfig",
    "TimelapseService",
    "TimelapseSession",
    "timelapse_service",
]

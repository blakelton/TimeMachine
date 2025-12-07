"""Camera service modules."""

from app.services.camera.discovery import (
    CameraDiscovery,
    CameraInfo,
    CameraCapabilities,
)
from app.services.camera.pipeline import ManagedPipeline, PipelineConfig, PipelineState
from app.services.camera.preview import preview_service
from app.services.camera.capture import capture_service
from app.services.camera.recording import recording_service

__all__ = [
    "CameraDiscovery",
    "CameraInfo",
    "CameraCapabilities",
    "ManagedPipeline",
    "PipelineConfig",
    "PipelineState",
    "preview_service",
    "capture_service",
    "recording_service",
]

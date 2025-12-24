"""Timelapse capture and assembly service with Job tracking.

This package provides timelapse functionality for the camera service.
The main module has been split into focused components:
- config: TimelapseConfig class for session configuration
- session: TimelapseSession class with capture loop and recovery
- service: TimelapseService class for orchestration
- assembly: Video assembly utilities

For backward compatibility, all main classes are exported from this module.
"""

from .assembly import assemble_video, format_size
from .config import TimelapseConfig
from .service import TimelapseService
from .session import CaptureState, TimelapseSession

# Global timelapse service instance
timelapse_service = TimelapseService()

__all__ = [
    "TimelapseConfig",
    "TimelapseSession",
    "TimelapseService",
    "CaptureState",
    "timelapse_service",
    "assemble_video",
    "format_size",
]

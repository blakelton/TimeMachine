"""Timelapse capture and assembly service with Job tracking.

DEPRECATED: This module is now a package. Import from:
- app.services.camera.timelapse.config for TimelapseConfig
- app.services.camera.timelapse.session for TimelapseSession, CaptureState
- app.services.camera.timelapse.service for TimelapseService
- app.services.camera.timelapse.assembly for video assembly utilities

For backward compatibility, all exports are re-exported from this module.
"""

# Re-export everything from the package for backward compatibility
from app.services.camera.timelapse import (
    CaptureState,
    TimelapseConfig,
    TimelapseService,
    TimelapseSession,
    assemble_video,
    format_size,
    timelapse_service,
)

__all__ = [
    "TimelapseConfig",
    "TimelapseSession",
    "TimelapseService",
    "CaptureState",
    "timelapse_service",
    "assemble_video",
    "format_size",
]

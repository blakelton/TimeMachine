"""Pydantic schemas for request/response models."""

from app.models.schemas.base import (
    DiskInfo,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    MemoryInfo,
    Meta,
    ResponseWrapper,
    StatsResponse,
    ThrottleInfo,
)
from app.models.schemas.websocket import (
    WSCameraEvent,
    WSError,
    WSJobUpdate,
    WSMessage,
    WSStatsUpdate,
)

__all__ = [
    # Base schemas
    "Meta",
    "ResponseWrapper",
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "ThrottleInfo",
    "MemoryInfo",
    "DiskInfo",
    "StatsResponse",
    # WebSocket schemas
    "WSStatsUpdate",
    "WSCameraEvent",
    "WSJobUpdate",
    "WSError",
    "WSMessage",
]

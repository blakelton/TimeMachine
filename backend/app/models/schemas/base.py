"""Pydantic schemas for request/response models."""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Meta(BaseModel):
    """Response metadata."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str | None = None


class ResponseWrapper(BaseModel, Generic[T]):
    """Standard response wrapper for successful responses."""

    data: T
    meta: Meta = Field(default_factory=Meta)


class ErrorDetail(BaseModel):
    """Error response structure."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standard error response wrapper."""

    error: ErrorDetail
    meta: Meta = Field(default_factory=Meta)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    environment: str
    auth_enabled: bool


class ThrottleInfo(BaseModel):
    """Throttle status information."""

    available: bool
    raw_value: str | None = None
    is_throttled: bool = False
    active: list[str] | None = None
    historical: list[str] | None = None
    error: str | None = None


class MemoryInfo(BaseModel):
    """Memory statistics."""

    total_mb: float
    available_mb: float
    used_mb: float
    percent: float
    status: str


class DiskInfo(BaseModel):
    """Disk statistics."""

    path: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent_used: float
    is_available: bool


class StatsResponse(BaseModel):
    """System statistics response."""

    cpu_percent: float
    memory: MemoryInfo
    disk: DiskInfo
    temperature_celsius: float | None
    throttle: ThrottleInfo
    timestamp: datetime

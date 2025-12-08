"""Health and statistics endpoints."""

from fastapi import APIRouter

from app import __version__
from app.core.config import settings
from app.models.schemas import (
    DiskInfo,
    HealthResponse,
    MemoryInfo,
    Meta,
    ResponseWrapper,
    StatsResponse,
    ThrottleInfo,
)
from app.services.system.stats import get_system_stats

router = APIRouter(prefix="/health", tags=["system"])


@router.get("", response_model=ResponseWrapper[HealthResponse])
async def health_check() -> ResponseWrapper[HealthResponse]:
    """Health check endpoint.

    Returns application health status and basic info.
    This endpoint is always accessible (no auth required).
    """
    return ResponseWrapper(
        data=HealthResponse(
            status="ok",
            version=__version__,
            environment=settings.env,
            auth_enabled=settings.auth_enabled,
        ),
        meta=Meta(),
    )


@router.get("/stats", response_model=ResponseWrapper[StatsResponse])
async def get_stats() -> ResponseWrapper[StatsResponse]:
    """Get system statistics.

    Returns comprehensive system information including:
    - CPU usage
    - Memory usage with status (ok/warning/critical)
    - Disk usage
    - CPU temperature (if available)
    - Throttle status (if on Raspberry Pi)

    This endpoint is always accessible (no auth required).
    """
    stats = await get_system_stats()

    return ResponseWrapper(
        data=StatsResponse(
            cpu_percent=stats.cpu_percent,
            memory=MemoryInfo(
                total_mb=stats.memory.total_mb,
                available_mb=stats.memory.available_mb,
                used_mb=stats.memory.used_mb,
                percent=stats.memory.percent,
                status=stats.memory.status,
            ),
            disk=DiskInfo(
                path=stats.disk.path,
                total_gb=stats.disk.total_gb,
                used_gb=stats.disk.used_gb,
                free_gb=stats.disk.free_gb,
                percent_used=stats.disk.percent_used,
                is_available=stats.disk.is_available,
            ),
            temperature_celsius=stats.temperature_celsius,
            throttle=ThrottleInfo(
                available=stats.throttle.available,
                raw_value=stats.throttle.raw_value,
                is_throttled=stats.throttle.is_throttled,
                active=stats.throttle.active,
                historical=stats.throttle.historical,
                error=stats.throttle.error,
            ),
            timestamp=stats.timestamp,
        ),
        meta=Meta(),
    )

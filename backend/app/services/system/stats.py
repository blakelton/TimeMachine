"""System statistics service."""

import asyncio
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import psutil
import structlog

from app.core.config import settings
from app.services.system.throttle import ThrottleStatus, get_cpu_temperature, get_throttle_status

logger = structlog.get_logger(__name__)


@dataclass
class DiskStats:
    """Disk usage statistics."""

    path: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent_used: float
    is_available: bool


@dataclass
class MemoryStats:
    """Memory usage statistics."""

    total_mb: float
    available_mb: float
    used_mb: float
    percent: float
    status: str  # "ok", "warning", "critical"


@dataclass
class SystemStats:
    """Complete system statistics."""

    cpu_percent: float
    memory: MemoryStats
    disk: DiskStats
    temperature_celsius: float | None
    throttle: ThrottleStatus
    timestamp: datetime = field(default_factory=datetime.utcnow)


def get_memory_stats() -> MemoryStats:
    """Get memory usage statistics.

    Returns:
        MemoryStats with current memory information.
    """
    mem = psutil.virtual_memory()

    total_mb = mem.total / (1024 * 1024)
    available_mb = mem.available / (1024 * 1024)
    used_mb = mem.used / (1024 * 1024)
    percent = mem.percent

    # Determine status based on available memory
    if available_mb < settings.min_memory_mb:
        status = "critical"
    elif available_mb < settings.min_memory_mb * 2:
        status = "warning"
    else:
        status = "ok"

    return MemoryStats(
        total_mb=round(total_mb, 1),
        available_mb=round(available_mb, 1),
        used_mb=round(used_mb, 1),
        percent=round(percent, 1),
        status=status,
    )


def get_disk_stats(path: Path | None = None) -> DiskStats:
    """Get disk usage statistics.

    Args:
        path: Path to check disk usage for. Defaults to media path.

    Returns:
        DiskStats with current disk information.
    """
    check_path = path or settings.media_path

    try:
        usage = shutil.disk_usage(check_path)

        return DiskStats(
            path=str(check_path),
            total_gb=round(usage.total / (1024**3), 2),
            used_gb=round(usage.used / (1024**3), 2),
            free_gb=round(usage.free / (1024**3), 2),
            percent_used=round((usage.used / usage.total) * 100, 1),
            is_available=True,
        )
    except OSError as e:
        logger.warning("disk_stats_failed", path=str(check_path), error=str(e))
        return DiskStats(
            path=str(check_path),
            total_gb=0,
            used_gb=0,
            free_gb=0,
            percent_used=0,
            is_available=False,
        )


async def get_system_stats() -> SystemStats:
    """Get comprehensive system statistics.

    Uses asyncio to parallelize blocking operations.

    Returns:
        SystemStats with all system information.
    """
    loop = asyncio.get_event_loop()

    # Run blocking operations in executor
    cpu_percent, memory, disk, temperature, throttle = await asyncio.gather(
        loop.run_in_executor(None, lambda: psutil.cpu_percent(interval=0.1)),
        loop.run_in_executor(None, get_memory_stats),
        loop.run_in_executor(None, get_disk_stats),
        loop.run_in_executor(None, get_cpu_temperature),
        loop.run_in_executor(None, get_throttle_status),
    )

    return SystemStats(
        cpu_percent=round(cpu_percent, 1),
        memory=memory,
        disk=disk,
        temperature_celsius=temperature,
        throttle=throttle,
    )


def check_memory_available(min_mb: int | None = None) -> tuple[bool, int]:
    """Check if minimum memory is available.

    Args:
        min_mb: Minimum required memory in MB. Defaults to settings value.

    Returns:
        Tuple of (is_available: bool, available_mb: int)
    """
    required = min_mb or settings.min_memory_mb
    available = int(psutil.virtual_memory().available / (1024 * 1024))
    return available >= required, available


def check_disk_available(min_mb: int | None = None, path: Path | None = None) -> tuple[bool, int]:
    """Check if minimum disk space is available.

    Args:
        min_mb: Minimum required space in MB. Defaults to settings value.
        path: Path to check. Defaults to media path.

    Returns:
        Tuple of (is_available: bool, available_mb: int)
    """
    required = min_mb or settings.min_disk_mb
    check_path = path or settings.media_path

    try:
        usage = shutil.disk_usage(check_path)
        available = int(usage.free / (1024 * 1024))
        return available >= required, available
    except OSError:
        return False, 0

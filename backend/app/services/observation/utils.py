"""Utility functions for observation service."""

from datetime import datetime, timedelta


# Use local time for all timestamps (simpler for local appliance)
def now() -> datetime:
    """Return current local time (naive datetime)."""
    return datetime.now()


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def interval_to_seconds(value: int, unit: str) -> int:
    """Convert interval value and unit to seconds."""
    if unit == "hours":
        return value * 3600
    elif unit == "minutes":
        return value * 60
    else:
        return value


def calculate_end_datetime(
    end_mode: str,
    end_datetime: datetime | None,
    duration_value: int | None,
    duration_unit: str | None,
) -> datetime | None:
    """Calculate the end datetime from config."""
    if end_mode == "datetime" and end_datetime:
        return end_datetime
    elif end_mode == "duration" and duration_value and duration_unit:
        delta_seconds = interval_to_seconds(duration_value, duration_unit)
        return now() + timedelta(seconds=delta_seconds)
    return None


def calculate_total_frames(
    interval_seconds: int,
    end_mode: str,
    end_datetime: datetime | None,
    duration_value: int | None,
    duration_unit: str | None,
) -> int | None:
    """Calculate total frames for timelapse."""
    target_end = calculate_end_datetime(
        end_mode, end_datetime, duration_value, duration_unit
    )
    if target_end:
        duration_seconds = (target_end - now()).total_seconds()
        if duration_seconds > 0:
            return int(duration_seconds / interval_seconds)
    return None

"""WebSocket message protocol schemas."""

from datetime import datetime
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


class WSStatsUpdate(BaseModel):
    """System statistics update message."""

    type: Literal["stats_update"] = "stats_update"
    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_percent: float = Field(..., description="Memory usage percentage")
    disk_free_gb: float = Field(..., description="Free disk space in GB")
    temperature_celsius: Optional[float] = Field(
        None, description="CPU temperature in Celsius"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSCameraEvent(BaseModel):
    """Camera status event message."""

    type: Literal["camera_event"] = "camera_event"
    camera_id: int = Field(..., description="Camera database ID")
    event: Literal[
        "online", "offline", "recording_started", "recording_stopped", "error"
    ] = Field(..., description="Event type")
    message: Optional[str] = Field(None, description="Additional event message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSJobUpdate(BaseModel):
    """Job progress update message."""

    type: Literal["job_update"] = "job_update"
    job_id: int = Field(..., description="Job database ID")
    camera_id: int = Field(..., description="Camera database ID")
    job_type: str = Field(..., description="Job type (capture, record, timelapse)")
    status: Literal["pending", "running", "completed", "failed", "interrupted"] = Field(
        ..., description="Job status"
    )
    progress: Optional[float] = Field(
        None, ge=0, le=100, description="Progress percentage (0-100)"
    )
    current_frame: Optional[int] = Field(
        None, ge=0, description="Current frame count (for timelapse jobs)"
    )
    total_frames: Optional[int] = Field(
        None, ge=0, description="Total expected frames (for timelapse jobs, None=unlimited)"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSError(BaseModel):
    """Error message."""

    type: Literal["error"] = "error"
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Union type for all WebSocket messages
WSMessage = Union[WSStatsUpdate, WSCameraEvent, WSJobUpdate, WSError]

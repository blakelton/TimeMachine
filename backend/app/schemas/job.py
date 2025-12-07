"""Job API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class TimelapseConfigSchema(BaseModel):
    """Timelapse configuration schema."""

    interval_seconds: int = Field(60, ge=1, le=3600, description="Seconds between captures")
    total_frames: int | None = Field(None, ge=1, description="Total frames to capture")
    duration_hours: float | None = Field(None, ge=0.1, description="Total duration in hours")
    quality: int = Field(95, ge=1, le=100, description="JPEG quality (1-100)")
    resolution_width: int = Field(1920, ge=640, description="Output width")
    resolution_height: int = Field(1080, ge=480, description="Output height")
    output_fps: int = Field(30, ge=1, le=60, description="Output video FPS")


class StartRecordingRequest(BaseModel):
    """Request to start a recording."""

    duration_seconds: int | None = Field(None, ge=1, description="Optional duration limit")
    filename: str | None = Field(None, max_length=200, description="Optional custom filename")


class StartTimelapseRequest(BaseModel):
    """Request to start a timelapse."""

    config: TimelapseConfigSchema = Field(
        default_factory=TimelapseConfigSchema, description="Timelapse configuration"
    )


class StopTimelapseRequest(BaseModel):
    """Request to stop a timelapse."""

    assemble_video: bool = Field(True, description="Whether to assemble frames into video")


class JobResponse(BaseModel):
    """Job response schema."""

    id: int = Field(..., description="Job ID")
    camera_id: int = Field(..., description="Camera ID")
    job_type: str = Field(..., description="Job type: recording, timelapse, capture")
    status: str = Field(..., description="Job status: pending, running, completed, failed, interrupted")
    output_path: str | None = Field(None, description="Output file path")
    error_message: str | None = Field(None, description="Error message if failed")
    started_at: datetime = Field(..., description="Start timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")
    timelapse_progress: int | None = Field(None, description="Timelapse frame count")
    timelapse_config: dict | None = Field(None, description="Timelapse configuration")

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """Job list response schema."""

    jobs: list[JobResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total number of jobs")


class RecordingStatusResponse(BaseModel):
    """Recording status response."""

    camera_id: int = Field(..., description="Camera ID")
    state: str = Field(..., description="Pipeline state")
    pid: int | None = Field(None, description="Process ID")
    uptime_seconds: float | None = Field(None, description="Recording uptime")
    job_id: int | None = Field(None, description="Job ID")


class TimelapseStatusResponse(BaseModel):
    """Timelapse status response."""

    camera_id: int = Field(..., description="Camera ID")
    is_running: bool = Field(..., description="Whether timelapse is running")
    current_frame: int = Field(0, description="Current frame count")
    total_frames: int | None = Field(None, description="Total frames target")
    job_id: int | None = Field(None, description="Job ID")


class OperationResponse(BaseModel):
    """Generic operation response."""

    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(..., description="Status message")
    job_id: int | None = Field(None, description="Associated job ID")
    filepath: str | None = Field(None, description="Output file path")
    pid: int | None = Field(None, description="Process ID")

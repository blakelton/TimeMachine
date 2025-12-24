"""Observation API schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# Minimum capture interval in seconds for timelapse (below this causes crashes)
MIN_CAPTURE_INTERVAL_SECONDS = 5


# Configuration schemas for observation types
class TimelapseObservationConfig(BaseModel):
    """Configuration for timelapse observations."""

    interval_value: int = Field(1, ge=1, description="Interval numeric value")
    interval_unit: Literal["seconds", "minutes", "hours"] = Field(
        "minutes", description="Interval time unit"
    )

    @model_validator(mode="after")
    def validate_minimum_interval(self) -> "TimelapseObservationConfig":
        """Ensure capture interval is at least 5 seconds to prevent crashes."""
        # Convert to seconds
        if self.interval_unit == "hours":
            interval_seconds = self.interval_value * 3600
        elif self.interval_unit == "minutes":
            interval_seconds = self.interval_value * 60
        else:
            interval_seconds = self.interval_value

        if interval_seconds < MIN_CAPTURE_INTERVAL_SECONDS:
            raise ValueError(
                f"Capture interval must be at least {MIN_CAPTURE_INTERVAL_SECONDS} seconds. "
                f"Got {interval_seconds} seconds ({self.interval_value} {self.interval_unit})."
            )
        return self

    end_mode: Literal["datetime", "duration"] = Field(
        "duration", description="How to determine when observation ends"
    )
    end_datetime: datetime | None = Field(
        None, description="End datetime (if end_mode is 'datetime')"
    )
    duration_value: int | None = Field(
        None, ge=1, description="Duration numeric value (if end_mode is 'duration')"
    )
    duration_unit: Literal["seconds", "minutes", "hours"] | None = Field(
        None, description="Duration time unit (if end_mode is 'duration')"
    )

    output_fps: int = Field(30, ge=1, le=60, description="Output video FPS")
    resolution_width: int = Field(1920, ge=640, description="Output width")
    resolution_height: int = Field(1080, ge=480, description="Output height")
    quality: int = Field(95, ge=1, le=100, description="JPEG quality (1-100)")

    # Environment overlay settings
    env_overlay_device_id: int | None = Field(
        None, description="Environment device ID for data overlay (optional)"
    )
    env_overlay_position: Literal["tl", "tr", "bl", "br"] = Field(
        "br", description="Overlay position: tl, tr, bl, br"
    )
    env_overlay_show_graph: bool = Field(
        False, description="Show temperature mini-graph on overlay"
    )


class RecordingObservationConfig(BaseModel):
    """Configuration for recording observations."""

    end_mode: Literal["datetime", "duration", "manual"] = Field(
        "manual", description="How to determine when observation ends"
    )
    end_datetime: datetime | None = Field(
        None, description="End datetime (if end_mode is 'datetime')"
    )
    duration_value: int | None = Field(
        None, ge=1, description="Duration numeric value (if end_mode is 'duration')"
    )
    duration_unit: Literal["seconds", "minutes", "hours"] | None = Field(
        None, description="Duration time unit (if end_mode is 'duration')"
    )

    bitrate_kbps: int = Field(4000, ge=500, le=25000, description="Video bitrate in kbps")
    resolution_width: int = Field(1920, ge=640, description="Output width")
    resolution_height: int = Field(1080, ge=480, description="Output height")


# Request schemas
class StartObservationRequest(BaseModel):
    """Request to start a new observation."""

    camera_id: int = Field(..., description="Camera ID")
    observation_type: Literal["timelapse", "recording"] = Field(
        ..., description="Type of observation"
    )

    timelapse_config: TimelapseObservationConfig | None = Field(
        None, description="Timelapse configuration (required if type is 'timelapse')"
    )
    recording_config: RecordingObservationConfig | None = Field(
        None, description="Recording configuration (required if type is 'recording')"
    )


class StopObservationRequest(BaseModel):
    """Request to stop an observation."""

    assemble_video: bool = Field(
        True, description="Whether to assemble timelapse frames into video"
    )


class UpdateObservationNotesRequest(BaseModel):
    """Request to update observation notes."""

    notes: str = Field(..., description="Notes content (markdown supported)")


# Response schemas
class ObservationProgressResponse(BaseModel):
    """Progress information for an observation."""

    current: int = Field(..., description="Current progress (frames or seconds)")
    total: int | None = Field(None, description="Target progress (None if manual stop)")
    percentage: float | None = Field(
        None, description="Progress percentage (None if manual stop)"
    )


class ObservationResponse(BaseModel):
    """Response schema for an observation."""

    id: int = Field(..., description="Observation ID")
    camera_id: int = Field(..., description="Camera ID")
    observation_type: str = Field(..., description="Type: timelapse or recording")
    status: str = Field(
        ..., description="Status: running, completed, failed, stopped"
    )

    folder_path: str = Field(..., description="Observation folder path")
    config: dict = Field(..., description="Type-specific configuration")

    progress_current: int = Field(..., description="Current progress")
    progress_total: int | None = Field(None, description="Target progress")
    size_bytes: int = Field(..., description="Total size in bytes")

    started_at: datetime = Field(..., description="Start timestamp")
    target_end_at: datetime | None = Field(None, description="Target end timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")

    job_id: int | None = Field(None, description="Associated job ID")
    error_message: str | None = Field(None, description="Error message if failed")
    notes: str | None = Field(None, description="User notes")

    model_config = {"from_attributes": True}


class ObservationStatusResponse(BaseModel):
    """Real-time status response for an observation."""

    id: int = Field(..., description="Observation ID")
    observation_type: str = Field(..., description="Type: timelapse or recording")
    status: str = Field(..., description="Current status")
    progress: ObservationProgressResponse = Field(..., description="Progress info")
    size_bytes: int = Field(..., description="Current size in bytes")
    size_formatted: str = Field(..., description="Human-readable size")
    elapsed_seconds: float = Field(..., description="Elapsed time in seconds")
    has_preview: bool = Field(
        False, description="Whether preview video is available (timelapse only)"
    )


class ObservationListResponse(BaseModel):
    """List of observations response."""

    observations: list[ObservationResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total count")


class ActiveObservationResponse(BaseModel):
    """Response for active observation on a camera."""

    has_active: bool = Field(..., description="Whether camera has active observation")
    observation: ObservationResponse | None = Field(
        None, description="Active observation details"
    )


class StartObservationResponse(BaseModel):
    """Response after starting an observation."""

    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(..., description="Status message")
    observation: ObservationResponse | None = Field(
        None, description="Created observation"
    )


class StopObservationResponse(BaseModel):
    """Response after stopping an observation."""

    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(..., description="Status message")
    observation: ObservationResponse | None = Field(
        None, description="Updated observation"
    )
    output_path: str | None = Field(None, description="Path to output file")


# Completed observation browser schemas
class CompletedObservationResponse(BaseModel):
    """Response schema for a completed observation in the browser."""

    id: int = Field(..., description="Observation ID")
    camera_id: int = Field(..., description="Camera ID")
    camera_name: str = Field(..., description="Camera name")
    observation_type: str = Field(..., description="Type: timelapse, recording, or still")
    status: str = Field(..., description="Status: completed, stopped, or failed")

    started_at: datetime = Field(..., description="Start timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")
    duration_seconds: float = Field(..., description="Duration in seconds")

    frame_count: int | None = Field(None, description="Number of frames (timelapse only)")
    size_bytes: int = Field(..., description="Total size in bytes")
    size_display: str = Field(..., description="Human-readable size")

    notes: str | None = Field(None, description="User notes")
    thumbnail_url: str = Field(..., description="URL to thumbnail image")
    media_url: str = Field(..., description="URL to full media file")

    model_config = {"from_attributes": True}


class CompletedObservationListResponse(BaseModel):
    """List of completed observations for the browser."""

    observations: list[CompletedObservationResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total count matching filters")
    limit: int = Field(..., description="Requested limit")
    offset: int = Field(..., description="Requested offset")

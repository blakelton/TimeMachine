"""Output configuration API schemas."""

from pydantic import BaseModel, Field


class OutputConfigBase(BaseModel):
    """Base output configuration schema."""

    recordings_path: str = Field(
        "/var/lib/timemachine/media/recordings",
        description="Base directory for recordings",
    )
    stills_path: str = Field(
        "/var/lib/timemachine/media/stills",
        description="Base directory for still captures",
    )
    timelapse_path: str = Field(
        "/var/lib/timemachine/media/timelapse",
        description="Base directory for timelapses",
    )
    retention_days: int = Field(
        30, ge=1, le=365, description="Number of days to retain recordings"
    )
    retention_max_gb: int = Field(
        50, ge=1, le=1000, description="Maximum storage usage in GB"
    )


class OutputConfigCreate(OutputConfigBase):
    """Schema for creating output configuration."""

    pass


class OutputConfigUpdate(BaseModel):
    """Schema for updating output configuration (all fields optional)."""

    recordings_path: str | None = Field(None, min_length=1)
    stills_path: str | None = Field(None, min_length=1)
    timelapse_path: str | None = Field(None, min_length=1)
    retention_days: int | None = Field(None, ge=1, le=365)
    retention_max_gb: int | None = Field(None, ge=1, le=1000)


class OutputConfigResponse(OutputConfigBase):
    """Schema for output configuration response."""

    id: int = Field(..., description="Configuration ID")

    model_config = {"from_attributes": True}


class OutputConfigListResponse(BaseModel):
    """Schema for output configuration list response."""

    configs: list[OutputConfigResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total number of configurations")

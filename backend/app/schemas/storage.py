"""Storage API schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class StoredFileResponse(BaseModel):
    """Response schema for a stored file."""

    file_id: str = Field(..., description="Unique file identifier for secure access")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="File type: recording, still, or timelapse")
    size_bytes: int = Field(..., description="File size in bytes")
    size_display: str = Field(..., description="Human-readable file size")
    created_at: datetime = Field(..., description="File creation timestamp")
    camera_id: Optional[int] = Field(None, description="Camera ID if detectable from filename")
    download_url: str = Field(..., description="URL to download the file")


class StorageStatsResponse(BaseModel):
    """Response schema for storage statistics."""

    total_files: int = Field(..., description="Total number of files")
    total_size_bytes: int = Field(..., description="Total size in bytes")
    total_size_display: str = Field(..., description="Human-readable total size")

    recordings: dict = Field(..., description="Recording files stats")
    stills: dict = Field(..., description="Still image stats")
    timelapse: dict = Field(..., description="Timelapse video stats")

    disk: Optional[dict] = Field(None, description="Disk usage information")


class StorageListResponse(BaseModel):
    """Response schema for file listing."""

    files: list[StoredFileResponse] = Field(..., description="List of files")
    total: int = Field(..., description="Total number of files matching filter")
    limit: int = Field(..., description="Maximum files returned")
    offset: int = Field(..., description="Number of files skipped")


class RetentionEnforceRequest(BaseModel):
    """Request schema for retention enforcement."""

    max_age_days: Optional[int] = Field(None, description="Delete files older than this")
    max_size_gb: Optional[float] = Field(None, description="Delete until under this size")


class RetentionEnforceResponse(BaseModel):
    """Response schema for retention enforcement."""

    deleted_by_age: int = Field(..., description="Files deleted due to age")
    deleted_by_size: int = Field(..., description="Files deleted due to size limit")
    deleted_size_bytes: int = Field(..., description="Total bytes deleted")
    deleted_size_display: str = Field(..., description="Human-readable deleted size")
    errors: int = Field(..., description="Number of deletion errors")

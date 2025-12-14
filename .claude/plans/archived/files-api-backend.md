# Feature: Files API - Backend Media Management

## Overview
Implement a Files API to allow browsing, downloading, and deleting media files (recordings, stills, timelapses) from the backend. This is critical for users to manage their captured media.

## Current State

**Media Storage Locations** (from output_config):
- Recordings: `/var/lib/timemachine/media/recordings/`
- Stills: `/var/lib/timemachine/media/stills/`
- Timelapses: `/var/lib/timemachine/media/timelapse/`

**Existing Infrastructure**:
- nginx serves `/media/` from `/var/lib/timemachine/media/`
- OutputConfig model stores paths and retention settings
- Jobs track recording/timelapse operations with output_path

**Missing**:
- No API to list files
- No API to get file metadata
- No API to delete files
- Frontend has no way to browse media

## Requirements

### Functional Requirements
- FR1: List recordings with metadata (filename, size, duration, camera_id, created_at)
- FR2: List stills with metadata (filename, size, camera_id, created_at)
- FR3: List timelapses with metadata (filename, size, frame_count, camera_id, created_at)
- FR4: Filter files by camera_id
- FR5: Paginate file listings (limit/offset)
- FR6: Delete individual files
- FR7: Get file download URL (via nginx /media/ path)
- FR8: Get disk usage statistics per media type

### Non-Functional Requirements
- NFR1: File listing should be fast (<500ms for up to 1000 files)
- NFR2: Secure: validate file paths to prevent path traversal attacks
- NFR3: Atomic deletion: remove file and any associated job record
- NFR4: Support sorting by date, size, name

## API Design

### Endpoints

```
GET  /api/v1/files/recordings
GET  /api/v1/files/stills
GET  /api/v1/files/timelapses
GET  /api/v1/files/{file_type}/{filename}
DELETE /api/v1/files/{file_type}/{filename}
GET  /api/v1/files/stats
```

### GET /api/v1/files/recordings

**Query Parameters**:
- `camera_id` (optional): Filter by camera
- `limit` (default: 50): Max files to return
- `offset` (default: 0): Pagination offset
- `sort_by` (default: "created_at"): Sort field (created_at, size, name)
- `sort_order` (default: "desc"): Sort direction (asc, desc)

**Response** (200):
```json
{
  "files": [
    {
      "filename": "recording_2024-01-15_14-30-00.mp4",
      "path": "/media/recordings/recording_2024-01-15_14-30-00.mp4",
      "size_bytes": 52428800,
      "size_human": "50.0 MB",
      "duration_seconds": 120,
      "camera_id": 1,
      "camera_name": "USB Camera 1",
      "created_at": "2024-01-15T14:30:00Z",
      "job_id": 42
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

### GET /api/v1/files/stills

**Response** (200):
```json
{
  "files": [
    {
      "filename": "capture_2024-01-15_14-30-00.jpg",
      "path": "/media/stills/capture_2024-01-15_14-30-00.jpg",
      "size_bytes": 1048576,
      "size_human": "1.0 MB",
      "width": 1920,
      "height": 1080,
      "camera_id": 1,
      "camera_name": "USB Camera 1",
      "created_at": "2024-01-15T14:30:00Z"
    }
  ],
  "total": 500,
  "limit": 50,
  "offset": 0
}
```

### GET /api/v1/files/timelapses

**Response** (200):
```json
{
  "files": [
    {
      "filename": "timelapse_2024-01-15_14-30-00.mp4",
      "path": "/media/timelapse/timelapse_2024-01-15_14-30-00.mp4",
      "size_bytes": 104857600,
      "size_human": "100.0 MB",
      "duration_seconds": 60,
      "frame_count": 360,
      "camera_id": 1,
      "camera_name": "USB Camera 1",
      "created_at": "2024-01-15T14:30:00Z",
      "job_id": 43
    }
  ],
  "total": 25,
  "limit": 50,
  "offset": 0
}
```

### DELETE /api/v1/files/{file_type}/{filename}

**Path Parameters**:
- `file_type`: "recordings", "stills", or "timelapses"
- `filename`: The filename to delete

**Response** (204): No content on success

**Errors**:
- 404: File not found
- 400: Invalid file_type
- 403: Cannot delete (file in use by running job)

### GET /api/v1/files/stats

**Response** (200):
```json
{
  "recordings": {
    "count": 150,
    "total_size_bytes": 5368709120,
    "total_size_human": "5.0 GB"
  },
  "stills": {
    "count": 500,
    "total_size_bytes": 524288000,
    "total_size_human": "500.0 MB"
  },
  "timelapses": {
    "count": 25,
    "total_size_bytes": 2684354560,
    "total_size_human": "2.5 GB"
  },
  "total": {
    "count": 675,
    "total_size_bytes": 8577351680,
    "total_size_human": "8.0 GB"
  },
  "disk_free_bytes": 10737418240,
  "disk_free_human": "10.0 GB"
}
```

## Implementation Plan

### Phase 1: Core Files Service

**Task 1.1: Create FileInfo schema**

File: `backend/app/schemas/files.py`

```python
from datetime import datetime
from pydantic import BaseModel, Field

class FileInfo(BaseModel):
    """Base file information."""
    filename: str
    path: str  # URL path for nginx serving
    size_bytes: int
    size_human: str
    camera_id: int | None = None
    camera_name: str | None = None
    created_at: datetime
    job_id: int | None = None

class RecordingFile(FileInfo):
    """Recording file with duration."""
    duration_seconds: float | None = None

class StillFile(FileInfo):
    """Still image file with dimensions."""
    width: int | None = None
    height: int | None = None

class TimelapseFile(FileInfo):
    """Timelapse file with frame count."""
    duration_seconds: float | None = None
    frame_count: int | None = None

class FileListResponse(BaseModel):
    """Paginated file list response."""
    files: list[FileInfo]
    total: int
    limit: int
    offset: int

class FileStats(BaseModel):
    """Statistics for a file type."""
    count: int
    total_size_bytes: int
    total_size_human: str

class FileStatsResponse(BaseModel):
    """Overall file statistics."""
    recordings: FileStats
    stills: FileStats
    timelapses: FileStats
    total: FileStats
    disk_free_bytes: int
    disk_free_human: str
```

**Task 1.2: Create FilesService**

File: `backend/app/services/files.py`

```python
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

FileType = Literal["recordings", "stills", "timelapses"]

class FilesService:
    """Service for managing media files."""

    def __init__(self):
        self.base_paths = {
            "recordings": Path(settings.RECORDING_PATH),
            "stills": Path(settings.STILL_PATH),
            "timelapses": Path(settings.TIMELAPSE_PATH),
        }

    def _format_size(self, size_bytes: int) -> str:
        """Format bytes as human readable string."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    def _extract_camera_id(self, filename: str) -> int | None:
        """Extract camera ID from filename if present."""
        # Pattern: camera_1_recording_... or cam1_...
        match = re.search(r'camera[_-]?(\d+)', filename, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def _get_file_created_time(self, filepath: Path) -> datetime:
        """Get file creation time."""
        stat = filepath.stat()
        # Use mtime as ctime may be inode change time on Linux
        return datetime.fromtimestamp(stat.st_mtime)

    async def list_files(
        self,
        file_type: FileType,
        camera_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[dict], int]:
        """List files of a given type with metadata."""
        base_path = self.base_paths[file_type]

        if not base_path.exists():
            return [], 0

        # Get all files
        files = []
        for filepath in base_path.iterdir():
            if not filepath.is_file():
                continue

            # Filter by extension based on type
            if file_type == "recordings" and filepath.suffix not in [".mp4", ".mkv", ".avi"]:
                continue
            if file_type == "stills" and filepath.suffix not in [".jpg", ".jpeg", ".png"]:
                continue
            if file_type == "timelapses" and filepath.suffix not in [".mp4", ".mkv", ".avi"]:
                continue

            file_camera_id = self._extract_camera_id(filepath.name)

            # Filter by camera_id if specified
            if camera_id is not None and file_camera_id != camera_id:
                continue

            stat = filepath.stat()
            files.append({
                "filename": filepath.name,
                "path": f"/media/{file_type}/{filepath.name}",
                "size_bytes": stat.st_size,
                "size_human": self._format_size(stat.st_size),
                "camera_id": file_camera_id,
                "created_at": datetime.fromtimestamp(stat.st_mtime),
            })

        # Sort
        reverse = sort_order == "desc"
        if sort_by == "created_at":
            files.sort(key=lambda f: f["created_at"], reverse=reverse)
        elif sort_by == "size":
            files.sort(key=lambda f: f["size_bytes"], reverse=reverse)
        elif sort_by == "name":
            files.sort(key=lambda f: f["filename"], reverse=reverse)

        total = len(files)

        # Paginate
        files = files[offset:offset + limit]

        return files, total

    async def delete_file(self, file_type: FileType, filename: str) -> bool:
        """Delete a file. Returns True if deleted, False if not found."""
        base_path = self.base_paths[file_type]
        filepath = base_path / filename

        # Security: ensure file is within base path (prevent path traversal)
        try:
            filepath = filepath.resolve()
            base_path = base_path.resolve()
            if not str(filepath).startswith(str(base_path)):
                logger.warning("path_traversal_attempt", filename=filename)
                return False
        except Exception:
            return False

        if not filepath.exists():
            return False

        filepath.unlink()
        logger.info("file_deleted", file_type=file_type, filename=filename)
        return True

    async def get_stats(self) -> dict:
        """Get file statistics for all types."""
        stats = {}
        total_count = 0
        total_size = 0

        for file_type, base_path in self.base_paths.items():
            count = 0
            size = 0

            if base_path.exists():
                for filepath in base_path.iterdir():
                    if filepath.is_file():
                        count += 1
                        size += filepath.stat().st_size

            stats[file_type] = {
                "count": count,
                "total_size_bytes": size,
                "total_size_human": self._format_size(size),
            }
            total_count += count
            total_size += size

        # Get disk free space
        statvfs = os.statvfs(self.base_paths["recordings"])
        disk_free = statvfs.f_frsize * statvfs.f_bavail

        stats["total"] = {
            "count": total_count,
            "total_size_bytes": total_size,
            "total_size_human": self._format_size(total_size),
        }
        stats["disk_free_bytes"] = disk_free
        stats["disk_free_human"] = self._format_size(disk_free)

        return stats


# Singleton instance
files_service = FilesService()
```

### Phase 2: API Routes

**Task 2.1: Create files router**

File: `backend/app/api/routes/files.py`

```python
"""Files management API endpoints."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.camera import CameraRepository
from app.db.repositories.job import JobRepository
from app.db.session import get_session
from app.services.files import files_service, FileType

router = APIRouter(prefix="/files", tags=["files"])
logger = get_logger(__name__)


async def _enrich_with_camera_names(
    files: list[dict], session: AsyncSession
) -> list[dict]:
    """Add camera names to file list."""
    camera_repo = CameraRepository(session)
    cameras = await camera_repo.get_all()
    camera_map = {cam.id: cam.name for cam in cameras}

    for f in files:
        if f.get("camera_id"):
            f["camera_name"] = camera_map.get(f["camera_id"])

    return files


@router.get("/recordings")
async def list_recordings(
    session: Annotated[AsyncSession, Depends(get_session)],
    camera_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="created_at", regex="^(created_at|size|name)$"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$"),
):
    """List recording files."""
    files, total = await files_service.list_files(
        "recordings", camera_id, limit, offset, sort_by, sort_order
    )
    files = await _enrich_with_camera_names(files, session)

    logger.info("recordings_listed", total=total, camera_id=camera_id)

    return {"files": files, "total": total, "limit": limit, "offset": offset}


@router.get("/stills")
async def list_stills(
    session: Annotated[AsyncSession, Depends(get_session)],
    camera_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="created_at", regex="^(created_at|size|name)$"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$"),
):
    """List still image files."""
    files, total = await files_service.list_files(
        "stills", camera_id, limit, offset, sort_by, sort_order
    )
    files = await _enrich_with_camera_names(files, session)

    logger.info("stills_listed", total=total, camera_id=camera_id)

    return {"files": files, "total": total, "limit": limit, "offset": offset}


@router.get("/timelapses")
async def list_timelapses(
    session: Annotated[AsyncSession, Depends(get_session)],
    camera_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="created_at", regex="^(created_at|size|name)$"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$"),
):
    """List timelapse video files."""
    files, total = await files_service.list_files(
        "timelapses", camera_id, limit, offset, sort_by, sort_order
    )
    files = await _enrich_with_camera_names(files, session)

    logger.info("timelapses_listed", total=total, camera_id=camera_id)

    return {"files": files, "total": total, "limit": limit, "offset": offset}


@router.get("/stats")
async def get_file_stats():
    """Get file statistics for all media types."""
    stats = await files_service.get_stats()
    logger.info("file_stats_retrieved")
    return stats


@router.delete("/{file_type}/{filename}")
async def delete_file(
    file_type: Literal["recordings", "stills", "timelapses"],
    filename: str,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Delete a media file."""
    # Check if file is in use by a running job
    job_repo = JobRepository(session)
    running_jobs = await job_repo.get_running()
    for job in running_jobs:
        if job.output_path and filename in job.output_path:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete file: currently in use by a running job",
            )

    deleted = await files_service.delete_file(file_type, filename)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {filename}",
        )

    logger.info("file_deleted_via_api", file_type=file_type, filename=filename)
    return None  # 204 No Content
```

**Task 2.2: Register router**

File: `backend/app/api/routes/__init__.py` - Add:
```python
from app.api.routes.files import router as files_router
# ... in router list
api_router.include_router(files_router)
```

### Phase 3: Testing

**Task 3.1: Unit tests for FilesService**

File: `backend/tests/services/test_files.py`

- Test list_files with various filters
- Test delete_file success and not found
- Test get_stats calculation
- Test path traversal prevention

**Task 3.2: API tests**

File: `backend/tests/api/test_files.py`

- Test all endpoints with mock files
- Test pagination
- Test sorting
- Test camera_id filtering
- Test delete protection for running jobs

---

## Security Considerations

1. **Path Traversal**: Always resolve paths and verify they're within base directory
2. **File Type Validation**: Only serve expected file extensions
3. **Running Job Protection**: Don't delete files in use
4. **Rate Limiting**: Consider rate limiting delete operations

## File Naming Convention

Files should follow a consistent naming pattern for camera_id extraction:
```
camera_{id}_{type}_{timestamp}.{ext}
```

Examples:
- `camera_1_recording_2024-01-15_14-30-00.mp4`
- `camera_2_capture_2024-01-15_14-30-00.jpg`
- `camera_1_timelapse_2024-01-15_14-30-00.mp4`

Backend services (recording, capture, timelapse) should use this convention.

---

**Status**: `.ready.md` - Ready for implementation

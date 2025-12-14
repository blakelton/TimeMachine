# Storage & Output - Plan

## Overview

Implement file storage management, output configuration, retention policies, and NAS support.

**Dependencies**: 01-backend-foundation, 02-database-config
**Estimated Duration**: 2 days

---

## Phase 1: Storage Configuration

### Goal
Configurable paths with validation and free space monitoring.

### Tasks

1. **Create `app/services/storage/config.py`**
   ```python
   from pathlib import Path
   from dataclasses import dataclass
   import shutil
   import structlog

   logger = structlog.get_logger(__name__)

   @dataclass
   class StorageStats:
       path: str
       total_gb: float
       used_gb: float
       free_gb: float
       percent_used: float
       is_available: bool

   class StorageConfig:
       def __init__(self, recording_path: str, stills_path: str, timelapse_path: str):
           self.recording_path = Path(recording_path)
           self.stills_path = Path(stills_path)
           self.timelapse_path = Path(timelapse_path)

       def validate_paths(self) -> dict[str, bool]:
           """Validate all storage paths exist and are writable."""
           results = {}
           for name, path in [
               ("recording", self.recording_path),
               ("stills", self.stills_path),
               ("timelapse", self.timelapse_path),
           ]:
               try:
                   path.mkdir(parents=True, exist_ok=True)
                   test_file = path / ".write_test"
                   test_file.touch()
                   test_file.unlink()
                   results[name] = True
               except Exception as e:
                   logger.warning("path_validation_failed", path=str(path), error=str(e))
                   results[name] = False
           return results

       def get_stats(self, path: Path) -> StorageStats:
           """Get storage statistics for a path."""
           try:
               usage = shutil.disk_usage(path)
               return StorageStats(
                   path=str(path),
                   total_gb=usage.total / (1024**3),
                   used_gb=usage.used / (1024**3),
                   free_gb=usage.free / (1024**3),
                   percent_used=(usage.used / usage.total) * 100,
                   is_available=True,
               )
           except Exception as e:
               logger.error("storage_stats_failed", path=str(path), error=str(e))
               return StorageStats(
                   path=str(path),
                   total_gb=0,
                   used_gb=0,
                   free_gb=0,
                   percent_used=0,
                   is_available=False,
               )

       def get_all_stats(self) -> list[StorageStats]:
           return [
               self.get_stats(self.recording_path),
               self.get_stats(self.stills_path),
               self.get_stats(self.timelapse_path),
           ]
   ```

### Acceptance Criteria
- [ ] Path validation works
- [ ] Free space monitoring accurate
- [ ] NAS paths detected correctly

---

## Phase 2: File Organization

### Goal
Consistent directory structure and naming conventions.

### Directory Structure

```
{storage_root}/
├── recordings/
│   ├── camera_1/
│   │   ├── 2024-01/
│   │   │   ├── recording_20240115_103000.mp4
│   │   │   └── recording_20240115_143022.mp4
│   │   └── 2024-02/
│   └── camera_2/
├── stills/
│   ├── camera_1/
│   │   ├── 2024-01/
│   │   │   └── still_20240115_103005.jpg
│   │   └── 2024-02/
│   └── camera_2/
└── timelapse/
    ├── camera_1/
    │   └── timelapse_20240115_100000/
    │       ├── frame_00001.jpg
    │       ├── frame_00002.jpg
    │       └── output.mp4
    └── camera_2/
```

### Tasks

1. **Create `app/services/storage/organizer.py`**
   ```python
   from pathlib import Path
   from datetime import datetime
   from enum import Enum

   class MediaType(str, Enum):
       RECORDING = "recording"
       STILL = "still"
       TIMELAPSE = "timelapse"

   class FileOrganizer:
       def __init__(self, base_path: Path):
           self.base_path = base_path

       def get_camera_path(self, camera_id: int) -> Path:
           return self.base_path / f"camera_{camera_id}"

       def get_date_path(self, camera_id: int, date: datetime = None) -> Path:
           date = date or datetime.now()
           return self.get_camera_path(camera_id) / date.strftime("%Y-%m")

       def generate_filename(
           self,
           media_type: MediaType,
           camera_id: int,
           extension: str,
           timestamp: datetime = None,
       ) -> Path:
           timestamp = timestamp or datetime.now()
           date_path = self.get_date_path(camera_id, timestamp)
           date_path.mkdir(parents=True, exist_ok=True)
           
           filename = f"{media_type.value}_{timestamp.strftime('%Y%m%d_%H%M%S')}.{extension}"
           return date_path / filename

       def generate_timelapse_dir(self, camera_id: int, timestamp: datetime = None) -> Path:
           timestamp = timestamp or datetime.now()
           date_path = self.get_date_path(camera_id, timestamp)
           dir_name = f"timelapse_{timestamp.strftime('%Y%m%d_%H%M%S')}"
           timelapse_path = date_path / dir_name
           timelapse_path.mkdir(parents=True, exist_ok=True)
           return timelapse_path
   ```

### Acceptance Criteria
- [ ] Files organized by camera and date
- [ ] Consistent naming convention
- [ ] Timelapse sequences in dedicated folders

---

## Phase 3: Retention System

### Goal
Automatic cleanup based on age and size limits.

### Tasks

1. **Create `app/services/storage/retention.py`**
   ```python
   from pathlib import Path
   from datetime import datetime, timedelta
   from dataclasses import dataclass
   import asyncio
   import structlog

   logger = structlog.get_logger(__name__)

   @dataclass
   class RetentionPolicy:
       max_age_days: int = 30
       max_size_gb: float = 50.0
       enabled: bool = True

   @dataclass
   class CleanupResult:
       files_deleted: int
       space_freed_mb: float
       errors: list[str]

   class RetentionManager:
       def __init__(self, base_path: Path, policy: RetentionPolicy):
           self.base_path = base_path
           self.policy = policy

       def _get_all_files(self) -> list[Path]:
           """Get all media files sorted by modification time (oldest first)."""
           files = []
           for ext in ["*.mp4", "*.jpg", "*.jpeg", "*.png"]:
               files.extend(self.base_path.rglob(ext))
           return sorted(files, key=lambda f: f.stat().st_mtime)

       def _get_total_size_bytes(self, files: list[Path]) -> int:
           return sum(f.stat().st_size for f in files if f.exists())

       async def cleanup_by_age(self) -> CleanupResult:
           """Delete files older than max_age_days."""
           cutoff = datetime.now() - timedelta(days=self.policy.max_age_days)
           cutoff_ts = cutoff.timestamp()

           deleted = 0
           freed = 0.0
           errors = []

           for file in self._get_all_files():
               try:
                   if file.stat().st_mtime < cutoff_ts:
                       size = file.stat().st_size
                       file.unlink()
                       deleted += 1
                       freed += size / (1024 * 1024)
                       logger.info("file_deleted_age", path=str(file))
               except Exception as e:
                   errors.append(f"{file}: {e}")

           return CleanupResult(deleted, freed, errors)

       async def cleanup_by_size(self) -> CleanupResult:
           """Delete oldest files until under max_size_gb."""
           max_bytes = self.policy.max_size_gb * (1024**3)
           files = self._get_all_files()
           total_size = self._get_total_size_bytes(files)

           deleted = 0
           freed = 0.0
           errors = []

           for file in files:
               if total_size <= max_bytes:
                   break
               try:
                   size = file.stat().st_size
                   file.unlink()
                   total_size -= size
                   deleted += 1
                   freed += size / (1024 * 1024)
                   logger.info("file_deleted_size", path=str(file))
               except Exception as e:
                   errors.append(f"{file}: {e}")

           return CleanupResult(deleted, freed, errors)

       async def run_cleanup(self) -> CleanupResult:
           """Run all cleanup policies."""
           if not self.policy.enabled:
               return CleanupResult(0, 0, [])

           age_result = await self.cleanup_by_age()
           size_result = await self.cleanup_by_size()

           return CleanupResult(
               files_deleted=age_result.files_deleted + size_result.files_deleted,
               space_freed_mb=age_result.space_freed_mb + size_result.space_freed_mb,
               errors=age_result.errors + size_result.errors,
           )
   ```

### Acceptance Criteria
- [ ] Age-based cleanup works
- [ ] Size-based cleanup works
- [ ] Cleanup runs without blocking

---

## Phase 4: Storage Service

### Goal
Unified storage API with security measures.

### Tasks

1. **Create `app/services/storage/service.py`**
   ```python
   from pathlib import Path
   from datetime import datetime
   import os
   import structlog

   logger = structlog.get_logger(__name__)

   class PathSecurityError(Exception):
       pass

   class StorageService:
       def __init__(self, base_paths: dict[str, Path]):
           self.base_paths = base_paths

       def _validate_path(self, path: Path, base: Path) -> bool:
           """Prevent path traversal attacks."""
           try:
               resolved = path.resolve()
               base_resolved = base.resolve()
               return str(resolved).startswith(str(base_resolved))
           except Exception:
               return False

       def _sanitize_filename(self, filename: str) -> str:
           """Remove dangerous characters from filename."""
           # Remove path separators and null bytes
           sanitized = filename.replace("/", "_").replace("\\", "_").replace("\x00", "")
           # Remove leading dots
           while sanitized.startswith("."):
               sanitized = sanitized[1:]
           return sanitized or "unnamed"

       async def save_file(
           self,
           media_type: str,
           camera_id: int,
           data: bytes,
           extension: str,
       ) -> str:
           """Save file to appropriate location."""
           base = self.base_paths.get(media_type)
           if not base:
               raise ValueError(f"Unknown media type: {media_type}")

           timestamp = datetime.now()
           filename = f"{media_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}.{extension}"
           filename = self._sanitize_filename(filename)

           camera_path = base / f"camera_{camera_id}" / timestamp.strftime("%Y-%m")
           camera_path.mkdir(parents=True, exist_ok=True)

           file_path = camera_path / filename
           if not self._validate_path(file_path, base):
               raise PathSecurityError("Invalid path detected")

           file_path.write_bytes(data)
           logger.info("file_saved", path=str(file_path), size=len(data))
           return str(file_path)

       async def list_files(
           self,
           media_type: str,
           camera_id: int = None,
           limit: int = 100,
       ) -> list[dict]:
           """List files with metadata."""
           base = self.base_paths.get(media_type)
           if not base:
               return []

           search_path = base
           if camera_id:
               search_path = base / f"camera_{camera_id}"

           files = []
           for ext in ["*.mp4", "*.jpg", "*.jpeg"]:
               for f in search_path.rglob(ext):
                   stat = f.stat()
                   files.append({
                       "path": str(f),
                       "name": f.name,
                       "size_mb": stat.st_size / (1024 * 1024),
                       "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                       "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                   })
                   if len(files) >= limit:
                       break

           return sorted(files, key=lambda x: x["modified_at"], reverse=True)[:limit]

       async def delete_file(self, path: str) -> bool:
           """Delete a file with path validation."""
           file_path = Path(path)
           
           # Verify path is within allowed bases
           valid = False
           for base in self.base_paths.values():
               if self._validate_path(file_path, base):
                   valid = True
                   break

           if not valid:
               raise PathSecurityError("Path not in allowed directories")

           if file_path.exists():
               file_path.unlink()
               logger.info("file_deleted", path=path)
               return True
           return False
   ```

### Acceptance Criteria
- [ ] Path traversal prevented
- [ ] Filenames sanitized
- [ ] CRUD operations work

---

## Phase 5: API Endpoints

### Goal
REST API for output configuration and storage management.

### Tasks

1. **Create `app/api/routes/outputs.py`**
   ```python
   from fastapi import APIRouter, Depends
   from sqlalchemy.ext.asyncio import AsyncSession
   from datetime import datetime

   from app.db.session import get_session
   from app.db.repositories.output import OutputRepository
   from app.models.schemas.output import OutputConfigUpdate, OutputConfigResponse
   from app.models.schemas.common import ResponseWrapper, Meta

   router = APIRouter(prefix="/outputs")

   @router.get("", response_model=ResponseWrapper[OutputConfigResponse])
   async def get_output_config(session: AsyncSession = Depends(get_session)):
       repo = OutputRepository(session)
       config = await repo.get()
       return ResponseWrapper(
           data=OutputConfigResponse.model_validate(config),
           meta=Meta(timestamp=datetime.utcnow()),
       )

   @router.put("", response_model=ResponseWrapper[OutputConfigResponse])
   async def update_output_config(
       data: OutputConfigUpdate,
       session: AsyncSession = Depends(get_session),
   ):
       repo = OutputRepository(session)
       config = await repo.update(**data.model_dump(exclude_unset=True))
       return ResponseWrapper(
           data=OutputConfigResponse.model_validate(config),
           meta=Meta(timestamp=datetime.utcnow()),
       )

   @router.post("/test")
   async def test_output_paths(session: AsyncSession = Depends(get_session)):
       """Test write access to all configured paths."""
       repo = OutputRepository(session)
       config = await repo.get()
       
       from app.services.storage.config import StorageConfig
       storage = StorageConfig(
           config.recording_path,
           config.stills_path,
           config.timelapse_path,
       )
       results = storage.validate_paths()
       
       return ResponseWrapper(
           data={"paths": results},
           meta=Meta(timestamp=datetime.utcnow()),
       )
   ```

2. **Create `app/api/routes/storage.py`**
   ```python
   from fastapi import APIRouter, Depends, Query
   from sqlalchemy.ext.asyncio import AsyncSession
   from datetime import datetime

   from app.db.session import get_session

   router = APIRouter(prefix="/storage")

   @router.get("/stats")
   async def get_storage_stats(session: AsyncSession = Depends(get_session)):
       """Get storage usage statistics."""
       # Implementation
       pass

   @router.get("/files")
   async def list_files(
       media_type: str = Query(...),
       camera_id: int = Query(None),
       limit: int = Query(100, le=500),
       session: AsyncSession = Depends(get_session),
   ):
       """List stored files with filters."""
       # Implementation
       pass

   @router.delete("/files/{file_id}")
   async def delete_file(file_id: str, session: AsyncSession = Depends(get_session)):
       """Delete a stored file."""
       # Implementation
       pass

   @router.post("/cleanup")
   async def trigger_cleanup(session: AsyncSession = Depends(get_session)):
       """Manually trigger retention cleanup."""
       # Implementation
       pass
   ```

### Acceptance Criteria
- [ ] Output config CRUD works
- [ ] Path test endpoint functional
- [ ] File listing with filters
- [ ] Manual cleanup trigger

---

## Testing Requirements

| Test | Type | Coverage |
|------|------|----------|
| Path validation | Unit | Traversal prevention |
| File organizer | Unit | Naming conventions |
| Retention | Unit | Age/size cleanup |
| Storage service | Integration | Full operations |

---

## File Lifecycle

- Current: `.ready.md`
- When starting: Rename to `.in_progress.md`
- When complete: Move to `.claude/plans/completed/04-storage-output.md`

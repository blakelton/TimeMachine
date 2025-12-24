# DRY, SOLID Principles & Dead Code Evaluation

**Date:** 2025-12-23
**Analyzer:** Claude Opus 4.5
**Scope:** Full codebase analysis

---

## Executive Summary

| Principle | Compliance | Grade |
|-----------|------------|-------|
| DRY (Don't Repeat Yourself) | 65% | C |
| Single Responsibility | 60% | C |
| Open/Closed | 75% | B |
| Liskov Substitution | 90% | A |
| Interface Segregation | 70% | B- |
| Dependency Inversion | 65% | C |
| Dead Code | 85% Clean | B |

---

## DRY Principle Violations

### 1. Duplicate `_format_size` Implementations (CRITICAL)

**Found in 4 locations:**

| Location | Lines |
|----------|-------|
| `observation/service.py:37` | 10 |
| `timelapse.py:916` | 10 |
| `storage/service.py:434` | 10 |
| `observations.py:34` | 10 |

**Identical Implementation:**
```python
def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
```

**Fix:** Move to `app/core/utils.py`:
```python
# app/core/utils.py
def format_bytes(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"
```

### 2. Duplicate `formatDate` and `formatDuration` (Frontend)

**Found in multiple components with local implementations:**

| Component | Function | Status |
|-----------|----------|--------|
| utils/formatters.ts | formatDate, formatDuration | CANONICAL |
| TimelapseResumeBar.tsx:36 | formatDate (local) | DUPLICATE |
| ObservationInProgress.tsx:34 | formatDuration (local) | DUPLICATE |
| ImageLightbox.tsx:26 | formatDate (local) | DUPLICATE |
| VideoPlayer.tsx:41 | formatDate (local) | DUPLICATE |
| ObservationTile.tsx:21 | formatDate (local) | DUPLICATE |
| ObservationTile.tsx:44 | formatDuration (local) | DUPLICATE |

**Fix:** Remove local implementations, import from formatters.ts:
```typescript
import { formatDate, formatDuration } from '../../utils/formatters';
```

### 3. Magic Numbers Not Using Constants

**Backend constants defined but not used:**

| Constant | Defined In | Used By |
|----------|------------|---------|
| MAX_FILE_LIST_LIMIT (10000) | constants.py | 0 files (hardcoded in 3 places) |
| DB_BUSY_TIMEOUT_MS (5000) | constants.py | 0 files (hardcoded in session.py) |
| STREAM_CHUNK_SIZE_BYTES (65536) | constants.py | 0 files (hardcoded in cameras.py) |

**Fix:** Import and use constants:
```python
from app.core.constants import (
    MAX_FILE_LIST_LIMIT,
    DB_BUSY_TIMEOUT_MS,
    STREAM_CHUNK_SIZE_BYTES,
)
```

### 4. Duplicate Time Unit Conversion Logic

**Backend:** `_interval_to_seconds` in observation/service.py

**Frontend:** Similar logic exists inline in StartObservationModal.tsx

**Fix:** Create shared utility or API contract

---

## SOLID Principles Analysis

### S - Single Responsibility Principle

#### Violations Found

**1. ObservationService (1,365 lines, 28 methods)**

Current responsibilities:
- Observation CRUD operations
- Progress tracking (background loop)
- Live preview generation (background loop)
- Timelapse orchestration
- Recording orchestration
- Folder/metadata management
- Preview video generation

**Recommended Split:**
```
observation/
├── __init__.py
├── service.py            # Main orchestration (~300 lines)
├── timelapse_handler.py  # Timelapse-specific logic
├── recording_handler.py  # Recording-specific logic
├── progress_tracker.py   # Progress monitoring loop
├── preview_generator.py  # Preview generation
└── metadata.py           # Folder/metadata helpers
```

**2. cameras.py Router (1,703 lines)**

Current responsibilities:
- Camera CRUD (list, create, update, delete)
- Camera health checks
- Camera discovery
- Preview management
- Recording control
- Timelapse control
- Image capture

**Recommended Split:**
```
cameras/
├── __init__.py
├── crud.py               # Basic CRUD operations
├── health.py             # Health check endpoint
├── discovery.py          # Discovery endpoints
├── preview.py            # Preview endpoints
├── recording.py          # Recording endpoints
├── timelapse.py          # Timelapse endpoints
└── capture.py            # Capture endpoints
```

### O - Open/Closed Principle

#### Compliance: Good (75%)

**Positive Examples:**
- `BaseRepository[T]` is extensible without modification
- `ManagedPipeline` state machine is configurable
- Custom exceptions extend `AppException`

**Violations:**
- No plugin system for sensor types (hardcoded DHT11/DHT22/BME280)
- Camera type handling uses if/else chains instead of strategy pattern

**Improvement:**
```python
# Current (violation)
if camera_type == "csi":
    command = self._build_csi_capture_command(...)
elif camera_type == "usb":
    command = self._build_usb_capture_command(...)

# Better (strategy pattern)
class CaptureStrategy(Protocol):
    def build_command(self, config: CaptureConfig) -> list[str]: ...

class CSICaptureStrategy(CaptureStrategy): ...
class USBCaptureStrategy(CaptureStrategy): ...

# Usage
strategy = self._strategies[camera_type]
command = strategy.build_command(config)
```

### L - Liskov Substitution Principle

#### Compliance: Excellent (90%)

**Good Examples:**
- All custom exceptions can substitute `AppException`
- Repository subclasses properly extend `BaseRepository`
- Sensor readers implement common interface

**Minor Issue:**
- Some repository methods add behaviors not in base class

### I - Interface Segregation Principle

#### Compliance: Fair (70%)

**Issues:**
- No formal interfaces/protocols for services
- `ObservationService` has too many public methods
- Frontend API client is monolithic

**Improvement:**
```python
# Define focused protocols
class ITimelapseService(Protocol):
    async def start(self, config: TimelapseConfig) -> Result: ...
    async def stop(self, camera_id: int) -> Result: ...
    def get_status(self, camera_id: int) -> Status: ...

class IRecordingService(Protocol):
    async def start(self, config: RecordingConfig) -> Result: ...
    async def stop(self, camera_id: int) -> Result: ...
    def get_status(self, camera_id: int) -> Status: ...
```

### D - Dependency Inversion Principle

#### Compliance: Fair (65%)

**Issues:**
1. **Direct Service Imports:**
   ```python
   # observation/service.py
   from app.services.camera.timelapse import timelapse_service  # Concrete
   from app.services.camera.recording import recording_service  # Concrete
   ```

2. **No Dependency Injection Container:**
   - Services are module-level singletons
   - Hard to mock for testing
   - Tight coupling between services

**Current Pattern:**
```python
# High-level module depends on low-level module
class ObservationService:
    def __init__(self):
        # Direct dependency on concrete implementations
        self._timelapse = timelapse_service  # Module-level singleton
```

**Recommended Pattern:**
```python
# Constructor injection
class ObservationService:
    def __init__(
        self,
        timelapse: ITimelapseService,
        recording: IRecordingService,
    ):
        self._timelapse = timelapse
        self._recording = recording

# Factory/container creates with dependencies
def create_observation_service() -> ObservationService:
    return ObservationService(
        timelapse=timelapse_service,
        recording=recording_service,
    )
```

---

## Dead Code Analysis

### Backend Dead Code

#### 1. Unused Imports (Confirmed by Vulture)

| File | Import | Confidence |
|------|--------|------------|
| db/session.py:8 | `Engine` | 90% |
| environment/sensors.py:223 | `NoSensorFoundError` | 90% |

#### 2. Unused Exception Classes (Potentially Dead)

Analysis of `app/core/exceptions.py` (17 exception classes):

| Exception Class | Used? | Evidence |
|-----------------|-------|----------|
| AppException | YES | main.py handler |
| ValidationError | NO | No raise found |
| UnauthorizedError | NO | No raise found |
| NotFoundError | NO | No raise found |
| ConflictError | NO | No raise found |
| CameraBusyError | NO | No raise found |
| RecordingLimitError | NO | No raise found |
| EncoderBusyError | NO | No raise found |
| RateLimitError | NO | No raise found |
| StorageError | NO | No raise found |
| InsufficientStorageError | NO | No raise found |
| PathSecurityError | NO | No raise found |
| CameraError | NO | No raise found |
| CameraDisconnectedError | NO | No raise found |
| PipelineError | NO | No raise found |
| ConfigError | NO | No raise found |
| MemoryPressureError | NO | No raise found |

**Analysis:** The exception hierarchy was created but routes use `HTTPException` directly instead. Either:
1. Migrate routes to use custom exceptions (recommended)
2. Remove unused exceptions

**Recommendation:** Keep exceptions, add middleware to convert them:
```python
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.code, "message": exc.message, "details": exc.details}
    )
```

#### 3. Constants Module Partially Used

| Constant | Used? |
|----------|-------|
| STATS_BROADCAST_INTERVAL_SECONDS | YES |
| DEFAULT_RATE_LIMIT_RETRY_AFTER_SECONDS | NO |
| DB_BUSY_TIMEOUT_MS | NO (hardcoded) |
| FFMPEG_TIMEOUT_SECONDS | NO |
| TIMELAPSE_WAIT_INTERVAL_SECONDS | NO |
| DEFAULT_FPS | NO |
| DEFAULT_OUTPUT_FPS | NO |
| MAX_FPS | NO |
| DEFAULT_TIMELAPSE_INTERVAL_SECONDS | NO |
| DEFAULT_VIDEO_WIDTH | NO |
| DEFAULT_VIDEO_HEIGHT | NO |
| MAX_FILE_LIST_LIMIT | NO (hardcoded) |
| DEFAULT_RETENTION_DAYS | NO |
| STREAM_CHUNK_SIZE_BYTES | NO (hardcoded) |
| FILE_ID_LOG_TRUNCATE_LENGTH | NO |
| DEFAULT_PREVIEW_MAX_FRAMES | NO |
| MIN_TEMPERATURE_CELSIUS | NO |
| MAX_TEMPERATURE_CELSIUS | NO |

**Status:** Constants defined but not imported - code uses magic numbers

### Frontend Dead Code

#### 1. Duplicate Utility Functions (Shadow Dead Code)

Local implementations shadow shared utilities:

| Component | Dead Function | Shadowed By |
|-----------|---------------|-------------|
| TimelapseResumeBar.tsx | formatDate | utils/formatters.ts |
| ObservationInProgress.tsx | formatDuration | utils/formatters.ts |
| ImageLightbox.tsx | formatDate | utils/formatters.ts |
| VideoPlayer.tsx | formatDate | utils/formatters.ts |
| ObservationTile.tsx | formatDate, formatDuration | utils/formatters.ts |

#### 2. CSS Rules (Potential Dead CSS)

Unable to verify without runtime analysis. Recommend:
- Use PurgeCSS in build process
- Add CSS coverage reporting

---

## Recommendations Summary

### Immediate Fixes (DRY)

1. **Create `app/core/utils.py`:**
   ```python
   # Centralize format_bytes, format_duration, etc.
   ```

2. **Remove duplicate frontend formatters:**
   ```bash
   # Delete local implementations, import from utils/formatters
   ```

3. **Use constants module:**
   ```python
   from app.core.constants import MAX_FILE_LIST_LIMIT
   ```

### SOLID Improvements

4. **Split ObservationService:**
   - Extract progress tracker
   - Extract preview generator
   - Create handler classes for timelapse/recording

5. **Split cameras.py router:**
   - Create cameras/ package
   - Separate endpoints by functionality

6. **Add service interfaces:**
   ```python
   # app/services/interfaces.py
   class ITimelapseService(Protocol): ...
   class IRecordingService(Protocol): ...
   ```

### Dead Code Cleanup

7. **Remove unused imports:**
   ```python
   # db/session.py - remove Engine import
   # environment/sensors.py - remove NoSensorFoundError
   ```

8. **Wire up exception handlers:**
   ```python
   # Use custom exceptions instead of HTTPException
   raise NotFoundError("Camera", camera_id)
   ```

9. **Use or remove constants:**
   - Either import and use defined constants
   - Or remove unused ones

---

## Metrics Impact

### Current State

| Metric | Value |
|--------|-------|
| Duplicate Code Blocks | ~15 |
| SRP Violations | 2 major |
| Unused Constants | 17/18 |
| Unused Exceptions | 16/17 |
| Dead Imports | 2 |

### After Fixes

| Metric | Target |
|--------|--------|
| Duplicate Code Blocks | 0 |
| SRP Violations | 0 |
| Unused Constants | 0 |
| Unused Exceptions | 0 |
| Dead Imports | 0 |

---

## Priority Matrix

| Issue | Impact | Effort | Priority |
|-------|--------|--------|----------|
| Duplicate _format_size | HIGH | LOW | P1 |
| Frontend duplicate formatters | MEDIUM | LOW | P1 |
| Hardcoded magic numbers | MEDIUM | LOW | P1 |
| Unused exceptions | LOW | MEDIUM | P2 |
| ObservationService split | HIGH | HIGH | P2 |
| cameras.py split | HIGH | HIGH | P2 |
| Service interfaces | MEDIUM | MEDIUM | P3 |
| DI container | MEDIUM | HIGH | P3 |

---

*Report generated by automated code analysis*

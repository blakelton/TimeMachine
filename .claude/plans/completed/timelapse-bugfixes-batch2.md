# Timelapse Bugfixes - Batch 2

**Status**: Completed
**Priority**: Low to Architectural
**Scope**: 3 bugs related to video assembly validation, race conditions, and storage patterns
**Completed**: 2026-01-03

---

## Bug 4: Video Assembly Success Check Insufficient (Low Priority)

### Problem Statement

The video assembly success check only verifies ffmpeg return code and file existence, not file validity:

**File**: [assembly.py:69-86](backend/app/services/camera/timelapse/assembly.py#L69-L86)

```python
if proc.returncode == 0 and output_file.exists():
    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    logger.info(
        "timelapse_assembly_success",
        camera_id=camera_id,
        output=str(output_file),
        size_mb=file_size_mb,
    )
    return str(output_file)
else:
    error_msg = stderr.decode() if stderr else "Unknown error"
    logger.error(
        "timelapse_assembly_failed",
        # ...
    )
    return None
```

### Root Cause Analysis

1. **Empty file passes**: If ffmpeg creates an empty file before failing, the check passes
2. **Truncated file passes**: Disk-full conditions can create partial files that pass existence check
3. **Corrupted file passes**: A file with invalid MP4 structure would still pass
4. **No minimum size validation**: Even a 0-byte file would be accepted

The code DOES log `file_size_mb`, but doesn't use it for validation.

### Impact

- Users may receive "Video generated successfully" message for corrupt/empty files
- Downstream playback failures with no clear cause
- Wasted storage on invalid files

### Correction

#### Step 1: Add minimum file size validation

A valid MP4 with even 1 frame should be at least 1KB. Add a minimum size check:

**File**: [assembly.py:69-86](backend/app/services/camera/timelapse/assembly.py#L69-L86)

```python
MIN_VIDEO_SIZE_BYTES = 1024  # 1KB minimum for valid MP4

if proc.returncode == 0 and output_file.exists():
    file_size = output_file.stat().st_size
    file_size_mb = file_size / (1024 * 1024)

    # Validate minimum file size
    if file_size < MIN_VIDEO_SIZE_BYTES:
        logger.error(
            "timelapse_assembly_invalid_output",
            camera_id=camera_id,
            output=str(output_file),
            size_bytes=file_size,
            reason="File too small, likely corrupted or empty",
        )
        # Clean up invalid file
        try:
            output_file.unlink()
        except Exception:
            pass
        return None

    logger.info(
        "timelapse_assembly_success",
        camera_id=camera_id,
        output=str(output_file),
        size_mb=file_size_mb,
    )
    return str(output_file)
```

#### Step 2: Add frame count vs file size sanity check (Optional Enhancement)

For extra validation, compare expected size based on frame count:

```python
# Optional: Warn if file seems too small for frame count
frame_count = len(list(timelapse_dir.glob("frame_*.jpg")))
expected_min_size = frame_count * 1000  # ~1KB per frame compressed is very low estimate
if file_size < expected_min_size:
    logger.warning(
        "timelapse_assembly_size_warning",
        camera_id=camera_id,
        file_size=file_size,
        frame_count=frame_count,
        expected_min=expected_min_size,
        reason="Output file smaller than expected for frame count",
    )
```

#### Step 3: (Optional) Use ffprobe to validate MP4 structure

For robust validation, use ffprobe to check the file:

```python
async def validate_video(video_path: Path) -> tuple[bool, str]:
    """Validate video file using ffprobe.

    Returns:
        Tuple of (is_valid, error_message)
    """
    cmd = f"ffprobe -v error -select_streams v:0 -show_entries stream=codec_type -of csv=p=0 '{video_path}'"

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)

        if proc.returncode == 0 and b"video" in stdout:
            return True, ""
        else:
            return False, stderr.decode() if stderr else "No video stream found"
    except Exception as e:
        return False, str(e)
```

This is optional as it adds complexity and another subprocess call.

### Testing

1. Create a timelapse with 5 frames, verify video generation succeeds
2. Manually create an empty `.mp4` file, verify it's rejected by size check
3. Simulate disk-full by setting low disk quota, verify truncated file is rejected
4. Test with 1 frame timelapse - verify minimum viable video is accepted (should be >1KB)
5. Verify cleanup removes invalid files (don't leave orphaned empty files)

---

## Bug 5: Frame Count Race Condition During Resume (Very Low Priority)

### Problem Statement

When resuming a timelapse, frame counting uses glob without synchronization:

**File**: [service.py:269-274](backend/app/services/camera/timelapse/service.py#L269-L274)

```python
# Count existing frames
timelapse_dir = Path(job.timelapse_dir)
if not timelapse_dir.exists():
    return False, "Timelapse directory no longer exists"

existing_frames = len(list(timelapse_dir.glob("frame_*.jpg")))
```

### Root Cause Analysis

1. **No lock on frame directory**: Another process could write frames during count
2. **Glob is not atomic**: File could be created between glob() and len()
3. **Session check exists but is per-camera**: Doesn't prevent external writes

In practice, this is nearly impossible because:
- Only one timelapse session can run per camera
- Resume is only called for interrupted jobs (not running)
- The check at lines 262-264 prevents resuming while running

However, defensive programming suggests we should handle this edge case.

### Impact

- Extremely unlikely: Frame count could be off by 1
- Could cause duplicate frame numbers if count is wrong
- No data corruption, just potentially overwritten frames

### Correction

#### Step 1: Add explicit running check before frame count

**File**: [service.py:261-274](backend/app/services/camera/timelapse/service.py#L261-L274)

```python
# Check if already running (defensive - should already be checked)
camera_id = job.camera_id
if camera_id in self._sessions:
    session = self._sessions[camera_id]
    if session.is_running:
        return False, f"Timelapse already running for camera {camera_id}"
    # Session exists but not running - clean it up
    del self._sessions[camera_id]

# Restore config
config = TimelapseConfig.from_dict(camera_id, job.timelapse_config or {})

# Count existing frames (safe now that we've confirmed no active session)
timelapse_dir = Path(job.timelapse_dir)
if not timelapse_dir.exists():
    return False, "Timelapse directory no longer exists"

existing_frames = len(list(timelapse_dir.glob("frame_*.jpg")))
```

#### Step 2: Use sorted glob to find highest frame number

Instead of just counting, find the highest frame number to ensure correct continuation:

```python
# Find highest existing frame number for safe continuation
frame_files = sorted(timelapse_dir.glob("frame_*.jpg"))
if frame_files:
    # Extract frame number from last file: frame_000042.jpg -> 42
    last_frame_name = frame_files[-1].stem  # "frame_000042"
    try:
        existing_frames = int(last_frame_name.split("_")[1]) + 1  # Next frame number
    except (IndexError, ValueError):
        existing_frames = len(frame_files)  # Fallback to count
else:
    existing_frames = 0
```

This is more robust because:
- Finds the actual highest frame number, not just count
- Handles gaps in frame sequence (if some frames were deleted)
- Ensures new frames don't overwrite existing ones

#### Step 3: Add logging for frame count verification

```python
logger.debug(
    "timelapse_resume_frame_count",
    camera_id=camera_id,
    job_id=job_id,
    directory=str(timelapse_dir),
    existing_frames=existing_frames,
    frame_files_count=len(frame_files),
)
```

### Testing

1. Create timelapse with 10 frames, interrupt it
2. Manually delete frame_000005.jpg (create gap)
3. Resume timelapse - verify it continues from frame 10, not frame 9
4. Verify no duplicate frame numbers in final sequence
5. Test resume with empty directory - should fail gracefully

---

## Bug 6: Dual Storage Patterns Not Coordinated (Architectural Note)

### Problem Statement

Two timelapse storage patterns exist in the codebase without coordination:

**Pattern 1 - Job-based (Active)**:
- **File**: [service.py:92-95](backend/app/services/camera/timelapse/service.py#L92-L95)
- **Path**: `/media/timelapses/camera{id}_{timestamp}/`
- **Model**: `Job` with `job_type="timelapse"`

**Pattern 2 - Observation-based (Planned/Partial)**:
- **File**: `backend/app/db/models/observation.py`
- **Path**: `/media/observations/camera{id}_{timestamp}/` (implied)
- **Model**: `Observation` with `observation_type="timelapse"`

### Root Cause Analysis

The codebase appears to have two generations of design:
1. **Job model**: Original implementation for tracking camera operations
2. **Observation model**: Newer unified model for all camera outputs (recordings, timelapses, captures)

The Observation model seems more comprehensive but isn't fully integrated with the timelapse service.

### Impact

- Developer confusion about which pattern to use
- Potential for orphaned files if patterns diverge
- Maintenance burden of two systems
- Inconsistent API responses if both are queried

### Correction

This is an architectural decision that requires product/team input. The options are:

#### Option A: Document Current State (Minimal Change)

Add clear documentation explaining the relationship:

**File**: Create `backend/app/services/camera/README.md`

```markdown
# Camera Services Architecture

## Storage Patterns

### Job-based Storage (Current)
- Used by: TimelapseService, RecordingService
- Path: `/media/timelapses/`, `/media/recordings/`
- Model: `Job` table
- Status: Active, production-ready

### Observation-based Storage (Future)
- Planned unified model for all camera outputs
- Path: `/media/observations/`
- Model: `Observation` table
- Status: Planned, not yet integrated

## Migration Path
The Observation model is intended to eventually replace Job-based
storage for better organization and metadata. Migration TBD.
```

#### Option B: Centralize Path Configuration

Create a single source of truth for media paths:

**File**: `backend/app/core/paths.py`

```python
"""Centralized media path configuration."""

from pathlib import Path
from app.core.config import settings


class MediaPaths:
    """Media storage path configuration."""

    def __init__(self, base_path: str | None = None):
        self.base = Path(base_path or settings.media_path)

    @property
    def timelapses(self) -> Path:
        """Timelapse frames storage."""
        return self.base / "timelapses"

    @property
    def recordings(self) -> Path:
        """Video recordings storage."""
        return self.base / "recordings"

    @property
    def captures(self) -> Path:
        """Single image captures storage."""
        return self.base / "captures"

    @property
    def observations(self) -> Path:
        """Unified observations storage (future)."""
        return self.base / "observations"

    def timelapse_dir(self, camera_id: int, timestamp: str) -> Path:
        """Get timelapse directory for a camera."""
        return self.timelapses / f"camera{camera_id}_{timestamp}"

    def ensure_directories(self) -> None:
        """Create all media directories if they don't exist."""
        for path in [self.timelapses, self.recordings, self.captures]:
            path.mkdir(parents=True, exist_ok=True)


# Global instance
media_paths = MediaPaths()
```

Then update service.py to use it:

**File**: [service.py:92-95](backend/app/services/camera/timelapse/service.py#L92-L95)

```python
from app.core.paths import media_paths

# In start_timelapse():
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
timelapse_dir = media_paths.timelapse_dir(camera_id, timestamp)
timelapse_dir.mkdir(parents=True, exist_ok=True)
```

#### Option C: Deprecate Observation Model for Timelapses

If Job-based storage is working well, formally deprecate the Observation model for timelapses:

**File**: `backend/app/db/models/observation.py`

```python
"""
DEPRECATION NOTICE:
The Observation model for timelapse tracking is deprecated.
Use the Job model with job_type="timelapse" instead.
See: backend/app/services/camera/timelapse/service.py

This model remains for potential future unified storage but is not
currently integrated with the timelapse service.
"""
```

### Recommended Approach

**Option B (Centralize Path Configuration)** is recommended because:
1. Immediate value: Single source of truth for paths
2. Non-breaking: Doesn't change existing behavior
3. Future-ready: Makes migration to Observation model easier
4. Testable: Can unit test path generation

### Testing

1. Verify existing timelapses continue to work after path centralization
2. Verify new timelapses are created in correct directory
3. Verify interrupted timelapse detection still works
4. Check that settings.media_path override still works

---

## Implementation Order

1. **Bug 4** (Video Validation) - Prevents user-facing errors, quick fix
2. **Bug 5** (Race Condition) - Defensive programming, low risk
3. **Bug 6** (Storage Patterns) - Architectural, can be done incrementally

## Files to Modify

| File | Changes |
|------|---------|
| `backend/app/services/camera/timelapse/assembly.py` | Bug 4 |
| `backend/app/services/camera/timelapse/service.py` | Bug 5 |
| `backend/app/core/paths.py` | Bug 6 (new file) |
| `backend/app/services/camera/README.md` | Bug 6 (new file, documentation) |

## Dependencies

- Bug 4: None
- Bug 5: None
- Bug 6: Should be coordinated with any ongoing Observation model work

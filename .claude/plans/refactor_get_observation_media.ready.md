# Plan: Refactor get_observation_media Function

**Date:** 2025-12-23
**Priority:** P1 - Critical
**Current Complexity:** 22 (Grade D - HIGH)
**Target Complexity:** <10 per function (Grade A/B)
**File:** `backend/app/api/routes/observations.py:559`

---

## Problem Statement

The `get_observation_media` function has a cyclomatic complexity of 22 due to:
- Multiple nested loops for file discovery
- Three different observation types with unique logic
- Multiple file format checks per type
- Complex fallback patterns

## Current Structure Analysis

The function handles:
1. **Database lookup** - Get observation record
2. **Folder validation** - Check folder exists
3. **Timelapse media** - Check frames.mp4, output.mp4, timelapse.mp4, preview.mp4
4. **Recording media** - Check output.{mp4,mkv,avi,webm}, glob for output*
5. **Still media** - Check *.{jpg,jpeg,png,webp}, exclude thumbnails
6. **MIME type mapping** - Map file extension to content type
7. **Response building** - Return FileResponse

## Proposed Refactoring

### Strategy: Media Finder Strategy Pattern

Create a strategy pattern where each observation type has its own media finder, and extract MIME type mapping to a utility.

### Implementation Steps

#### Step 1: Create Media Finder Module

Create `backend/app/services/observation/media.py`:

```python
"""Observation media file discovery service."""

from pathlib import Path
from typing import Protocol
import structlog

logger = structlog.get_logger(__name__)


# MIME type mappings
MIME_TYPES = {
    ".mp4": "video/mp4",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".webm": "video/webm",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def get_mime_type(filepath: Path) -> str:
    """Get MIME type for a file based on extension."""
    return MIME_TYPES.get(filepath.suffix.lower(), "application/octet-stream")


class MediaFinder(Protocol):
    """Protocol for observation media finders."""

    def find(self, folder_path: Path) -> tuple[Path | None, str]:
        """
        Find media file in observation folder.

        Returns:
            (filepath, mime_type) or (None, "") if not found
        """
        ...


class TimelapseMediaFinder:
    """Find media files for timelapse observations."""

    # Priority order for timelapse videos
    VIDEO_NAMES = ["frames.mp4", "output.mp4", "timelapse.mp4", "preview.mp4"]

    def find(self, folder_path: Path) -> tuple[Path | None, str]:
        """
        Find timelapse video file.

        Checks in priority order:
        1. frames.mp4 (full assembled video)
        2. output.mp4 (alternate name)
        3. timelapse.mp4 (alternate name)
        4. preview.mp4 (short preview, fallback)

        Complexity: ~3
        """
        for name in self.VIDEO_NAMES:
            candidate = folder_path / name
            if candidate.exists():
                return candidate, get_mime_type(candidate)

        return None, ""


class RecordingMediaFinder:
    """Find media files for recording observations."""

    VIDEO_EXTENSIONS = [".mp4", ".mkv", ".avi", ".webm"]

    def find(self, folder_path: Path) -> tuple[Path | None, str]:
        """
        Find recording video file.

        Checks for output.{ext} files, then globs for output*.

        Complexity: ~5
        """
        # Check standard output.{ext} names first
        for ext in self.VIDEO_EXTENSIONS:
            candidate = folder_path / f"output{ext}"
            if candidate.exists():
                return candidate, get_mime_type(candidate)

        # Fallback: glob for any output* video
        for filepath in folder_path.glob("output*"):
            if filepath.suffix.lower() in self.VIDEO_EXTENSIONS:
                return filepath, get_mime_type(filepath)

        return None, ""


class StillMediaFinder:
    """Find media files for still image observations."""

    IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
    EXCLUDE_NAMES = {"thumbnail.jpg", "thumbnail.jpeg", "thumbnail.png"}

    def find(self, folder_path: Path) -> tuple[Path | None, str]:
        """
        Find still image file.

        Searches for image files, excluding thumbnails.

        Complexity: ~5
        """
        for ext in self.IMAGE_EXTENSIONS:
            for filepath in folder_path.glob(f"*{ext}"):
                if filepath.name.lower() not in self.EXCLUDE_NAMES:
                    return filepath, get_mime_type(filepath)

        return None, ""


def get_media_finder(observation_type: str) -> MediaFinder:
    """
    Factory function to get appropriate media finder.

    Complexity: ~2
    """
    finders = {
        "timelapse": TimelapseMediaFinder(),
        "recording": RecordingMediaFinder(),
        "still": StillMediaFinder(),
    }
    return finders.get(observation_type, RecordingMediaFinder())


async def find_observation_media(
    folder_path: Path,
    observation_type: str,
) -> tuple[Path | None, str]:
    """
    Find the main media file for an observation.

    Args:
        folder_path: Path to observation folder
        observation_type: Type of observation (timelapse, recording, still)

    Returns:
        (filepath, mime_type) or (None, "") if not found

    Complexity: ~2
    """
    finder = get_media_finder(observation_type)
    return finder.find(folder_path)
```

#### Step 2: Refactored API Route

```python
@router.get("/{observation_id}/media")
async def get_observation_media(
    observation_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FileResponse:
    """
    Get the full media file for an observation.

    Complexity: ~5 (down from 22)
    """
    from app.services.observation.media import find_observation_media

    obs_repo = ObservationRepository(session)
    observation = await obs_repo.get(observation_id)

    if not observation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation {observation_id} not found",
        )

    folder_path = Path(observation.folder_path)
    if not folder_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Observation folder not found",
        )

    media_file, media_type = await find_observation_media(
        folder_path, observation.observation_type
    )

    if not media_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found",
        )

    return FileResponse(
        path=media_file,
        media_type=media_type,
        filename=media_file.name,
    )
```

### Complexity Analysis After Refactor

| Function | Before | After |
|----------|--------|-------|
| `get_observation_media` (route) | 22 | ~5 |
| `get_mime_type` | - | ~1 |
| `TimelapseMediaFinder.find` | - | ~3 |
| `RecordingMediaFinder.find` | - | ~5 |
| `StillMediaFinder.find` | - | ~5 |
| `get_media_finder` | - | ~2 |
| `find_observation_media` | - | ~2 |

**All functions under complexity 10.**

---

## Additional Benefits

### Reusability

The media finder can be reused in:
- Thumbnail generation
- Media listing endpoints
- Cleanup operations
- Storage analysis

### Extensibility

Adding new observation types (e.g., "burst", "hdr") only requires:
1. Create new `BurstMediaFinder` class
2. Add to `get_media_finder` factory
3. No changes to API route

### Testability

Each finder can be unit tested independently:
- Mock filesystem with specific files
- Test priority order
- Test fallback behavior

---

## Testing Strategy

### Unit Tests to Add

Create `backend/tests/services/observation/test_media.py`:

```python
def test_get_mime_type_mp4():
    assert get_mime_type(Path("video.mp4")) == "video/mp4"

def test_get_mime_type_unknown():
    assert get_mime_type(Path("file.xyz")) == "application/octet-stream"

def test_timelapse_finder_priority(tmp_path):
    # Create both frames.mp4 and preview.mp4
    (tmp_path / "frames.mp4").touch()
    (tmp_path / "preview.mp4").touch()
    finder = TimelapseMediaFinder()
    path, mime = finder.find(tmp_path)
    assert path.name == "frames.mp4"  # Higher priority

def test_timelapse_finder_fallback(tmp_path):
    # Only preview.mp4 exists
    (tmp_path / "preview.mp4").touch()
    finder = TimelapseMediaFinder()
    path, mime = finder.find(tmp_path)
    assert path.name == "preview.mp4"

def test_recording_finder_standard(tmp_path):
    (tmp_path / "output.mp4").touch()
    finder = RecordingMediaFinder()
    path, mime = finder.find(tmp_path)
    assert path.name == "output.mp4"

def test_recording_finder_glob(tmp_path):
    (tmp_path / "output_camera1.mkv").touch()
    finder = RecordingMediaFinder()
    path, mime = finder.find(tmp_path)
    assert path.name == "output_camera1.mkv"

def test_still_finder_excludes_thumbnail(tmp_path):
    (tmp_path / "thumbnail.jpg").touch()
    (tmp_path / "capture.jpg").touch()
    finder = StillMediaFinder()
    path, mime = finder.find(tmp_path)
    assert path.name == "capture.jpg"  # Not thumbnail

def test_still_finder_no_media(tmp_path):
    finder = StillMediaFinder()
    path, mime = finder.find(tmp_path)
    assert path is None
```

---

## Migration Steps

1. Create `backend/app/services/observation/media.py`
2. Add unit tests for media finder module
3. Update `observations.py` route to use new service
4. Run existing API tests
5. Remove old inline code from route

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Priority order changes | Document order in class, test thoroughly |
| Missing MIME types | Include all current types, add fallback |
| Performance regression | Finders are synchronous, minimal overhead |

---

## Success Criteria

- [ ] Route handler complexity < 10
- [ ] All finder functions complexity < 10
- [ ] All existing tests pass
- [ ] New unit tests for each finder
- [ ] Same media files returned as before
- [ ] MIME types unchanged

---

## Estimated Effort

- Implementation: 1-2 hours
- Testing: 1-2 hours
- Review & validation: 30 minutes

**Total: ~3-4 hours**

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

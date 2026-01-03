"""Centralized media path configuration.

This module provides a single source of truth for all media storage paths,
making it easier to maintain consistent path handling across the application.
"""

from pathlib import Path

from app.core.config import settings


class MediaPaths:
    """Media storage path configuration.

    Centralizes all media path logic to ensure consistency across:
    - TimelapseService
    - RecordingService
    - CaptureService
    - Future Observation-based storage

    Usage:
        from app.core.paths import media_paths

        timelapse_dir = media_paths.timelapse_dir(camera_id=1, timestamp="20250103_143000")
    """

    def __init__(self, base_path: Path | str | None = None):
        """Initialize media paths.

        Args:
            base_path: Base media directory. Defaults to settings.media_path.
        """
        if base_path is None:
            self.base = settings.media_path
        else:
            self.base = Path(base_path)

    @property
    def timelapses(self) -> Path:
        """Timelapse frames storage directory."""
        return self.base / "timelapses"

    @property
    def recordings(self) -> Path:
        """Video recordings storage directory."""
        return self.base / "recordings"

    @property
    def captures(self) -> Path:
        """Single image captures storage directory."""
        return self.base / "captures"

    @property
    def observations(self) -> Path:
        """Unified observations storage directory (future).

        Note: The Observation model is planned but not yet fully integrated
        with the timelapse/recording services. This path is reserved for
        future migration to a unified storage pattern.
        """
        return self.base / "observations"

    def timelapse_dir(self, camera_id: int, timestamp: str) -> Path:
        """Get timelapse directory for a camera session.

        Args:
            camera_id: Camera database ID
            timestamp: Timestamp string (e.g., "20250103_143000")

        Returns:
            Path to timelapse frame directory
        """
        return self.timelapses / f"camera{camera_id}_{timestamp}"

    def recording_path(self, camera_id: int, timestamp: str, extension: str = "mp4") -> Path:
        """Get recording file path.

        Args:
            camera_id: Camera database ID
            timestamp: Timestamp string
            extension: File extension (default: mp4)

        Returns:
            Path to recording file
        """
        return self.recordings / f"camera{camera_id}_{timestamp}.{extension}"

    def capture_path(self, camera_id: int, timestamp: str, extension: str = "jpg") -> Path:
        """Get capture image path.

        Args:
            camera_id: Camera database ID
            timestamp: Timestamp string
            extension: File extension (default: jpg)

        Returns:
            Path to capture image file
        """
        return self.captures / f"camera{camera_id}_{timestamp}.{extension}"

    def ensure_directories(self) -> None:
        """Create all media directories if they don't exist."""
        for path in [self.timelapses, self.recordings, self.captures]:
            path.mkdir(parents=True, exist_ok=True)

    def cleanup_empty_dirs(self) -> int:
        """Remove empty subdirectories from media paths.

        Returns:
            Number of directories removed
        """
        removed = 0
        for base_dir in [self.timelapses, self.recordings, self.captures]:
            if not base_dir.exists():
                continue
            for subdir in base_dir.iterdir():
                if subdir.is_dir() and not any(subdir.iterdir()):
                    subdir.rmdir()
                    removed += 1
        return removed


# Global singleton instance
media_paths = MediaPaths()

"""Storage service for file management, listing, and retention enforcement."""

import asyncio
import base64
import hashlib
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class FileType(str, Enum):
    """Type of stored file."""

    RECORDING = "recording"
    STILL = "still"
    TIMELAPSE = "timelapse"
    UNKNOWN = "unknown"


@dataclass
class StoredFile:
    """Information about a stored file."""

    file_id: str
    filename: str
    file_type: FileType
    path: str
    size_bytes: int
    created_at: datetime
    camera_id: Optional[int] = None

    @property
    def size_mb(self) -> float:
        """Size in megabytes."""
        return self.size_bytes / (1024 * 1024)

    @property
    def size_display(self) -> str:
        """Human-readable size string."""
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        elif self.size_bytes < 1024 * 1024 * 1024:
            return f"{self.size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{self.size_bytes / (1024 * 1024 * 1024):.2f} GB"


class StorageService:
    """Service for managing stored media files.

    Features:
    - File listing by type
    - Secure file ID generation (prevents path traversal)
    - File deletion with validation
    - Retention enforcement (by age and total size)
    - Storage statistics
    """

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize storage service.

        Args:
            base_path: Base path for media storage (defaults to settings.media_path)
        """
        self.base_path = base_path or settings.media_path
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure storage directories exist."""
        for subdir in ["recordings", "stills", "timelapse"]:
            path = self.base_path / subdir
            path.mkdir(parents=True, exist_ok=True)

    @property
    def recordings_path(self) -> Path:
        """Path to recordings directory."""
        return self.base_path / "recordings"

    @property
    def stills_path(self) -> Path:
        """Path to stills directory."""
        return self.base_path / "stills"

    @property
    def timelapse_path(self) -> Path:
        """Path to timelapse directory."""
        return self.base_path / "timelapse"

    def _get_type_path(self, file_type: FileType) -> Path:
        """Get directory path for file type."""
        if file_type == FileType.RECORDING:
            return self.recordings_path
        elif file_type == FileType.STILL:
            return self.stills_path
        elif file_type == FileType.TIMELAPSE:
            return self.timelapse_path
        else:
            return self.base_path

    def _detect_file_type(self, file_path: Path) -> FileType:
        """Detect file type from path."""
        path_str = str(file_path).lower()
        if "recording" in path_str or file_path.suffix == ".mp4":
            # Check if it's in timelapse directory
            if "timelapse" in path_str:
                return FileType.TIMELAPSE
            return FileType.RECORDING
        elif "still" in path_str or file_path.suffix in [".jpg", ".jpeg", ".png"]:
            # Exclude timelapse frames
            if "timelapse" in path_str:
                return FileType.TIMELAPSE
            return FileType.STILL
        elif "timelapse" in path_str:
            return FileType.TIMELAPSE
        return FileType.UNKNOWN

    def _extract_camera_id(self, filename: str) -> Optional[int]:
        """Extract camera ID from filename if present.

        Expected format: camera_{id}_{timestamp}.ext or cam{id}_*.ext
        """
        import re

        # Try pattern: camera_1_*, cam1_*, etc.
        patterns = [
            r"camera[_-]?(\d+)",
            r"cam[_-]?(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    def generate_file_id(self, file_path: str) -> str:
        """Generate secure file ID from path.

        Uses base64 encoding with a hash prefix for validation.
        This prevents path traversal by only accepting IDs we generated.

        Args:
            file_path: Absolute path to file

        Returns:
            URL-safe file ID
        """
        # Create hash of path for validation
        path_hash = hashlib.sha256(file_path.encode()).hexdigest()[:8]
        # Encode path
        encoded = base64.urlsafe_b64encode(file_path.encode()).decode()
        # Combine hash and encoded path
        return f"{path_hash}_{encoded}"

    def decode_file_id(self, file_id: str) -> Optional[str]:
        """Decode file ID back to path with validation.

        Args:
            file_id: File ID to decode

        Returns:
            File path if valid, None otherwise
        """
        try:
            parts = file_id.split("_", 1)
            if len(parts) != 2:
                return None

            expected_hash, encoded = parts
            file_path = base64.urlsafe_b64decode(encoded.encode()).decode()

            # Verify hash
            actual_hash = hashlib.sha256(file_path.encode()).hexdigest()[:8]
            if actual_hash != expected_hash:
                logger.warning(
                    "file_id_hash_mismatch",
                    file_id=file_id[:20],
                    expected=expected_hash,
                    actual=actual_hash,
                )
                return None

            return file_path
        except Exception as e:
            logger.warning("file_id_decode_failed", file_id=file_id[:20], error=str(e))
            return None

    def validate_path(self, file_path: str) -> bool:
        """Validate that path is within allowed storage directories.

        Args:
            file_path: Path to validate

        Returns:
            True if path is valid and within storage directories
        """
        try:
            path = Path(file_path).resolve()
            base = self.base_path.resolve()

            # Check if path is within base directory
            path.relative_to(base)
            return True
        except ValueError:
            return False

    def get_file(self, file_id: str) -> Optional[StoredFile]:
        """Get file information by ID.

        Args:
            file_id: File ID

        Returns:
            StoredFile if found and valid, None otherwise
        """
        file_path = self.decode_file_id(file_id)
        if not file_path:
            return None

        if not self.validate_path(file_path):
            logger.warning(
                "file_access_denied_invalid_path",
                file_id=file_id[:20],
                path=file_path,
            )
            return None

        path = Path(file_path)
        if not path.exists():
            return None

        stat = path.stat()
        return StoredFile(
            file_id=file_id,
            filename=path.name,
            file_type=self._detect_file_type(path),
            path=file_path,
            size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_mtime),
            camera_id=self._extract_camera_id(path.name),
        )

    def get_file_path(self, file_id: str) -> Optional[Path]:
        """Get validated file path by ID.

        Args:
            file_id: File ID

        Returns:
            Path if valid, None otherwise
        """
        file_path = self.decode_file_id(file_id)
        if not file_path:
            return None

        if not self.validate_path(file_path):
            return None

        path = Path(file_path)
        if not path.exists():
            return None

        return path

    async def list_files(
        self,
        file_type: Optional[FileType] = None,
        camera_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StoredFile]:
        """List stored files with optional filtering.

        Args:
            file_type: Filter by file type
            camera_id: Filter by camera ID
            limit: Maximum files to return
            offset: Number of files to skip

        Returns:
            List of stored files, sorted by creation time (newest first)
        """
        files: list[StoredFile] = []

        # Determine which directories to scan
        if file_type:
            dirs = [self._get_type_path(file_type)]
        else:
            dirs = [self.recordings_path, self.stills_path, self.timelapse_path]

        # Collect all files
        for dir_path in dirs:
            if not dir_path.exists():
                continue

            for file_path in dir_path.rglob("*"):
                if not file_path.is_file():
                    continue

                # Skip hidden files and temp files
                if file_path.name.startswith(".") or file_path.name.startswith("~"):
                    continue

                # Skip timelapse frame images (only show final video)
                if (
                    "timelapse" in str(file_path).lower()
                    and file_path.suffix in [".jpg", ".jpeg", ".png"]
                    and "frame_" in file_path.name
                ):
                    continue

                detected_type = self._detect_file_type(file_path)
                detected_camera = self._extract_camera_id(file_path.name)

                # Apply filters
                if file_type and detected_type != file_type:
                    continue
                if camera_id and detected_camera != camera_id:
                    continue

                stat = file_path.stat()
                file_id = self.generate_file_id(str(file_path))

                files.append(
                    StoredFile(
                        file_id=file_id,
                        filename=file_path.name,
                        file_type=detected_type,
                        path=str(file_path),
                        size_bytes=stat.st_size,
                        created_at=datetime.fromtimestamp(stat.st_mtime),
                        camera_id=detected_camera,
                    )
                )

        # Sort by creation time (newest first)
        files.sort(key=lambda f: f.created_at, reverse=True)

        # Apply pagination
        return files[offset : offset + limit]

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file by ID.

        Args:
            file_id: File ID to delete

        Returns:
            True if deleted, False if not found or invalid
        """
        file_path = self.decode_file_id(file_id)
        if not file_path:
            return False

        if not self.validate_path(file_path):
            logger.warning("file_delete_denied_invalid_path", file_id=file_id[:20])
            return False

        path = Path(file_path)
        if not path.exists():
            return False

        try:
            path.unlink()
            logger.info(
                "file_deleted",
                file_id=file_id[:20],
                filename=path.name,
                size_mb=path.stat().st_size / (1024 * 1024) if path.exists() else 0,
            )
            return True
        except Exception as e:
            logger.error("file_delete_failed", file_id=file_id[:20], error=str(e))
            return False

    async def get_storage_stats(self) -> dict:
        """Get storage statistics.

        Returns:
            Dictionary with storage statistics
        """
        stats = {
            "total_files": 0,
            "total_size_bytes": 0,
            "recordings": {"count": 0, "size_bytes": 0},
            "stills": {"count": 0, "size_bytes": 0},
            "timelapse": {"count": 0, "size_bytes": 0},
        }

        for file in await self.list_files(limit=10000):
            stats["total_files"] += 1
            stats["total_size_bytes"] += file.size_bytes

            if file.file_type == FileType.RECORDING:
                stats["recordings"]["count"] += 1
                stats["recordings"]["size_bytes"] += file.size_bytes
            elif file.file_type == FileType.STILL:
                stats["stills"]["count"] += 1
                stats["stills"]["size_bytes"] += file.size_bytes
            elif file.file_type == FileType.TIMELAPSE:
                stats["timelapse"]["count"] += 1
                stats["timelapse"]["size_bytes"] += file.size_bytes

        # Add human-readable sizes
        stats["total_size_display"] = self._format_size(stats["total_size_bytes"])
        for key in ["recordings", "stills", "timelapse"]:
            stats[key]["size_display"] = self._format_size(stats[key]["size_bytes"])

        # Get disk usage
        try:
            usage = shutil.disk_usage(self.base_path)
            stats["disk"] = {
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "free_display": self._format_size(usage.free),
                "percent_used": (usage.used / usage.total) * 100,
            }
        except Exception as e:
            logger.warning("disk_usage_check_failed", error=str(e))
            stats["disk"] = None

        return stats

    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human-readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    async def enforce_retention(
        self,
        max_age_days: Optional[int] = None,
        max_size_gb: Optional[float] = None,
    ) -> dict:
        """Enforce retention policy by deleting old/excess files.

        Args:
            max_age_days: Delete files older than this (defaults to settings)
            max_size_gb: Delete oldest files until under this size (defaults to settings)

        Returns:
            Dictionary with cleanup results
        """
        max_age_days = max_age_days or settings.retention_days
        max_size_gb = max_size_gb or settings.retention_max_gb

        results = {
            "deleted_by_age": 0,
            "deleted_by_size": 0,
            "deleted_size_bytes": 0,
            "errors": 0,
        }

        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        max_size_bytes = max_size_gb * 1024 * 1024 * 1024

        # Get all files sorted by age (oldest first for size-based cleanup)
        all_files = await self.list_files(limit=10000)
        all_files.sort(key=lambda f: f.created_at)

        # Delete files older than max_age_days
        for file in all_files:
            if file.created_at < cutoff_date:
                if await self.delete_file(file.file_id):
                    results["deleted_by_age"] += 1
                    results["deleted_size_bytes"] += file.size_bytes
                else:
                    results["errors"] += 1

        # Recalculate total size after age-based cleanup
        remaining_files = await self.list_files(limit=10000)
        remaining_files.sort(key=lambda f: f.created_at)  # Oldest first
        total_size = sum(f.size_bytes for f in remaining_files)

        # Delete oldest files until under max_size_bytes
        for file in remaining_files:
            if total_size <= max_size_bytes:
                break
            if await self.delete_file(file.file_id):
                results["deleted_by_size"] += 1
                results["deleted_size_bytes"] += file.size_bytes
                total_size -= file.size_bytes
            else:
                results["errors"] += 1

        results["deleted_size_display"] = self._format_size(results["deleted_size_bytes"])

        logger.info(
            "retention_enforced",
            deleted_by_age=results["deleted_by_age"],
            deleted_by_size=results["deleted_by_size"],
            deleted_size=results["deleted_size_display"],
            errors=results["errors"],
        )

        return results


# Global storage service instance
storage_service = StorageService()

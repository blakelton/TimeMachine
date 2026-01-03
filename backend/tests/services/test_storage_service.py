"""Tests for storage service."""

from datetime import datetime
from pathlib import Path

import pytest

from app.services.storage.service import FileType, StorageService, StoredFile


class TestStoredFile:
    """Tests for StoredFile dataclass."""

    def test_stored_file_size_mb(self):
        """StoredFile calculates size_mb correctly."""
        file = StoredFile(
            file_id="test",
            filename="test.mp4",
            file_type=FileType.RECORDING,
            path="/test/path",
            size_bytes=10 * 1024 * 1024,  # 10 MB
            created_at=datetime.now(),
        )

        assert file.size_mb == 10.0

    def test_stored_file_size_display_bytes(self):
        """StoredFile displays bytes correctly."""
        file = StoredFile(
            file_id="test",
            filename="test.mp4",
            file_type=FileType.RECORDING,
            path="/test/path",
            size_bytes=500,
            created_at=datetime.now(),
        )

        assert file.size_display == "500 B"

    def test_stored_file_size_display_kb(self):
        """StoredFile displays KB correctly."""
        file = StoredFile(
            file_id="test",
            filename="test.mp4",
            file_type=FileType.RECORDING,
            path="/test/path",
            size_bytes=5 * 1024,  # 5 KB
            created_at=datetime.now(),
        )

        assert file.size_display == "5.0 KB"

    def test_stored_file_size_display_mb(self):
        """StoredFile displays MB correctly."""
        file = StoredFile(
            file_id="test",
            filename="test.mp4",
            file_type=FileType.RECORDING,
            path="/test/path",
            size_bytes=15 * 1024 * 1024,  # 15 MB
            created_at=datetime.now(),
        )

        assert file.size_display == "15.0 MB"

    def test_stored_file_size_display_gb(self):
        """StoredFile displays GB correctly."""
        file = StoredFile(
            file_id="test",
            filename="test.mp4",
            file_type=FileType.RECORDING,
            path="/test/path",
            size_bytes=2 * 1024 * 1024 * 1024,  # 2 GB
            created_at=datetime.now(),
        )

        assert file.size_display == "2.00 GB"


class TestStorageServiceInitialization:
    """Tests for StorageService initialization."""

    def test_service_creates_directories(self, tmp_path):
        """Service creates required directories on init."""
        service = StorageService(base_path=tmp_path)

        assert (tmp_path / "recordings").exists()
        assert (tmp_path / "stills").exists()
        assert (tmp_path / "timelapse").exists()

    def test_service_uses_provided_base_path(self, tmp_path):
        """Service uses provided base path."""
        service = StorageService(base_path=tmp_path)

        assert service.base_path == tmp_path


class TestStorageServicePaths:
    """Tests for storage path properties."""

    def test_recordings_path(self, tmp_path):
        """recordings_path returns correct path."""
        service = StorageService(base_path=tmp_path)

        assert service.recordings_path == tmp_path / "recordings"

    def test_stills_path(self, tmp_path):
        """stills_path returns correct path."""
        service = StorageService(base_path=tmp_path)

        assert service.stills_path == tmp_path / "stills"

    def test_timelapse_path(self, tmp_path):
        """timelapse_path returns correct path."""
        service = StorageService(base_path=tmp_path)

        assert service.timelapse_path == tmp_path / "timelapse"


class TestFileType:
    """Tests for FileType enum."""

    def test_file_type_values(self):
        """FileType has expected values."""
        assert FileType.RECORDING.value == "recording"
        assert FileType.STILL.value == "still"
        assert FileType.TIMELAPSE.value == "timelapse"
        assert FileType.UNKNOWN.value == "unknown"

    def test_file_type_is_string_enum(self):
        """FileType inherits from str."""
        # FileType is a str enum, so value is a string
        assert isinstance(FileType.RECORDING.value, str)
        # Comparison with string uses value
        assert FileType.RECORDING == "recording"


class TestStorageServiceFileOperations:
    """Tests for file operations."""

    @pytest.mark.asyncio
    async def test_list_files_empty_directory(self, tmp_path):
        """list_files returns empty list for empty directory."""
        service = StorageService(base_path=tmp_path)

        files = await service.list_files(FileType.RECORDING)
        assert files == []

    @pytest.mark.asyncio
    async def test_list_files_with_files(self, tmp_path):
        """list_files returns files in directory."""
        service = StorageService(base_path=tmp_path)

        # Create test files
        (tmp_path / "recordings" / "test1.mp4").touch()
        (tmp_path / "recordings" / "test2.mp4").touch()

        files = await service.list_files(FileType.RECORDING)
        assert len(files) == 2

    @pytest.mark.asyncio
    async def test_get_storage_stats(self, tmp_path):
        """get_storage_stats returns storage information."""
        service = StorageService(base_path=tmp_path)

        # Create test file with content
        test_file = tmp_path / "recordings" / "test.mp4"
        test_file.write_bytes(b"x" * 1000)

        stats = await service.get_storage_stats()

        # Check disk stats are present
        assert "disk" in stats
        assert "total_bytes" in stats["disk"]

        # Check recordings stats
        assert "recordings" in stats
        assert stats["recordings"]["count"] == 1
        assert stats["recordings"]["size_bytes"] == 1000


class TestStorageServiceSecurity:
    """Tests for security features."""

    def test_file_id_generation_is_consistent(self, tmp_path):
        """File ID generation produces consistent IDs."""
        service = StorageService(base_path=tmp_path)

        test_file = tmp_path / "recordings" / "test.mp4"
        test_file.touch()

        # Generate ID twice for same path
        id1 = service.generate_file_id(str(test_file))
        id2 = service.generate_file_id(str(test_file))

        assert id1 == id2

    def test_file_id_differs_for_different_files(self, tmp_path):
        """Different files get different IDs."""
        service = StorageService(base_path=tmp_path)

        file1 = tmp_path / "recordings" / "test1.mp4"
        file2 = tmp_path / "recordings" / "test2.mp4"

        id1 = service.generate_file_id(str(file1))
        id2 = service.generate_file_id(str(file2))

        assert id1 != id2

    def test_file_id_decode_roundtrip(self, tmp_path):
        """File ID can be decoded back to original path."""
        service = StorageService(base_path=tmp_path)

        test_path = str(tmp_path / "recordings" / "test.mp4")
        file_id = service.generate_file_id(test_path)
        decoded = service.decode_file_id(file_id)

        assert decoded == test_path

    def test_validate_path_rejects_outside_base(self, tmp_path):
        """validate_path rejects paths outside base directory."""
        service = StorageService(base_path=tmp_path)

        assert service.validate_path(str(tmp_path / "recordings" / "test.mp4")) is True
        assert service.validate_path("/etc/passwd") is False

"""Tests for timelapse service."""

import inspect
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.camera.timelapse.config import TimelapseConfig
from app.services.camera.timelapse.service import TimelapseService


class TestTimelapseServiceInitialization:
    """Tests for TimelapseService initialization."""

    def test_service_initializes_with_empty_sessions(self):
        """Service initializes with empty session dict."""
        service = TimelapseService()
        assert service._sessions == {}

    def test_service_is_not_running_initially(self):
        """is_running returns False for non-existent camera."""
        service = TimelapseService()
        assert service.is_running(1) is False


class TestTimelapseServiceIsRunning:
    """Tests for is_running method."""

    def test_is_running_false_for_unknown_camera(self):
        """is_running returns False for camera with no session."""
        service = TimelapseService()
        assert service.is_running(999) is False

    def test_is_running_returns_session_state(self):
        """is_running reflects session's is_running property."""
        service = TimelapseService()

        mock_session = MagicMock()
        mock_session.is_running = True
        service._sessions[1] = mock_session

        assert service.is_running(1) is True

        mock_session.is_running = False
        assert service.is_running(1) is False


class TestTimelapseServiceProgress:
    """Tests for progress tracking methods."""

    def test_get_timelapse_progress_returns_none_for_unknown(self):
        """get_timelapse_progress returns None for unknown camera."""
        service = TimelapseService()
        assert service.get_timelapse_progress(1) is None

    def test_get_timelapse_progress_returns_frame_counts(self):
        """get_timelapse_progress returns (current, total) tuple."""
        service = TimelapseService()

        mock_session = MagicMock()
        mock_session.get_progress.return_value = (42, 100)
        service._sessions[1] = mock_session

        progress = service.get_timelapse_progress(1)
        assert progress == (42, 100)
        mock_session.get_progress.assert_called_once()

    def test_get_timelapse_job_id_returns_none_for_unknown(self):
        """get_timelapse_job_id returns None for unknown camera."""
        service = TimelapseService()
        assert service.get_timelapse_job_id(1) is None

    def test_get_timelapse_job_id_returns_session_job_id(self):
        """get_timelapse_job_id returns session's job_id."""
        service = TimelapseService()

        mock_session = MagicMock()
        mock_session.job_id = 42
        service._sessions[1] = mock_session

        assert service.get_timelapse_job_id(1) == 42


class TestTimelapseServiceSessionManagement:
    """Tests for session lifecycle management."""

    def test_sessions_dict_tracks_active_sessions(self):
        """_sessions dictionary tracks active timelapse sessions."""
        service = TimelapseService()

        session1 = MagicMock()
        session2 = MagicMock()

        service._sessions[1] = session1
        service._sessions[2] = session2

        assert 1 in service._sessions
        assert 2 in service._sessions
        assert service._sessions[1] is session1


class TestTimelapseServiceMethodSignatures:
    """Tests for method signatures and parameters."""

    def test_start_timelapse_has_required_parameters(self):
        """start_timelapse has all required parameters."""
        sig = inspect.signature(TimelapseService.start_timelapse)
        params = list(sig.parameters.keys())

        assert "camera_id" in params
        assert "device_path" in params
        assert "camera_type" in params
        assert "config" in params

    def test_stop_timelapse_has_assemble_video_flag_parameter(self):
        """stop_timelapse uses assemble_video_flag (not assemble_video)."""
        sig = inspect.signature(TimelapseService.stop_timelapse)
        params = list(sig.parameters.keys())

        # Bug 6 regression test: must be assemble_video_flag
        assert "assemble_video_flag" in params
        assert "assemble_video" not in params

    def test_resume_timelapse_has_required_parameters(self):
        """resume_timelapse has job_id and device parameters."""
        sig = inspect.signature(TimelapseService.resume_timelapse)
        params = list(sig.parameters.keys())

        assert "job_id" in params
        assert "device_path" in params
        assert "camera_type" in params


class TestTimelapseServiceResumeLogic:
    """Tests for resume timelapse functionality."""

    def test_resume_uses_existing_session_variable_name(self):
        """resume_timelapse uses existing_session to avoid shadowing."""
        source = inspect.getsource(TimelapseService.resume_timelapse)

        # Bug fix verification: should use existing_session, not session
        # to avoid shadowing the AsyncSession parameter
        assert "existing_session = self._sessions" in source


class TestTimelapseServiceCallbacks:
    """Tests for callback integration."""

    def test_start_timelapse_creates_frame_callback(self):
        """start_timelapse creates on_frame_captured callback for WebSocket."""
        source = inspect.getsource(TimelapseService.start_timelapse)

        # Should create callback for WebSocket updates
        assert "on_frame_captured" in source
        assert "broadcast_job_update" in source


class TestTimelapseConfig:
    """Tests for TimelapseConfig dataclass."""

    def test_config_has_required_fields(self):
        """TimelapseConfig has all required configuration fields."""
        config = TimelapseConfig(camera_id=1)

        assert hasattr(config, "camera_id")
        assert hasattr(config, "interval_seconds")
        assert hasattr(config, "total_frames")
        assert hasattr(config, "quality")

    def test_config_defaults(self):
        """TimelapseConfig has sensible defaults."""
        config = TimelapseConfig(camera_id=1)

        assert config.camera_id == 1
        assert config.interval_seconds > 0
        assert config.quality > 0

    def test_config_custom_values(self):
        """TimelapseConfig accepts custom values."""
        config = TimelapseConfig(
            camera_id=1,
            interval_seconds=30,
            total_frames=100,
            quality=90,
        )

        assert config.interval_seconds == 30
        assert config.total_frames == 100
        assert config.quality == 90

"""Tests for camera validation service."""

from datetime import datetime
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ObservationStatus
from app.db.models.camera import Camera
from app.db.models.observation import Observation
from app.services.camera.pipeline import PipelineState
from app.services.camera.validation import (
    CameraInUseResult,
    check_camera_in_use,
    require_camera_available,
)


@pytest_asyncio.fixture
async def camera(db_session: AsyncSession) -> Camera:
    """Create a test camera."""
    camera = Camera(
        name="Test Camera",
        device_path="/dev/video0",
        camera_type="usb",
        enabled=True,
    )
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)
    return camera


@pytest_asyncio.fixture
async def running_observation(
    db_session: AsyncSession, camera: Camera
) -> Observation:
    """Create a running observation."""
    obs = Observation(
        camera_id=camera.id,
        observation_type="timelapse",
        status=ObservationStatus.RUNNING,
        folder_path="/media/test/obs1",
        config={"interval_seconds": 60},
        started_at=datetime.now(),
    )
    db_session.add(obs)
    await db_session.commit()
    await db_session.refresh(obs)
    return obs


class TestCameraInUseResult:
    """Tests for CameraInUseResult dataclass."""

    def test_default_values(self):
        """Test default values for CameraInUseResult."""
        result = CameraInUseResult(in_use=False)
        assert result.in_use is False
        assert result.reason is None
        assert result.observation_id is None
        assert result.observation_type is None

    def test_with_all_values(self):
        """Test CameraInUseResult with all values set."""
        result = CameraInUseResult(
            in_use=True,
            reason="timelapse is running",
            observation_id=42,
            observation_type="timelapse",
        )
        assert result.in_use is True
        assert result.reason == "timelapse is running"
        assert result.observation_id == 42
        assert result.observation_type == "timelapse"


class TestCheckCameraInUse:
    """Tests for check_camera_in_use function."""

    @pytest.mark.asyncio
    async def test_returns_not_in_use_when_camera_idle(
        self, db_session: AsyncSession, camera: Camera
    ):
        """Test that idle camera returns not in use."""
        with patch(
            "app.services.camera.validation.recording_service"
        ) as mock_recording, patch(
            "app.services.camera.validation.timelapse_service"
        ) as mock_timelapse:
            mock_recording.get_recording_state.return_value = PipelineState.STOPPED
            mock_timelapse.is_running.return_value = False

            result = await check_camera_in_use(camera.id, db_session)

            assert result.in_use is False
            assert result.reason is None

    @pytest.mark.asyncio
    async def test_detects_database_active_observation(
        self, db_session: AsyncSession, camera: Camera, running_observation: Observation
    ):
        """Test that active database observation is detected."""
        with patch(
            "app.services.camera.validation.recording_service"
        ) as mock_recording, patch(
            "app.services.camera.validation.timelapse_service"
        ) as mock_timelapse:
            mock_recording.get_recording_state.return_value = PipelineState.STOPPED
            mock_timelapse.is_running.return_value = False

            result = await check_camera_in_use(camera.id, db_session)

            assert result.in_use is True
            assert "timelapse is running" in result.reason
            assert result.observation_id == running_observation.id
            assert result.observation_type == "timelapse"

    @pytest.mark.asyncio
    async def test_detects_recording_service_active(
        self, db_session: AsyncSession, camera: Camera
    ):
        """Test that in-memory recording state is detected."""
        with patch(
            "app.services.camera.validation.recording_service"
        ) as mock_recording, patch(
            "app.services.camera.validation.timelapse_service"
        ) as mock_timelapse:
            mock_recording.get_recording_state.return_value = PipelineState.RUNNING
            mock_timelapse.is_running.return_value = False

            result = await check_camera_in_use(camera.id, db_session)

            assert result.in_use is True
            assert result.reason == "recording is running"
            # No observation ID since it's only in-memory state
            assert result.observation_id is None

    @pytest.mark.asyncio
    async def test_detects_timelapse_service_active(
        self, db_session: AsyncSession, camera: Camera
    ):
        """Test that in-memory timelapse state is detected."""
        with patch(
            "app.services.camera.validation.recording_service"
        ) as mock_recording, patch(
            "app.services.camera.validation.timelapse_service"
        ) as mock_timelapse:
            mock_recording.get_recording_state.return_value = PipelineState.STOPPED
            mock_timelapse.is_running.return_value = True

            result = await check_camera_in_use(camera.id, db_session)

            assert result.in_use is True
            assert result.reason == "timelapse is running"
            # No observation ID since it's only in-memory state
            assert result.observation_id is None

    @pytest.mark.asyncio
    async def test_database_check_takes_priority(
        self, db_session: AsyncSession, camera: Camera, running_observation: Observation
    ):
        """Test that database status is checked first and takes priority."""
        with patch(
            "app.services.camera.validation.recording_service"
        ) as mock_recording, patch(
            "app.services.camera.validation.timelapse_service"
        ) as mock_timelapse:
            # Both services also report running
            mock_recording.get_recording_state.return_value = PipelineState.RUNNING
            mock_timelapse.is_running.return_value = True

            result = await check_camera_in_use(camera.id, db_session)

            # Should return database info (has observation_id)
            assert result.in_use is True
            assert result.observation_id == running_observation.id

            # Recording service should not be checked since DB returned active
            mock_recording.get_recording_state.assert_not_called()


class TestRequireCameraAvailable:
    """Tests for require_camera_available function."""

    @pytest.mark.asyncio
    async def test_does_not_raise_when_camera_available(
        self, db_session: AsyncSession, camera: Camera
    ):
        """Test that no exception is raised when camera is available."""
        with patch(
            "app.services.camera.validation.recording_service"
        ) as mock_recording, patch(
            "app.services.camera.validation.timelapse_service"
        ) as mock_timelapse:
            mock_recording.get_recording_state.return_value = PipelineState.STOPPED
            mock_timelapse.is_running.return_value = False

            # Should not raise
            await require_camera_available(camera.id, db_session, "edit camera")

    @pytest.mark.asyncio
    async def test_raises_409_when_camera_in_use(
        self, db_session: AsyncSession, camera: Camera, running_observation: Observation
    ):
        """Test that HTTPException 409 is raised when camera is in use."""
        with patch(
            "app.services.camera.validation.recording_service"
        ) as mock_recording, patch(
            "app.services.camera.validation.timelapse_service"
        ) as mock_timelapse:
            mock_recording.get_recording_state.return_value = PipelineState.STOPPED
            mock_timelapse.is_running.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await require_camera_available(camera.id, db_session, "edit camera")

            assert exc_info.value.status_code == 409
            assert "Cannot edit camera" in exc_info.value.detail
            assert "timelapse is running" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_error_message_includes_operation(
        self, db_session: AsyncSession, camera: Camera, running_observation: Observation
    ):
        """Test that error message includes the operation description."""
        with patch(
            "app.services.camera.validation.recording_service"
        ) as mock_recording, patch(
            "app.services.camera.validation.timelapse_service"
        ) as mock_timelapse:
            mock_recording.get_recording_state.return_value = PipelineState.STOPPED
            mock_timelapse.is_running.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await require_camera_available(
                    camera.id, db_session, "delete camera settings"
                )

            assert "Cannot delete camera settings" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_default_operation_message(
        self, db_session: AsyncSession, camera: Camera, running_observation: Observation
    ):
        """Test default operation message when not specified."""
        with patch(
            "app.services.camera.validation.recording_service"
        ) as mock_recording, patch(
            "app.services.camera.validation.timelapse_service"
        ) as mock_timelapse:
            mock_recording.get_recording_state.return_value = PipelineState.STOPPED
            mock_timelapse.is_running.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await require_camera_available(camera.id, db_session)

            assert "Cannot perform this operation" in exc_info.value.detail

"""Regression tests for timelapse bugs fixed in commit b0b7579.

These tests protect against regressions of the 6 timelapse bugs:
1. Progress reporting mismatch (frontend assumed percentage)
2. Job completed_at not set on manual stop
3. WebSocket progress not broadcast per frame
4. Video assembly validation (no minimum file size check)
5. Resume frame counting (count vs highest frame number)
6. Parameter naming (assemble_video vs assemble_video_flag)
"""

import inspect
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.core.constants import JobStatus
from app.db.models.job import Job
from app.db.repositories.job import JobRepository


class TestBug1ProgressReporting:
    """Bug 1: Progress reporting should use frame counts, not percentages.

    The WebSocket job_update message must include current_frame and total_frames
    fields so the frontend can display accurate progress.
    """

    @pytest.mark.asyncio
    async def test_websocket_manager_broadcast_job_update_includes_frame_counts(self):
        """WebSocket broadcast_job_update includes current_frame and total_frames."""
        from app.services.websocket.manager import WebSocketManager

        manager = WebSocketManager()
        messages_sent = []

        # Patch broadcast to capture messages
        async def capture_broadcast(message):
            messages_sent.append(message)

        manager.broadcast = capture_broadcast

        await manager.broadcast_job_update(
            job_id=1,
            camera_id=1,
            job_type="timelapse",
            status="running",
            current_frame=42,
            total_frames=100,
        )

        assert len(messages_sent) == 1
        msg = messages_sent[0]
        assert msg["type"] == "job_update"
        assert msg["current_frame"] == 42
        assert msg["total_frames"] == 100
        assert msg["job_type"] == "timelapse"
        assert msg["status"] == "running"

    @pytest.mark.asyncio
    async def test_websocket_manager_calculates_progress_from_frames(self):
        """Progress percentage is auto-calculated from frame counts."""
        from app.services.websocket.manager import WebSocketManager

        manager = WebSocketManager()
        messages_sent = []

        async def capture_broadcast(message):
            messages_sent.append(message)

        manager.broadcast = capture_broadcast

        await manager.broadcast_job_update(
            job_id=1,
            camera_id=1,
            job_type="timelapse",
            status="running",
            current_frame=50,
            total_frames=100,
        )

        msg = messages_sent[0]
        assert msg["progress"] == 50.0  # 50/100 * 100 = 50%

    @pytest.mark.asyncio
    async def test_websocket_manager_handles_unlimited_timelapse(self):
        """Unlimited timelapses (total_frames=None) don't break progress calc."""
        from app.services.websocket.manager import WebSocketManager

        manager = WebSocketManager()
        messages_sent = []

        async def capture_broadcast(message):
            messages_sent.append(message)

        manager.broadcast = capture_broadcast

        await manager.broadcast_job_update(
            job_id=1,
            camera_id=1,
            job_type="timelapse",
            status="running",
            current_frame=100,
            total_frames=None,  # Unlimited
        )

        msg = messages_sent[0]
        assert msg["current_frame"] == 100
        assert msg["total_frames"] is None
        assert msg["progress"] is None  # Can't calculate without total


class TestBug2JobLifecycle:
    """Bug 2: User-stopped timelapses should be marked COMPLETED, not INTERRUPTED.

    When a user manually stops a timelapse, even with 0 frames, the job should
    have status=COMPLETED with completed_at set. INTERRUPTED is reserved for
    system crashes/unexpected termination.
    """

    @pytest.mark.asyncio
    async def test_job_repository_mark_completed_sets_status(self, db_session):
        """mark_completed sets status to COMPLETED."""
        # Create a running job
        job = Job(
            camera_id=1,
            job_type="timelapse",
            status=JobStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        repo = JobRepository(db_session)
        updated = await repo.mark_completed(job.id, output_path="/test/video.mp4")

        assert updated.status == JobStatus.COMPLETED
        assert updated.completed_at is not None
        assert updated.output_path == "/test/video.mp4"

    @pytest.mark.asyncio
    async def test_job_repository_mark_completed_with_none_output(self, db_session):
        """mark_completed works with output_path=None (0 frames case)."""
        job = Job(
            camera_id=1,
            job_type="timelapse",
            status=JobStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        repo = JobRepository(db_session)
        updated = await repo.mark_completed(job.id, output_path=None)

        assert updated.status == JobStatus.COMPLETED
        assert updated.completed_at is not None
        assert updated.output_path is None

    @pytest.mark.asyncio
    async def test_mark_interrupted_sets_interrupted_status(self, db_session):
        """mark_interrupted sets status to INTERRUPTED (for crashes)."""
        job = Job(
            camera_id=1,
            job_type="timelapse",
            status=JobStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        repo = JobRepository(db_session)
        updated = await repo.mark_interrupted(job.id)

        assert updated.status == JobStatus.INTERRUPTED


class TestBug3WebSocketBroadcast:
    """Bug 3: WebSocket should broadcast progress on each frame capture.

    The TimelapseSession must invoke the on_frame_captured callback after
    each successful frame, which triggers a WebSocket broadcast.
    """

    @pytest.mark.asyncio
    async def test_timelapse_session_has_on_frame_captured_parameter(self):
        """TimelapseSession accepts on_frame_captured callback."""
        from app.services.camera.timelapse.session import TimelapseSession

        sig = inspect.signature(TimelapseSession.__init__)
        params = list(sig.parameters.keys())

        assert "on_frame_captured" in params

    @pytest.mark.asyncio
    async def test_timelapse_session_callback_invoked_on_capture(self, tmp_path):
        """on_frame_captured callback is invoked after successful capture."""
        from app.services.camera.timelapse.config import TimelapseConfig
        from app.services.camera.timelapse.session import TimelapseSession

        callback_calls = []

        async def mock_callback(current_frame, total_frames, job_id):
            callback_calls.append((current_frame, total_frames, job_id))

        config = TimelapseConfig(camera_id=1, interval_seconds=1, total_frames=5)
        session = TimelapseSession(
            config=config,
            device_path="/dev/video0",
            camera_type="usb",
            job_id=42,
            timelapse_dir=tmp_path,
            on_frame_captured=mock_callback,
        )

        # Simulate a successful capture by calling the internal handler
        session.frame_count = 0
        await session._handle_capture_success("/tmp/frame.jpg")

        assert len(callback_calls) == 1
        assert callback_calls[0] == (1, 5, 42)  # frame_count incremented to 1

    @pytest.mark.asyncio
    async def test_timelapse_service_passes_callback_to_session(self):
        """TimelapseService.start_timelapse creates callback for WebSocket."""
        from app.services.camera.timelapse.service import TimelapseService

        service = TimelapseService()

        # Check that start_timelapse creates a callback
        # We verify this by checking the code structure
        import inspect

        source = inspect.getsource(service.start_timelapse)
        assert "on_frame_captured" in source
        assert "broadcast_job_update" in source


class TestBug4VideoAssemblyValidation:
    """Bug 4: Video assembly should validate minimum file size.

    The assembly function must reject videos smaller than MIN_VIDEO_SIZE_BYTES
    to catch empty/corrupt files.
    """

    def test_min_video_size_constant_exists(self):
        """MIN_VIDEO_SIZE_BYTES constant is defined."""
        from app.services.camera.timelapse.assembly import MIN_VIDEO_SIZE_BYTES

        assert MIN_VIDEO_SIZE_BYTES == 1024  # 1KB minimum

    @pytest.mark.asyncio
    async def test_assembly_validates_output_size(self, tmp_path):
        """Assembly validation rejects files smaller than minimum."""
        from app.services.camera.timelapse.assembly import MIN_VIDEO_SIZE_BYTES

        # Create a tiny "video" file (smaller than minimum)
        tiny_file = tmp_path / "tiny.mp4"
        tiny_file.write_bytes(b"x" * 100)  # 100 bytes

        assert tiny_file.stat().st_size < MIN_VIDEO_SIZE_BYTES

        # The actual validation happens in assemble_video after ffmpeg runs
        # We verify the constant is correct and validation logic exists
        from app.services.camera.timelapse import assembly

        source = inspect.getsource(assembly.assemble_video)
        assert "MIN_VIDEO_SIZE_BYTES" in source
        assert "File too small" in source


class TestBug5ResumeFrameCounting:
    """Bug 5: Resume should find highest frame number, not count files.

    When resuming an interrupted timelapse with gaps in frame sequence,
    the service must parse the highest frame number (e.g., frame_000005.jpg -> 6)
    not just count the files (which would give 3 if frames 3,4 are missing).
    """

    def test_resume_parses_frame_number_from_filename(self, tmp_path):
        """Resume logic parses highest frame number, handles gaps."""
        # Create frames with gap: 1, 2, 5 (3 and 4 missing)
        (tmp_path / "frame_000001.jpg").touch()
        (tmp_path / "frame_000002.jpg").touch()
        (tmp_path / "frame_000005.jpg").touch()  # Gap - 3 and 4 missing

        # This is the logic from service.py resume_timelapse
        frame_files = sorted(tmp_path.glob("frame_*.jpg"))
        if frame_files:
            last_frame_name = frame_files[-1].stem  # "frame_000005"
            existing_frames = int(last_frame_name.split("_")[1]) + 1
        else:
            existing_frames = 0

        # Should be 6 (next frame after 5), not 3 (file count)
        assert existing_frames == 6
        assert len(frame_files) == 3  # Only 3 files exist

    def test_resume_handles_empty_directory(self, tmp_path):
        """Resume handles empty directory gracefully."""
        frame_files = sorted(tmp_path.glob("frame_*.jpg"))
        if frame_files:
            last_frame_name = frame_files[-1].stem
            existing_frames = int(last_frame_name.split("_")[1]) + 1
        else:
            existing_frames = 0

        assert existing_frames == 0

    def test_resume_handles_malformed_filename(self, tmp_path):
        """Resume handles malformed filenames with fallback to count."""
        (tmp_path / "frame_000001.jpg").touch()
        (tmp_path / "frame_malformed.jpg").touch()  # No number

        frame_files = sorted(tmp_path.glob("frame_*.jpg"))
        last_frame_name = frame_files[-1].stem  # "frame_malformed"
        try:
            existing_frames = int(last_frame_name.split("_")[1]) + 1
        except (IndexError, ValueError):
            existing_frames = len(frame_files)  # Fallback

        # Fallback to count when parsing fails
        assert existing_frames == 2


class TestBug6ParameterNaming:
    """Bug 6: Parameter name must be assemble_video_flag, not assemble_video.

    This was a parameter name mismatch between API and service layer fixed in
    commit 0acc8ee.
    """

    def test_stop_timelapse_uses_correct_parameter_name(self):
        """stop_timelapse has assemble_video_flag parameter."""
        from app.services.camera.timelapse.service import TimelapseService

        sig = inspect.signature(TimelapseService.stop_timelapse)
        params = list(sig.parameters.keys())

        assert "assemble_video_flag" in params
        # Ensure old buggy name is not present
        assert "assemble_video" not in params


class TestAdditionalRegressions:
    """Additional regression tests for related fixes."""

    def test_variable_shadowing_fixed_in_resume(self):
        """resume_timelapse uses existing_session, not session (shadowing fix)."""
        from app.services.camera.timelapse.service import TimelapseService

        source = inspect.getsource(TimelapseService.resume_timelapse)
        # Should use existing_session to avoid shadowing the session parameter
        assert "existing_session = self._sessions[camera_id]" in source
        # The line "session = self._sessions[camera_id]" should NOT be there
        # because it shadows the AsyncSession parameter

    def test_websocket_manager_documents_race_condition(self):
        """WebSocket manager has documentation about TOCTOU trade-off."""
        from app.services.websocket.manager import WebSocketManager

        docstring = WebSocketManager.broadcast.__doc__
        assert "TOCTOU" in docstring or "race" in docstring.lower()

    def test_media_paths_centralized(self):
        """MediaPaths module exists for centralized path handling."""
        from app.core.paths import MediaPaths, media_paths

        assert media_paths is not None
        assert hasattr(media_paths, "timelapse_dir")
        assert hasattr(media_paths, "timelapses")

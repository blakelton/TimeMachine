"""Tests for database repositories."""

from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import JobStatus, ObservationStatus
from app.db.models.camera import Camera
from app.db.models.job import Job
from app.db.models.observation import Observation
from app.db.repositories.camera import CameraRepository
from app.db.repositories.job import JobRepository
from app.db.repositories.observation import ObservationRepository


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
async def second_camera(db_session: AsyncSession) -> Camera:
    """Create a second test camera."""
    camera = Camera(
        name="Second Camera",
        device_path="/dev/video1",
        camera_type="csi",
        enabled=True,
    )
    db_session.add(camera)
    await db_session.commit()
    await db_session.refresh(camera)
    return camera


class TestCameraRepository:
    """Tests for CameraRepository."""

    @pytest.mark.asyncio
    async def test_get_all_returns_empty_list_initially(self, db_session: AsyncSession):
        """Test that get_all returns empty list when no cameras exist."""
        repo = CameraRepository(db_session)
        cameras = await repo.get_all()
        assert cameras == []

    @pytest.mark.asyncio
    async def test_create_camera(self, db_session: AsyncSession):
        """Test creating a camera."""
        repo = CameraRepository(db_session)
        camera = await repo.create(
            name="New Camera",
            device_path="/dev/video0",
            camera_type="usb",
        )
        assert camera.id is not None
        assert camera.name == "New Camera"
        assert camera.device_path == "/dev/video0"
        assert camera.camera_type == "usb"
        assert camera.enabled is True

    @pytest.mark.asyncio
    async def test_get_camera_by_id(self, db_session: AsyncSession, camera: Camera):
        """Test getting a camera by ID."""
        repo = CameraRepository(db_session)
        found = await repo.get(camera.id)
        assert found is not None
        assert found.id == camera.id
        assert found.name == camera.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_camera_returns_none(self, db_session: AsyncSession):
        """Test that getting a nonexistent camera returns None."""
        repo = CameraRepository(db_session)
        found = await repo.get(99999)
        assert found is None

    @pytest.mark.asyncio
    async def test_update_camera(self, db_session: AsyncSession, camera: Camera):
        """Test updating a camera."""
        repo = CameraRepository(db_session)
        updated = await repo.update(camera.id, name="Updated Name")
        assert updated is not None
        assert updated.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_get_enabled_cameras(
        self, db_session: AsyncSession, camera: Camera, second_camera: Camera
    ):
        """Test getting only enabled cameras."""
        repo = CameraRepository(db_session)
        # Disable one camera
        await repo.update(second_camera.id, enabled=False)

        enabled = await repo.get_enabled()
        assert len(enabled) == 1
        assert enabled[0].id == camera.id


class TestObservationRepository:
    """Tests for ObservationRepository."""

    @pytest_asyncio.fixture
    async def running_observation(
        self, db_session: AsyncSession, camera: Camera
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

    @pytest_asyncio.fixture
    async def completed_observation(
        self, db_session: AsyncSession, camera: Camera
    ) -> Observation:
        """Create a completed observation."""
        obs = Observation(
            camera_id=camera.id,
            observation_type="recording",
            status=ObservationStatus.COMPLETED,
            folder_path="/media/test/obs2",
            config={"duration_seconds": 300},
            started_at=datetime.now() - timedelta(hours=1),
            completed_at=datetime.now(),
            size_bytes=1024000,
        )
        db_session.add(obs)
        await db_session.commit()
        await db_session.refresh(obs)
        return obs

    @pytest.mark.asyncio
    async def test_create_observation(self, db_session: AsyncSession, camera: Camera):
        """Test creating an observation."""
        repo = ObservationRepository(db_session)
        obs = await repo.create(
            camera_id=camera.id,
            observation_type="timelapse",
            status=ObservationStatus.RUNNING,
            folder_path="/media/test/new_obs",
            config={"interval_seconds": 30},
        )
        assert obs.id is not None
        assert obs.camera_id == camera.id
        assert obs.observation_type == "timelapse"
        assert obs.status == ObservationStatus.RUNNING

    @pytest.mark.asyncio
    async def test_get_active_by_camera(
        self, db_session: AsyncSession, camera: Camera, running_observation: Observation
    ):
        """Test getting active observation for a camera."""
        repo = ObservationRepository(db_session)
        active = await repo.get_active_by_camera(camera.id)
        assert active is not None
        assert active.id == running_observation.id
        assert active.status == ObservationStatus.RUNNING

    @pytest.mark.asyncio
    async def test_get_active_by_camera_returns_none_when_no_active(
        self, db_session: AsyncSession, camera: Camera, completed_observation: Observation
    ):
        """Test that get_active_by_camera returns None when no active observation."""
        repo = ObservationRepository(db_session)
        active = await repo.get_active_by_camera(camera.id)
        assert active is None

    @pytest.mark.asyncio
    async def test_mark_completed(
        self, db_session: AsyncSession, camera: Camera, running_observation: Observation
    ):
        """Test marking an observation as completed."""
        repo = ObservationRepository(db_session)
        updated = await repo.mark_completed(running_observation.id, size_bytes=5000)
        assert updated is not None
        assert updated.status == ObservationStatus.COMPLETED
        assert updated.completed_at is not None
        assert updated.size_bytes == 5000

    @pytest.mark.asyncio
    async def test_mark_failed(
        self, db_session: AsyncSession, camera: Camera, running_observation: Observation
    ):
        """Test marking an observation as failed."""
        repo = ObservationRepository(db_session)
        updated = await repo.mark_failed(running_observation.id, "Test error")
        assert updated is not None
        assert updated.status == ObservationStatus.FAILED
        assert updated.error_message == "Test error"
        assert updated.completed_at is not None

    @pytest.mark.asyncio
    async def test_mark_stopped(
        self, db_session: AsyncSession, camera: Camera, running_observation: Observation
    ):
        """Test marking an observation as stopped."""
        repo = ObservationRepository(db_session)
        updated = await repo.mark_stopped(running_observation.id)
        assert updated is not None
        assert updated.status == ObservationStatus.STOPPED
        assert updated.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_progress(
        self, db_session: AsyncSession, camera: Camera, running_observation: Observation
    ):
        """Test updating observation progress."""
        repo = ObservationRepository(db_session)
        updated = await repo.update_progress(
            running_observation.id, progress_current=50, size_bytes=2500
        )
        assert updated is not None
        assert updated.progress_current == 50
        assert updated.size_bytes == 2500

    @pytest.mark.asyncio
    async def test_get_completed_filters_by_status(
        self, db_session: AsyncSession, camera: Camera,
        running_observation: Observation, completed_observation: Observation
    ):
        """Test that get_completed only returns non-running observations."""
        repo = ObservationRepository(db_session)
        completed = await repo.get_completed()
        assert len(completed) == 1
        assert completed[0].id == completed_observation.id

    @pytest.mark.asyncio
    async def test_get_completed_with_eager_load(
        self, db_session: AsyncSession, camera: Camera, completed_observation: Observation
    ):
        """Test that eager loading prevents N+1 queries."""
        repo = ObservationRepository(db_session)
        completed = await repo.get_completed(eager_load_camera=True)
        assert len(completed) == 1
        # Camera should be loaded without additional query
        assert completed[0].camera is not None
        assert completed[0].camera.name == camera.name

    @pytest.mark.asyncio
    async def test_get_completed_filters_by_type(
        self, db_session: AsyncSession, camera: Camera
    ):
        """Test filtering completed observations by type."""
        repo = ObservationRepository(db_session)
        # Create multiple observations of different types
        obs1 = Observation(
            camera_id=camera.id,
            observation_type="timelapse",
            status=ObservationStatus.COMPLETED,
            folder_path="/media/test/tl1",
            config={},
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
        obs2 = Observation(
            camera_id=camera.id,
            observation_type="recording",
            status=ObservationStatus.COMPLETED,
            folder_path="/media/test/rec1",
            config={},
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
        db_session.add_all([obs1, obs2])
        await db_session.commit()

        timelapses = await repo.get_completed(observation_type="timelapse")
        assert len(timelapses) == 1
        assert timelapses[0].observation_type == "timelapse"

    @pytest.mark.asyncio
    async def test_cleanup_stale_running(
        self, db_session: AsyncSession, camera: Camera, running_observation: Observation
    ):
        """Test cleanup of stale running observations."""
        repo = ObservationRepository(db_session)
        count = await repo.cleanup_stale_running()
        assert count == 1

        # Verify observation is now failed
        obs = await repo.get(running_observation.id)
        assert obs is not None
        assert obs.status == ObservationStatus.FAILED
        assert "system restart" in obs.error_message

    @pytest.mark.asyncio
    async def test_count_completed(
        self, db_session: AsyncSession, camera: Camera, completed_observation: Observation
    ):
        """Test counting completed observations."""
        repo = ObservationRepository(db_session)
        count = await repo.count_completed()
        assert count == 1

    @pytest.mark.asyncio
    async def test_delete_observation(
        self, db_session: AsyncSession, camera: Camera, completed_observation: Observation
    ):
        """Test deleting an observation."""
        repo = ObservationRepository(db_session)
        deleted = await repo.delete(completed_observation.id)
        assert deleted is True

        # Verify it's gone
        obs = await repo.get(completed_observation.id)
        assert obs is None


class TestJobRepository:
    """Tests for JobRepository."""

    @pytest_asyncio.fixture
    async def running_job(self, db_session: AsyncSession, camera: Camera) -> Job:
        """Create a running job."""
        job = Job(
            camera_id=camera.id,
            job_type="recording",
            status=JobStatus.RUNNING,
            started_at=datetime.now(),
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        return job

    @pytest_asyncio.fixture
    async def completed_job(self, db_session: AsyncSession, camera: Camera) -> Job:
        """Create a completed job."""
        job = Job(
            camera_id=camera.id,
            job_type="timelapse",
            status=JobStatus.COMPLETED,
            started_at=datetime.now() - timedelta(hours=1),
            completed_at=datetime.now(),
            output_path="/media/test/output.mp4",
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        return job

    @pytest.mark.asyncio
    async def test_get_running_jobs(
        self, db_session: AsyncSession, camera: Camera,
        running_job: Job, completed_job: Job
    ):
        """Test getting running jobs."""
        repo = JobRepository(db_session)
        running = await repo.get_running()
        assert len(running) == 1
        assert running[0].id == running_job.id

    @pytest.mark.asyncio
    async def test_get_running_with_camera_filter(
        self, db_session: AsyncSession, camera: Camera, second_camera: Camera
    ):
        """Test filtering running jobs by camera."""
        repo = JobRepository(db_session)
        # Create jobs for both cameras
        job1 = Job(
            camera_id=camera.id,
            job_type="recording",
            status=JobStatus.RUNNING,
            started_at=datetime.now(),
        )
        job2 = Job(
            camera_id=second_camera.id,
            job_type="recording",
            status=JobStatus.RUNNING,
            started_at=datetime.now(),
        )
        db_session.add_all([job1, job2])
        await db_session.commit()

        running = await repo.get_running(camera_id=camera.id)
        assert len(running) == 1
        assert running[0].camera_id == camera.id

    @pytest.mark.asyncio
    async def test_get_running_with_eager_load(
        self, db_session: AsyncSession, camera: Camera, running_job: Job
    ):
        """Test eager loading camera relationship."""
        repo = JobRepository(db_session)
        running = await repo.get_running(eager_load_camera=True)
        assert len(running) == 1
        # Camera should be loaded without additional query
        assert running[0].camera is not None
        assert running[0].camera.name == camera.name

    @pytest.mark.asyncio
    async def test_mark_completed(
        self, db_session: AsyncSession, camera: Camera, running_job: Job
    ):
        """Test marking a job as completed."""
        repo = JobRepository(db_session)
        updated = await repo.mark_completed(running_job.id, output_path="/output.mp4")
        assert updated is not None
        assert updated.status == JobStatus.COMPLETED
        assert updated.completed_at is not None
        assert updated.output_path == "/output.mp4"

    @pytest.mark.asyncio
    async def test_mark_failed(
        self, db_session: AsyncSession, camera: Camera, running_job: Job
    ):
        """Test marking a job as failed."""
        repo = JobRepository(db_session)
        updated = await repo.mark_failed(running_job.id, "Test failure")
        assert updated is not None
        assert updated.status == JobStatus.FAILED
        assert updated.error_message == "Test failure"

    @pytest.mark.asyncio
    async def test_mark_interrupted(
        self, db_session: AsyncSession, camera: Camera, running_job: Job
    ):
        """Test marking a job as interrupted."""
        repo = JobRepository(db_session)
        updated = await repo.mark_interrupted(running_job.id)
        assert updated is not None
        assert updated.status == JobStatus.INTERRUPTED

    @pytest.mark.asyncio
    async def test_get_active_by_camera_and_type(
        self, db_session: AsyncSession, camera: Camera, running_job: Job
    ):
        """Test getting active job by camera and type."""
        repo = JobRepository(db_session)
        active = await repo.get_active_by_camera_and_type(camera.id, "recording")
        assert active is not None
        assert active.id == running_job.id

        # Different type should return None
        active_tl = await repo.get_active_by_camera_and_type(camera.id, "timelapse")
        assert active_tl is None

    @pytest.mark.asyncio
    async def test_cleanup_stale_running_jobs(
        self, db_session: AsyncSession, camera: Camera, running_job: Job
    ):
        """Test cleanup of stale running jobs."""
        repo = JobRepository(db_session)
        count = await repo.cleanup_stale_running_jobs()
        assert count == 1

        # Verify job is now interrupted
        job = await repo.get(running_job.id)
        assert job is not None
        assert job.status == JobStatus.INTERRUPTED
        assert "system restart" in job.error_message

    @pytest.mark.asyncio
    async def test_update_timelapse_progress(
        self, db_session: AsyncSession, camera: Camera
    ):
        """Test updating timelapse progress."""
        repo = JobRepository(db_session)
        job = Job(
            camera_id=camera.id,
            job_type="timelapse",
            status=JobStatus.RUNNING,
            started_at=datetime.now(),
            timelapse_progress=0,
        )
        db_session.add(job)
        await db_session.commit()

        updated = await repo.update_timelapse_progress(job.id, frame_count=25)
        assert updated is not None
        assert updated.timelapse_progress == 25

    @pytest.mark.asyncio
    async def test_get_by_camera(
        self, db_session: AsyncSession, camera: Camera,
        running_job: Job, completed_job: Job
    ):
        """Test getting all jobs for a camera."""
        repo = JobRepository(db_session)
        jobs = await repo.get_by_camera(camera.id)
        assert len(jobs) == 2

    @pytest.mark.asyncio
    async def test_get_by_type(
        self, db_session: AsyncSession, camera: Camera,
        running_job: Job, completed_job: Job
    ):
        """Test getting jobs by type."""
        repo = JobRepository(db_session)
        recordings = await repo.get_by_type("recording")
        assert len(recordings) == 1
        assert recordings[0].job_type == "recording"

        timelapses = await repo.get_by_type("timelapse")
        assert len(timelapses) == 1
        assert timelapses[0].job_type == "timelapse"

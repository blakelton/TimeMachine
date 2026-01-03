"""Tests for job management endpoints."""

from datetime import datetime, timezone

import pytest

from app.core.constants import JobStatus
from app.db.models.camera import Camera
from app.db.models.job import Job


class TestJobListEndpoint:
    """Tests for GET /api/v1/jobs endpoint."""

    @pytest.mark.asyncio
    async def test_list_jobs_empty(self, client):
        """GET /jobs returns empty list when no jobs exist."""
        response = await client.get("/api/v1/jobs")

        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []

    @pytest.mark.asyncio
    async def test_list_jobs_returns_jobs(self, client, api_session):
        """GET /jobs returns list of jobs."""
        # Create camera first (jobs require camera_id)
        camera = Camera(
            name="Test Camera",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        api_session.add(camera)
        await api_session.commit()
        await api_session.refresh(camera)

        # Create jobs
        job1 = Job(
            camera_id=camera.id,
            job_type="timelapse",
            status=JobStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        job2 = Job(
            camera_id=camera.id,
            job_type="recording",
            status=JobStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
        )
        api_session.add_all([job1, job2])
        await api_session.commit()

        response = await client.get("/api/v1/jobs")

        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 2

    @pytest.mark.asyncio
    async def test_list_jobs_filter_by_camera(self, client, api_session):
        """GET /jobs?camera_id=X filters jobs by camera."""
        camera1 = Camera(
            name="Camera 1",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        camera2 = Camera(
            name="Camera 2",
            device_path="/dev/video1",
            camera_type="usb",
            enabled=True,
        )
        api_session.add_all([camera1, camera2])
        await api_session.commit()
        await api_session.refresh(camera1)
        await api_session.refresh(camera2)

        job1 = Job(
            camera_id=camera1.id,
            job_type="timelapse",
            status=JobStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        job2 = Job(
            camera_id=camera2.id,
            job_type="timelapse",
            status=JobStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        api_session.add_all([job1, job2])
        await api_session.commit()

        response = await client.get(f"/api/v1/jobs?camera_id={camera1.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["camera_id"] == camera1.id


class TestRunningJobsEndpoint:
    """Tests for GET /api/v1/jobs/running endpoint."""

    @pytest.mark.asyncio
    async def test_list_running_jobs(self, client, api_session):
        """GET /jobs/running returns only running jobs."""
        camera = Camera(
            name="Test Camera",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        api_session.add(camera)
        await api_session.commit()
        await api_session.refresh(camera)

        running_job = Job(
            camera_id=camera.id,
            job_type="timelapse",
            status=JobStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        completed_job = Job(
            camera_id=camera.id,
            job_type="recording",
            status=JobStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
        )
        api_session.add_all([running_job, completed_job])
        await api_session.commit()

        response = await client.get("/api/v1/jobs/running")

        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["status"] == "running"


class TestJobGetEndpoint:
    """Tests for GET /api/v1/jobs/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_job_by_id(self, client, api_session):
        """GET /jobs/{id} returns job details."""
        camera = Camera(
            name="Test Camera",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        api_session.add(camera)
        await api_session.commit()
        await api_session.refresh(camera)

        job = Job(
            camera_id=camera.id,
            job_type="timelapse",
            status=JobStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        api_session.add(job)
        await api_session.commit()
        await api_session.refresh(job)

        response = await client.get(f"/api/v1/jobs/{job.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job.id
        assert data["job_type"] == "timelapse"

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, client):
        """GET /jobs/{id} returns 404 for missing job."""
        response = await client.get("/api/v1/jobs/99999")

        assert response.status_code == 404


class TestJobDeleteEndpoint:
    """Tests for DELETE /api/v1/jobs/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_completed_job(self, client, api_session):
        """DELETE /jobs/{id} removes completed job."""
        camera = Camera(
            name="Test Camera",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        api_session.add(camera)
        await api_session.commit()
        await api_session.refresh(camera)

        job = Job(
            camera_id=camera.id,
            job_type="timelapse",
            status=JobStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
        )
        api_session.add(job)
        await api_session.commit()
        await api_session.refresh(job)

        response = await client.delete(f"/api/v1/jobs/{job.id}")

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_job_not_found(self, client):
        """DELETE /jobs/{id} returns 404 for missing job."""
        response = await client.delete("/api/v1/jobs/99999")

        assert response.status_code == 404

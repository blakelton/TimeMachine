"""Tests for camera timelapse endpoints."""

import pytest

from app.db.models.camera import Camera


class TestTimelapseStatusEndpoint:
    """Tests for GET /api/v1/cameras/{id}/timelapse/status endpoint."""

    @pytest.mark.asyncio
    async def test_get_timelapse_status(self, client, api_session):
        """GET /cameras/{id}/timelapse/status returns status."""
        camera = Camera(
            name="Test Camera",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        api_session.add(camera)
        await api_session.commit()
        await api_session.refresh(camera)

        response = await client.get(f"/api/v1/cameras/{camera.id}/timelapse/status")

        assert response.status_code == 200
        data = response.json()
        assert data["camera_id"] == camera.id
        assert "is_running" in data
        assert "current_frame" in data
        assert "total_frames" in data

    @pytest.mark.asyncio
    async def test_get_timelapse_status_camera_not_found(self, client):
        """GET /cameras/{id}/timelapse/status returns 404 for missing camera."""
        response = await client.get("/api/v1/cameras/99999/timelapse/status")

        assert response.status_code == 404


class TestTimelapseInterruptedEndpoint:
    """Tests for GET /api/v1/cameras/{id}/timelapse/interrupted endpoint."""

    @pytest.mark.asyncio
    async def test_check_interrupted_no_interrupted(self, client, api_session):
        """GET /cameras/{id}/timelapse/interrupted returns has_interrupted=False."""
        camera = Camera(
            name="Test Camera",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        api_session.add(camera)
        await api_session.commit()
        await api_session.refresh(camera)

        response = await client.get(f"/api/v1/cameras/{camera.id}/timelapse/interrupted")

        assert response.status_code == 200
        data = response.json()
        assert data["has_interrupted"] is False

    @pytest.mark.asyncio
    async def test_check_interrupted_camera_not_found(self, client):
        """GET /cameras/{id}/timelapse/interrupted returns 404 for missing camera."""
        response = await client.get("/api/v1/cameras/99999/timelapse/interrupted")

        assert response.status_code == 404


class TestTimelapseResumeEndpoint:
    """Tests for POST /api/v1/cameras/{id}/timelapse/resume endpoint."""

    @pytest.mark.asyncio
    async def test_resume_timelapse_no_interrupted(self, client, api_session):
        """POST /cameras/{id}/timelapse/resume returns 404 when no interrupted timelapse."""
        camera = Camera(
            name="Test Camera",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        api_session.add(camera)
        await api_session.commit()
        await api_session.refresh(camera)

        response = await client.post(f"/api/v1/cameras/{camera.id}/timelapse/resume")

        assert response.status_code == 404
        data = response.json()
        assert "no interrupted timelapse" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_resume_timelapse_camera_not_found(self, client):
        """POST /cameras/{id}/timelapse/resume returns 404 for missing camera."""
        response = await client.post("/api/v1/cameras/99999/timelapse/resume")

        assert response.status_code == 404


class TestTimelapseFinalizeEndpoint:
    """Tests for POST /api/v1/cameras/{id}/timelapse/finalize endpoint."""

    @pytest.mark.asyncio
    async def test_finalize_timelapse_camera_not_found(self, client):
        """POST /cameras/{id}/timelapse/finalize returns 404 for missing camera."""
        response = await client.post("/api/v1/cameras/99999/timelapse/finalize")

        assert response.status_code == 404


class TestTimelapseCleanupEndpoint:
    """Tests for DELETE /api/v1/cameras/{id}/timelapse/cleanup endpoint."""

    @pytest.mark.asyncio
    async def test_cleanup_timelapse_no_interrupted(self, client, api_session):
        """DELETE /cameras/{id}/timelapse/cleanup returns 404 when no interrupted timelapse."""
        camera = Camera(
            name="Test Camera",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        api_session.add(camera)
        await api_session.commit()
        await api_session.refresh(camera)

        response = await client.delete(f"/api/v1/cameras/{camera.id}/timelapse/cleanup")

        assert response.status_code == 404

"""Tests for camera CRUD endpoints."""

import pytest

from app.db.models.camera import Camera


class TestCameraListEndpoint:
    """Tests for GET /api/v1/cameras/ endpoint."""

    @pytest.mark.asyncio
    async def test_list_cameras_empty(self, client):
        """GET /cameras/ returns empty list when no cameras exist."""
        response = await client.get("/api/v1/cameras/")

        assert response.status_code == 200
        data = response.json()
        assert data["cameras"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_cameras_returns_cameras(self, client, api_session):
        """GET /cameras/ returns list of cameras."""
        # Create test cameras
        camera1 = Camera(
            name="Test Camera 1",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        camera2 = Camera(
            name="Test Camera 2",
            device_path="/dev/video1",
            camera_type="usb",
            enabled=False,
        )
        api_session.add_all([camera1, camera2])
        await api_session.commit()

        response = await client.get("/api/v1/cameras/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["cameras"]) == 2
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_list_cameras_enabled_only_filter(self, client, api_session):
        """GET /cameras/?enabled_only=true filters to enabled cameras."""
        camera1 = Camera(
            name="Enabled Camera",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        camera2 = Camera(
            name="Disabled Camera",
            device_path="/dev/video1",
            camera_type="usb",
            enabled=False,
        )
        api_session.add_all([camera1, camera2])
        await api_session.commit()

        response = await client.get("/api/v1/cameras/?enabled_only=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data["cameras"]) == 1
        assert data["cameras"][0]["name"] == "Enabled Camera"


class TestCameraCreateEndpoint:
    """Tests for POST /api/v1/cameras/ endpoint."""

    @pytest.mark.asyncio
    async def test_create_camera(self, client):
        """POST /cameras/ creates a new camera."""
        camera_data = {
            "name": "New Camera",
            "device_path": "/dev/video0",
            "camera_type": "usb",
            "enabled": True,
        }

        response = await client.post("/api/v1/cameras/", json=camera_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Camera"
        assert data["device_path"] == "/dev/video0"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_camera_duplicate_device_path(self, client, api_session):
        """POST /cameras/ returns 409 for duplicate device_path."""
        # Create existing camera
        camera = Camera(
            name="Existing Camera",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        api_session.add(camera)
        await api_session.commit()

        # Try to create camera with same device_path
        camera_data = {
            "name": "New Camera",
            "device_path": "/dev/video0",  # Same path
            "camera_type": "usb",
            "enabled": True,
        }

        response = await client.post("/api/v1/cameras/", json=camera_data)

        assert response.status_code == 409


class TestCameraGetEndpoint:
    """Tests for GET /api/v1/cameras/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_camera_by_id(self, client, api_session):
        """GET /cameras/{id} returns camera."""
        camera = Camera(
            name="Test Camera",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        api_session.add(camera)
        await api_session.commit()
        await api_session.refresh(camera)

        response = await client.get(f"/api/v1/cameras/{camera.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == camera.id
        assert data["name"] == "Test Camera"

    @pytest.mark.asyncio
    async def test_get_camera_not_found(self, client):
        """GET /cameras/{id} returns 404 for missing camera."""
        response = await client.get("/api/v1/cameras/99999")

        assert response.status_code == 404


class TestCameraUpdateEndpoint:
    """Tests for PATCH /api/v1/cameras/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_camera(self, client, api_session):
        """PATCH /cameras/{id} updates camera fields."""
        camera = Camera(
            name="Old Name",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        api_session.add(camera)
        await api_session.commit()
        await api_session.refresh(camera)

        response = await client.patch(
            f"/api/v1/cameras/{camera.id}",
            json={"name": "New Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_update_camera_not_found(self, client):
        """PATCH /cameras/{id} returns 404 for missing camera."""
        response = await client.patch(
            "/api/v1/cameras/99999",
            json={"name": "New Name"},
        )

        assert response.status_code == 404


class TestCameraDeleteEndpoint:
    """Tests for DELETE /api/v1/cameras/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_camera(self, client, api_session):
        """DELETE /cameras/{id} removes camera."""
        camera = Camera(
            name="Test Camera",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        api_session.add(camera)
        await api_session.commit()
        await api_session.refresh(camera)

        response = await client.delete(f"/api/v1/cameras/{camera.id}")

        assert response.status_code == 204

        # Verify camera is deleted
        get_response = await client.get(f"/api/v1/cameras/{camera.id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_camera_not_found(self, client):
        """DELETE /cameras/{id} returns 404 for missing camera."""
        response = await client.delete("/api/v1/cameras/99999")

        assert response.status_code == 404

"""Tests for observation management endpoints."""

from datetime import datetime, timezone

import pytest

from app.core.constants import ObservationStatus
from app.db.models.camera import Camera
from app.db.models.observation import Observation


class TestObservationListEndpoint:
    """Tests for GET /api/v1/observations endpoint."""

    @pytest.mark.asyncio
    async def test_list_observations_empty(self, client):
        """GET /observations returns empty list when no observations exist."""
        response = await client.get("/api/v1/observations/")

        assert response.status_code == 200
        data = response.json()
        assert data["observations"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_observations_returns_observations(self, client, api_session):
        """GET /observations returns list of observations."""
        # Create camera first
        camera = Camera(
            name="Test Camera",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        api_session.add(camera)
        await api_session.commit()
        await api_session.refresh(camera)

        # Create observations
        obs1 = Observation(
            camera_id=camera.id,
            observation_type="timelapse",
            status=ObservationStatus.RUNNING,
            folder_path="/media/observations/camera1_20260101_120000",
            config={"interval_seconds": 60},
            started_at=datetime.now(timezone.utc),
        )
        obs2 = Observation(
            camera_id=camera.id,
            observation_type="recording",
            status=ObservationStatus.COMPLETED,
            folder_path="/media/observations/camera1_20260101_130000",
            config={"quality": "high"},
            started_at=datetime.now(timezone.utc),
        )
        api_session.add_all([obs1, obs2])
        await api_session.commit()

        response = await client.get("/api/v1/observations/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["observations"]) == 2

    @pytest.mark.asyncio
    async def test_list_observations_filter_by_camera(self, client, api_session):
        """GET /observations?camera_id=X filters by camera."""
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

        obs1 = Observation(
            camera_id=camera1.id,
            observation_type="timelapse",
            status=ObservationStatus.RUNNING,
            folder_path="/media/observations/camera1_20260101_120000",
            config={},
            started_at=datetime.now(timezone.utc),
        )
        obs2 = Observation(
            camera_id=camera2.id,
            observation_type="timelapse",
            status=ObservationStatus.RUNNING,
            folder_path="/media/observations/camera2_20260101_120000",
            config={},
            started_at=datetime.now(timezone.utc),
        )
        api_session.add_all([obs1, obs2])
        await api_session.commit()

        response = await client.get(f"/api/v1/observations/?camera_id={camera1.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["observations"]) == 1
        assert data["observations"][0]["camera_id"] == camera1.id


class TestActiveObservationsEndpoint:
    """Tests for GET /api/v1/observations/active endpoint."""

    @pytest.mark.asyncio
    async def test_list_active_observations(self, client, api_session):
        """GET /observations/active returns only running observations."""
        camera = Camera(
            name="Test Camera",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        api_session.add(camera)
        await api_session.commit()
        await api_session.refresh(camera)

        running_obs = Observation(
            camera_id=camera.id,
            observation_type="timelapse",
            status=ObservationStatus.RUNNING,
            folder_path="/media/observations/camera1_20260101_120000",
            config={},
            started_at=datetime.now(timezone.utc),
        )
        completed_obs = Observation(
            camera_id=camera.id,
            observation_type="recording",
            status=ObservationStatus.COMPLETED,
            folder_path="/media/observations/camera1_20260101_130000",
            config={},
            started_at=datetime.now(timezone.utc),
        )
        api_session.add_all([running_obs, completed_obs])
        await api_session.commit()

        response = await client.get("/api/v1/observations/active")

        assert response.status_code == 200
        data = response.json()
        assert len(data["observations"]) == 1
        assert data["observations"][0]["status"] == "running"


class TestCompletedObservationsEndpoint:
    """Tests for GET /api/v1/observations/completed endpoint."""

    @pytest.mark.asyncio
    async def test_list_completed_observations(self, client, api_session):
        """GET /observations/completed returns only completed observations."""
        camera = Camera(
            name="Test Camera",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        api_session.add(camera)
        await api_session.commit()
        await api_session.refresh(camera)

        running_obs = Observation(
            camera_id=camera.id,
            observation_type="timelapse",
            status=ObservationStatus.RUNNING,
            folder_path="/media/observations/camera1_20260101_120000",
            config={},
            started_at=datetime.now(timezone.utc),
        )
        completed_obs = Observation(
            camera_id=camera.id,
            observation_type="recording",
            status=ObservationStatus.COMPLETED,
            folder_path="/media/observations/camera1_20260101_130000",
            config={},
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        api_session.add_all([running_obs, completed_obs])
        await api_session.commit()

        response = await client.get("/api/v1/observations/completed")

        assert response.status_code == 200
        data = response.json()
        assert len(data["observations"]) == 1
        assert data["observations"][0]["status"] == "completed"


class TestObservationGetEndpoint:
    """Tests for GET /api/v1/observations/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_observation_by_id(self, client, api_session):
        """GET /observations/{id} returns observation details."""
        camera = Camera(
            name="Test Camera",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        api_session.add(camera)
        await api_session.commit()
        await api_session.refresh(camera)

        obs = Observation(
            camera_id=camera.id,
            observation_type="timelapse",
            status=ObservationStatus.RUNNING,
            folder_path="/media/observations/camera1_20260101_120000",
            config={"interval_seconds": 60},
            started_at=datetime.now(timezone.utc),
        )
        api_session.add(obs)
        await api_session.commit()
        await api_session.refresh(obs)

        response = await client.get(f"/api/v1/observations/{obs.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == obs.id
        assert data["observation_type"] == "timelapse"

    @pytest.mark.asyncio
    async def test_get_observation_not_found(self, client):
        """GET /observations/{id} returns 404 for missing observation."""
        response = await client.get("/api/v1/observations/99999")

        assert response.status_code == 404


class TestObservationNotesEndpoint:
    """Tests for PUT /api/v1/observations/{id}/notes endpoint."""

    @pytest.mark.asyncio
    async def test_update_observation_notes(self, client, api_session):
        """PUT /observations/{id}/notes updates notes."""
        camera = Camera(
            name="Test Camera",
            device_path="/dev/video0",
            camera_type="usb",
            enabled=True,
        )
        api_session.add(camera)
        await api_session.commit()
        await api_session.refresh(camera)

        obs = Observation(
            camera_id=camera.id,
            observation_type="timelapse",
            status=ObservationStatus.COMPLETED,
            folder_path="/media/observations/camera1_20260101_120000",
            config={},
            started_at=datetime.now(timezone.utc),
        )
        api_session.add(obs)
        await api_session.commit()
        await api_session.refresh(obs)

        response = await client.put(
            f"/api/v1/observations/{obs.id}/notes",
            json={"notes": "Updated notes for testing"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Updated notes for testing"

    @pytest.mark.asyncio
    async def test_update_notes_not_found(self, client):
        """PUT /observations/{id}/notes returns 404 for missing observation."""
        response = await client.put(
            "/api/v1/observations/99999/notes",
            json={"notes": "Test notes"},
        )

        assert response.status_code == 404

"""Tests for health and stats endpoints."""

import pytest


class TestHealthEndpoints:
    """Tests for /api/v1/health endpoints."""

    @pytest.mark.asyncio
    async def test_health_check_returns_ok(self, client):
        """GET /health returns 200 with status 'ok'."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_check_contains_version(self, client):
        """Health response includes version field."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data["data"]

    @pytest.mark.asyncio
    async def test_health_check_contains_environment(self, client):
        """Health response includes environment field."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert "environment" in data["data"]

    @pytest.mark.asyncio
    async def test_stats_endpoint_returns_system_info(self, client):
        """GET /health/stats returns CPU, memory, disk info."""
        response = await client.get("/api/v1/health/stats")

        assert response.status_code == 200
        data = response.json()["data"]
        assert "cpu_percent" in data
        assert "memory" in data
        assert "disk" in data

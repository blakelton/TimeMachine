"""Tests for WebSocket manager service."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.websocket.manager import WebSocketManager


class TestWebSocketManagerConnections:
    """Tests for WebSocket connection management."""

    @pytest.mark.asyncio
    async def test_connect_adds_client(self):
        """Connect adds client to client set."""
        manager = WebSocketManager()
        websocket = MagicMock()
        websocket.accept = AsyncMock()

        await manager.connect(websocket)

        assert manager.client_count == 1
        websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_removes_client(self):
        """Disconnect removes client from client set."""
        manager = WebSocketManager()
        websocket = MagicMock()
        websocket.accept = AsyncMock()

        await manager.connect(websocket)
        assert manager.client_count == 1

        await manager.disconnect(websocket)
        assert manager.client_count == 0

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_client_is_safe(self):
        """Disconnect handles non-existent client gracefully."""
        manager = WebSocketManager()
        websocket = MagicMock()

        # Should not raise
        await manager.disconnect(websocket)
        assert manager.client_count == 0


class TestWebSocketManagerBroadcast:
    """Tests for WebSocket broadcast functionality."""

    @pytest.mark.asyncio
    async def test_broadcast_to_no_clients(self):
        """Broadcast with no clients does not raise."""
        manager = WebSocketManager()

        # Should not raise
        await manager.broadcast({"type": "test"})

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_clients(self):
        """Broadcast sends message to all connected clients."""
        manager = WebSocketManager()

        client1 = MagicMock()
        client1.accept = AsyncMock()
        client1.send_text = AsyncMock()

        client2 = MagicMock()
        client2.accept = AsyncMock()
        client2.send_text = AsyncMock()

        await manager.connect(client1)
        await manager.connect(client2)

        await manager.broadcast({"type": "test", "data": "hello"})

        client1.send_text.assert_called_once()
        client2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_removes_failed_clients(self):
        """Broadcast removes clients that fail to receive."""
        manager = WebSocketManager()

        good_client = MagicMock()
        good_client.accept = AsyncMock()
        good_client.send_text = AsyncMock()

        bad_client = MagicMock()
        bad_client.accept = AsyncMock()
        bad_client.send_text = AsyncMock(side_effect=Exception("Connection closed"))

        await manager.connect(good_client)
        await manager.connect(bad_client)
        assert manager.client_count == 2

        await manager.broadcast({"type": "test"})

        # Bad client should be removed
        assert manager.client_count == 1

    @pytest.mark.asyncio
    async def test_broadcast_handles_timeout(self):
        """Broadcast handles slow clients with timeout."""
        manager = WebSocketManager()

        slow_client = MagicMock()
        slow_client.accept = AsyncMock()

        async def slow_send(*args):
            await asyncio.sleep(10)  # Will timeout

        slow_client.send_text = slow_send

        await manager.connect(slow_client)

        # Use short timeout to avoid waiting
        await manager.broadcast({"type": "test"})

        # Client should be removed after timeout
        assert manager.client_count == 0


class TestWebSocketManagerJobUpdates:
    """Tests for job update broadcasting."""

    @pytest.mark.asyncio
    async def test_broadcast_job_update_message_format(self):
        """broadcast_job_update sends correctly formatted message."""
        manager = WebSocketManager()
        messages_sent = []

        async def capture_broadcast(message):
            messages_sent.append(message)

        manager.broadcast = capture_broadcast

        await manager.broadcast_job_update(
            job_id=1,
            camera_id=2,
            job_type="timelapse",
            status="running",
            current_frame=50,
            total_frames=100,
        )

        assert len(messages_sent) == 1
        msg = messages_sent[0]
        assert msg["type"] == "job_update"
        assert msg["job_id"] == 1
        assert msg["camera_id"] == 2
        assert msg["job_type"] == "timelapse"
        assert msg["status"] == "running"
        assert msg["current_frame"] == 50
        assert msg["total_frames"] == 100
        assert msg["progress"] == 50.0  # Auto-calculated

    @pytest.mark.asyncio
    async def test_broadcast_job_update_explicit_progress(self):
        """broadcast_job_update uses explicit progress when provided."""
        manager = WebSocketManager()
        messages_sent = []

        async def capture_broadcast(message):
            messages_sent.append(message)

        manager.broadcast = capture_broadcast

        await manager.broadcast_job_update(
            job_id=1,
            camera_id=2,
            job_type="timelapse",
            status="running",
            progress=75.5,  # Explicit progress
            current_frame=50,
            total_frames=100,
        )

        msg = messages_sent[0]
        assert msg["progress"] == 75.5  # Uses explicit value, not calculated

    @pytest.mark.asyncio
    async def test_broadcast_job_update_unlimited_timelapse(self):
        """broadcast_job_update handles unlimited timelapse (no total_frames)."""
        manager = WebSocketManager()
        messages_sent = []

        async def capture_broadcast(message):
            messages_sent.append(message)

        manager.broadcast = capture_broadcast

        await manager.broadcast_job_update(
            job_id=1,
            camera_id=2,
            job_type="timelapse",
            status="running",
            current_frame=50,
            total_frames=None,  # Unlimited
        )

        msg = messages_sent[0]
        assert msg["current_frame"] == 50
        assert msg["total_frames"] is None
        assert msg["progress"] is None  # Can't calculate without total


class TestWebSocketManagerClientCount:
    """Tests for client count property."""

    @pytest.mark.asyncio
    async def test_client_count_reflects_connections(self):
        """client_count accurately reflects active connections."""
        manager = WebSocketManager()
        assert manager.client_count == 0

        clients = []
        for i in range(3):
            client = MagicMock()
            client.accept = AsyncMock()
            clients.append(client)
            await manager.connect(client)
            assert manager.client_count == i + 1

        for i, client in enumerate(clients):
            await manager.disconnect(client)
            assert manager.client_count == 2 - i

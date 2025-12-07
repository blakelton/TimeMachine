"""WebSocket connection manager for real-time client updates."""

import asyncio
import json
from typing import Set

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and broadcasts messages to clients.

    Attributes:
        _clients: Set of active WebSocket connections.
        _lock: Asyncio lock for thread-safe client set operations.
    """

    def __init__(self) -> None:
        """Initialize the WebSocket manager."""
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to register.
        """
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
        logger.info("ws_client_connected", total=len(self._clients))

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from the manager.

        Args:
            websocket: The WebSocket connection to remove.
        """
        async with self._lock:
            self._clients.discard(websocket)
        logger.info("ws_client_disconnected", total=len(self._clients))

    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients.

        Failed sends are logged and the client is automatically disconnected.

        Race condition fix: We snapshot clients under lock, then verify each
        client is still active before sending. This prevents sending to
        disconnected clients while avoiding holding the lock during I/O.

        Args:
            message: Dictionary to send as JSON to all clients.
        """
        if not self._clients:
            return

        data = json.dumps(message, default=str)

        # Take snapshot of clients under lock
        async with self._lock:
            clients = list(self._clients)

        # Send to snapshot, collecting failures
        disconnected = []
        for client in clients:
            try:
                # Double-check client still active before sending
                # (avoids sending to clients disconnected during iteration)
                if client not in self._clients:
                    continue

                await asyncio.wait_for(
                    client.send_text(data),
                    timeout=5.0,
                )
            except asyncio.TimeoutError:
                logger.warning("ws_send_timeout")
                disconnected.append(client)
            except Exception as e:
                logger.warning("ws_send_failed", error=str(e))
                disconnected.append(client)

        # Clean up failed connections under lock
        if disconnected:
            async with self._lock:
                for client in disconnected:
                    self._clients.discard(client)
            logger.info(
                "ws_clients_cleaned_up",
                disconnected=len(disconnected),
                remaining=len(self._clients),
            )

    async def send_to(self, websocket: WebSocket, message: dict) -> None:
        """Send a message to a specific client.

        Args:
            websocket: The WebSocket connection to send to.
            message: Dictionary to send as JSON.
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning("ws_send_to_failed", error=str(e))
            await self.disconnect(websocket)

    @property
    def client_count(self) -> int:
        """Get the number of connected clients.

        Returns:
            Number of active WebSocket connections.
        """
        return len(self._clients)


# Global singleton instance
ws_manager = WebSocketManager()

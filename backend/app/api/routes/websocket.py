"""WebSocket endpoint for real-time updates."""

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket.manager import ws_manager

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time client updates.

    Clients connect to this endpoint to receive:
    - System stats updates (CPU, memory, disk, temperature)
    - Camera status events (online, offline, recording)
    - Job progress updates (capture, record, timelapse)
    - Error notifications

    Args:
        websocket: The WebSocket connection.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle any client messages
            # Currently we just receive and ignore client messages
            # In the future, we could handle client-initiated requests here
            data = await websocket.receive_text()
            logger.debug("ws_client_message_received", data=data)
    except WebSocketDisconnect:
        logger.info("ws_client_disconnect")
    finally:
        await ws_manager.disconnect(websocket)

"""Background task for broadcasting system stats to WebSocket clients."""

import asyncio

import structlog

from app.core.constants import STATS_BROADCAST_INTERVAL_SECONDS
from app.models.schemas.websocket import WSStatsUpdate
from app.services.system.stats import get_system_stats
from app.services.websocket.manager import ws_manager

logger = structlog.get_logger(__name__)


async def stats_broadcast_loop() -> None:
    """Periodically broadcast system stats to all connected WebSocket clients.

    Broadcasts every 2 seconds when clients are connected.
    Skips broadcasting when no clients are connected to save resources.
    """
    logger.info("stats_broadcast_loop_started")

    while True:
        try:
            if ws_manager.client_count > 0:
                # Get current system stats (returns SystemStats dataclass)
                stats = await get_system_stats()

                # Create stats update message using dataclass attributes
                message = WSStatsUpdate(
                    cpu_percent=stats.cpu_percent,
                    memory_percent=stats.memory.percent,
                    disk_free_gb=stats.disk.free_gb,
                    temperature_celsius=stats.temperature_celsius,
                )

                # Broadcast to all connected clients
                await ws_manager.broadcast(message.model_dump(mode="json"))

                logger.debug(
                    "stats_broadcast_sent",
                    clients=ws_manager.client_count,
                    cpu=stats.cpu_percent,
                    memory=stats.memory.percent,
                )
        except Exception as e:
            logger.error("stats_broadcast_error", error=str(e))

        await asyncio.sleep(STATS_BROADCAST_INTERVAL_SECONDS)

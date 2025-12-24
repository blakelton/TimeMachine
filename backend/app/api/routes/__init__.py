"""API route modules."""

from app.api.routes import (
    cameras,
    environment,
    health,
    jobs,
    observations,
    output_config,
    temperature,
    websocket,
)

__all__ = [
    "cameras",
    "environment",
    "health",
    "jobs",
    "observations",
    "output_config",
    "temperature",
    "websocket",
]

"""API route modules."""

from app.api.routes import cameras, health, jobs, output_config, temperature, websocket

__all__ = [
    "cameras",
    "health",
    "jobs",
    "output_config",
    "temperature",
    "websocket",
]

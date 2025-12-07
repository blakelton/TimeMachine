"""SQLAlchemy declarative base and model imports."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# Import all models here for Alembic auto-generation
from app.db.models.camera import Camera  # noqa: F401
from app.db.models.event import Event  # noqa: F401
from app.db.models.job import Job  # noqa: F401
from app.db.models.output_config import OutputConfig  # noqa: F401
from app.db.models.temperature_config import TemperatureConfig  # noqa: F401

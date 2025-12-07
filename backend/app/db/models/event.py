"""Event logging database model."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Event(Base):
    """System event log."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # "camera_online", "camera_offline", "recording_started", etc.
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # "info", "warning", "error"

    # Event details (JSON)
    # Example: {"camera_id": 1, "reason": "device_disconnected"}
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Human-readable message
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), index=True
    )

    def __repr__(self) -> str:
        return f"<Event(id={self.id}, type='{self.event_type}', severity='{self.severity}')>"

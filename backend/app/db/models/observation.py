"""Observation database model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.constants import ObservationStatus
from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.camera import Camera
    from app.db.models.job import Job

# Re-export for convenience
__all__ = ["Observation", "ObservationStatus"]


class Observation(Base):
    """Observation tracking for recordings, timelapses, and still captures.

    An observation represents a capture session (still image, recording, or timelapse),
    stored in an organized folder with metadata, notes, and media files.
    """

    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True
    )
    observation_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # "timelapse" | "recording" | "still"
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # See ObservationStatus enum for valid values

    # Folder structure
    folder_path: Mapped[str] = mapped_column(
        String(500), nullable=False, unique=True
    )  # /media/observations/{camera_id}_{timestamp}/

    # Configuration (JSON) - type-specific settings
    config: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Progress tracking
    progress_current: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # frames captured or seconds recorded
    progress_total: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # target frames/seconds (None for manual stop)

    # Size tracking
    size_bytes: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False
    )

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    target_end_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )  # When observation should end (if end_mode is datetime)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    # Links to existing Job for backward compatibility
    job_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Error information
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # User notes (optional)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    camera: Mapped["Camera"] = relationship("Camera", back_populates="observations")
    job: Mapped["Job | None"] = relationship("Job", back_populates="observation")

    def __repr__(self) -> str:
        return (
            f"<Observation(id={self.id}, type='{self.observation_type}', "
            f"status='{self.status}')>"
        )

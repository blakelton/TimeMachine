"""Job tracking database model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.camera import Camera
    from app.db.models.observation import Observation


class Job(Base):
    """Job tracking for recordings, timelapses, and captures."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # "recording", "timelapse", "capture"
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # "pending", "running", "completed", "failed", "interrupted"

    # Timelapse-specific fields
    timelapse_config: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # {interval, total_frames, quality}
    timelapse_progress: Mapped[int | None] = mapped_column(
        Integer, default=0, nullable=True
    )  # Current frame count
    timelapse_dir: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )  # Directory for frames

    # Output file path
    output_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Error information
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    camera: Mapped["Camera"] = relationship("Camera", back_populates="jobs")
    observation: Mapped["Observation | None"] = relationship(
        "Observation", back_populates="job", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, type='{self.job_type}', status='{self.status}')>"

"""Camera database model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.job import Job


class Camera(Base):
    """Camera configuration and metadata."""

    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    device_path: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    camera_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "csi" or "usb"
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Camera capabilities (JSON)
    # Example: {"resolutions": ["1920x1080", "1280x720"], "max_fps": 30}
    capabilities: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Default settings (JSON)
    # Example: {"resolution": "1920x1080", "fps": 30, "bitrate": 4000000}
    default_settings: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="camera", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Camera(id={self.id}, name='{self.name}', type='{self.camera_type}')>"

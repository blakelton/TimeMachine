"""Output configuration database model."""

from datetime import datetime

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class OutputConfig(Base):
    """Storage output configuration."""

    __tablename__ = "output_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Storage paths
    recordings_path: Mapped[str] = mapped_column(
        String(500), nullable=False, default="/var/lib/timemachine/media/recordings"
    )
    stills_path: Mapped[str] = mapped_column(
        String(500), nullable=False, default="/var/lib/timemachine/media/stills"
    )
    timelapse_path: Mapped[str] = mapped_column(
        String(500), nullable=False, default="/var/lib/timemachine/media/timelapse"
    )

    # Retention settings
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    retention_max_gb: Mapped[int] = mapped_column(Integer, nullable=False, default=50)

    # Dashboard preview settings
    dashboard_preview_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    dashboard_preview_fps: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<OutputConfig(id={self.id}, retention_days={self.retention_days})>"

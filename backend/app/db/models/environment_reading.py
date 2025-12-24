"""Environment sensor reading database model."""

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class EnvironmentReading(Base):
    """Environment sensor reading.

    Stores individual readings from environment sensors including
    temperature, humidity, and pressure values.
    """

    __tablename__ = "environment_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Link to device
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("environment_devices.id", ondelete="CASCADE"), nullable=False
    )

    # Sensor readings (nullable since not all sensors measure all values)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Reading timestamp
    timestamp: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    # Relationship to device
    device = relationship("EnvironmentDevice", backref="readings")

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_environment_readings_device_timestamp", "device_id", "timestamp"),
        Index("ix_environment_readings_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<EnvironmentReading(id={self.id}, device_id={self.device_id}, temp={self.temperature}, humidity={self.humidity})>"

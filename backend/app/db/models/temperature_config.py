"""Temperature control configuration database model."""

from datetime import datetime

from sqlalchemy import Boolean, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class TemperatureConfig(Base):
    """Temperature control configuration (stub for future implementation)."""

    __tablename__ = "temperature_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Target temperature in Celsius
    target_temp: Mapped[float | None] = mapped_column(Float, nullable=True)

    # GPIO pin assignments
    sensor_pin: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heater_pin: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cooler_pin: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Hysteresis (temperature deadband)
    hysteresis: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<TemperatureConfig(id={self.id}, enabled={self.enabled}, target={self.target_temp})>"

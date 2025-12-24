"""Environment feedback device database model."""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class DeviceType(str, Enum):
    """Supported feedback device types."""

    DHT22 = "dht22"  # DHT22 / AM2302 - Temperature & Humidity
    DHT11 = "dht11"  # DHT11 - Temperature & Humidity (lower precision)
    AM2303 = "am2303"  # AM2303 - Same as DHT22, different packaging
    BME280 = "bme280"  # BME280 - Temperature, Humidity, Pressure (I2C)
    DS18B20 = "ds18b20"  # DS18B20 - Temperature only (1-Wire)


class TemperatureUnit(str, Enum):
    """Temperature display units."""

    CELSIUS = "C"
    FAHRENHEIT = "F"


class EnvironmentDevice(Base):
    """Environment feedback device configuration.

    Represents a sensor device that provides environmental readings
    like temperature, humidity, or pressure.
    """

    __tablename__ = "environment_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Device identification
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Device configuration
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # GPIO/Interface configuration
    # For DHT11/DHT22/AM2303: GPIO data pin number
    # For BME280: I2C address (typically 0x76 or 0x77)
    # For DS18B20: 1-Wire device ID
    pin_or_address: Mapped[str] = mapped_column(String(100), nullable=False)

    # Optional notes for the device
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Reading configuration
    # How often to poll this sensor (in seconds)
    poll_interval_seconds: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False
    )

    # Display preferences
    # Temperature unit: 'C' for Celsius, 'F' for Fahrenheit
    temperature_unit: Mapped[str] = mapped_column(
        String(1), default="C", nullable=False
    )

    # Target/normal values for comparison (stored in Celsius)
    # These help visualize how current readings compare to expected values
    target_temperature: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=None
    )
    target_humidity: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=None
    )
    target_pressure: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=None
    )

    # Acceptable range around target (± this value)
    # If current reading is outside target ± range, it's considered out of normal
    temperature_tolerance: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=5.0  # ±5°C by default
    )
    humidity_tolerance: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=10.0  # ±10% by default
    )
    pressure_tolerance: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=20.0  # ±20 hPa by default
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<EnvironmentDevice(id={self.id}, name='{self.name}', type={self.device_type})>"

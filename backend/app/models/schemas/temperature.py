"""Pydantic schemas for temperature control."""

from datetime import datetime

from pydantic import BaseModel, Field


class TemperatureConfigBase(BaseModel):
    """Base schema for temperature configuration."""

    enabled: bool = Field(default=False, description="Enable temperature control")
    target_temp: float | None = Field(
        default=None,
        description="Target temperature in Celsius",
        ge=-20,
        le=60,
    )
    sensor_pin: int | None = Field(
        default=None, description="GPIO pin for temperature sensor"
    )
    heater_pin: int | None = Field(default=None, description="GPIO pin for heater")
    cooler_pin: int | None = Field(default=None, description="GPIO pin for cooler")
    hysteresis: float = Field(
        default=1.0,
        description="Temperature hysteresis (deadband) in Celsius",
        ge=0.1,
        le=10.0,
    )


class TemperatureConfigCreate(TemperatureConfigBase):
    """Schema for creating temperature configuration."""

    pass


class TemperatureConfigUpdate(BaseModel):
    """Schema for updating temperature configuration."""

    enabled: bool | None = None
    target_temp: float | None = Field(default=None, ge=-20, le=60)
    sensor_pin: int | None = None
    heater_pin: int | None = None
    cooler_pin: int | None = None
    hysteresis: float | None = Field(default=None, ge=0.1, le=10.0)


class TemperatureConfig(TemperatureConfigBase):
    """Schema for temperature configuration response."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemperatureReading(BaseModel):
    """Current temperature reading (stub)."""

    current_temp: float | None = Field(
        default=None, description="Current temperature in Celsius"
    )
    target_temp: float | None = Field(
        default=None, description="Target temperature in Celsius"
    )
    heater_active: bool = Field(default=False, description="Heater is currently active")
    cooler_active: bool = Field(default=False, description="Cooler is currently active")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TemperatureStubMessage(BaseModel):
    """Stub message for temperature features."""

    message: str = "Temperature control is not yet implemented. This is a stub endpoint for future functionality."
    enabled: bool = False

"""Environment feedback device API schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DeviceType(str, Enum):
    """Supported feedback device types."""

    DHT22 = "dht22"
    DHT11 = "dht11"
    AM2303 = "am2303"
    BME280 = "bme280"
    DS18B20 = "ds18b20"


class TemperatureUnit(str, Enum):
    """Temperature display units."""

    CELSIUS = "C"
    FAHRENHEIT = "F"


class DeviceTypeInfo(BaseModel):
    """Information about a device type."""

    type: DeviceType = Field(..., description="Device type identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Description of the device")
    measures: list[str] = Field(..., description="What this device measures")
    interface: str = Field(..., description="Interface type (GPIO, I2C, 1-Wire)")
    pin_label: str = Field(..., description="Label for the pin/address field")
    pin_placeholder: str = Field(..., description="Example value for pin/address")


# Device type definitions with metadata
DEVICE_TYPES: list[DeviceTypeInfo] = [
    DeviceTypeInfo(
        type=DeviceType.DHT22,
        name="DHT22 / AM2302",
        description="Digital temperature and humidity sensor with good accuracy",
        measures=["temperature", "humidity"],
        interface="GPIO",
        pin_label="GPIO Pin",
        pin_placeholder="4",
    ),
    DeviceTypeInfo(
        type=DeviceType.DHT11,
        name="DHT11",
        description="Basic digital temperature and humidity sensor",
        measures=["temperature", "humidity"],
        interface="GPIO",
        pin_label="GPIO Pin",
        pin_placeholder="4",
    ),
    DeviceTypeInfo(
        type=DeviceType.AM2303,
        name="AM2303",
        description="Wired version of DHT22, same specifications",
        measures=["temperature", "humidity"],
        interface="GPIO",
        pin_label="GPIO Pin",
        pin_placeholder="4",
    ),
    DeviceTypeInfo(
        type=DeviceType.BME280,
        name="BME280",
        description="High precision temperature, humidity, and pressure sensor",
        measures=["temperature", "humidity", "pressure"],
        interface="I2C",
        pin_label="I2C Address",
        pin_placeholder="0x76",
    ),
    DeviceTypeInfo(
        type=DeviceType.DS18B20,
        name="DS18B20",
        description="Waterproof digital temperature sensor",
        measures=["temperature"],
        interface="1-Wire",
        pin_label="Device ID",
        pin_placeholder="28-xxxxxxxxxxxx",
    ),
]


class ReadingStatus(str, Enum):
    """Status of a reading compared to target."""

    NORMAL = "normal"  # Within tolerance of target
    HIGH = "high"  # Above target + tolerance
    LOW = "low"  # Below target - tolerance
    UNKNOWN = "unknown"  # No target set


class EnvironmentDeviceBase(BaseModel):
    """Base schema for environment device."""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Device display name"
    )
    device_type: DeviceType = Field(..., description="Type of sensor device")
    pin_or_address: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="GPIO pin number, I2C address, or device ID",
    )
    enabled: bool = Field(True, description="Whether device is enabled for reading")
    poll_interval_seconds: int = Field(
        10, ge=5, le=3600, description="Polling interval in seconds (5-3600)"
    )
    temperature_unit: TemperatureUnit = Field(
        TemperatureUnit.CELSIUS, description="Temperature display unit (C or F)"
    )
    notes: str | None = Field(None, max_length=500, description="Optional notes")

    # Target/normal values for comparison
    target_temperature: float | None = Field(
        None, ge=-50, le=100, description="Target temperature in Celsius"
    )
    target_humidity: float | None = Field(
        None, ge=0, le=100, description="Target humidity percentage"
    )
    target_pressure: float | None = Field(
        None, ge=800, le=1200, description="Target pressure in hPa"
    )

    # Tolerance values (± range around target)
    temperature_tolerance: float | None = Field(
        5.0, ge=0.1, le=50, description="Acceptable ± range for temperature"
    )
    humidity_tolerance: float | None = Field(
        10.0, ge=1, le=50, description="Acceptable ± range for humidity"
    )
    pressure_tolerance: float | None = Field(
        20.0, ge=1, le=100, description="Acceptable ± range for pressure"
    )


class EnvironmentDeviceCreate(EnvironmentDeviceBase):
    """Schema for creating an environment device."""

    pass


class EnvironmentDeviceUpdate(BaseModel):
    """Schema for updating an environment device (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=100)
    device_type: DeviceType | None = None
    pin_or_address: str | None = Field(None, min_length=1, max_length=100)
    enabled: bool | None = None
    poll_interval_seconds: int | None = Field(None, ge=5, le=3600)
    temperature_unit: TemperatureUnit | None = None
    notes: str | None = Field(None, max_length=500)

    # Target/normal values for comparison
    target_temperature: float | None = Field(None, ge=-50, le=100)
    target_humidity: float | None = Field(None, ge=0, le=100)
    target_pressure: float | None = Field(None, ge=800, le=1200)

    # Tolerance values (± range around target)
    temperature_tolerance: float | None = Field(None, ge=0.1, le=50)
    humidity_tolerance: float | None = Field(None, ge=1, le=50)
    pressure_tolerance: float | None = Field(None, ge=1, le=100)


class EnvironmentDeviceResponse(EnvironmentDeviceBase):
    """Schema for environment device response."""

    id: int = Field(..., description="Device ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class EnvironmentDeviceListResponse(BaseModel):
    """Schema for list of environment devices."""

    devices: list[EnvironmentDeviceResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total number of devices")


class DeviceTypesResponse(BaseModel):
    """Schema for available device types."""

    device_types: list[DeviceTypeInfo] = Field(default_factory=list)


class EnvironmentReadingResponse(BaseModel):
    """A single sensor reading from the database."""

    id: int = Field(..., description="Reading ID")
    device_id: int = Field(..., description="Device ID")
    temperature: float | None = Field(None, description="Temperature in Celsius")
    humidity: float | None = Field(None, description="Relative humidity %")
    pressure: float | None = Field(None, description="Atmospheric pressure in hPa")
    timestamp: datetime = Field(..., description="Reading timestamp")

    model_config = {"from_attributes": True}


class DeviceCurrentReading(BaseModel):
    """Current reading for a device with device info."""

    device_id: int = Field(..., description="Device ID")
    device_name: str = Field(..., description="Device name")
    device_type: DeviceType = Field(..., description="Device type")
    enabled: bool = Field(..., description="Whether device is enabled")
    temperature_unit: TemperatureUnit = Field(..., description="Temperature display unit")

    # Current readings
    temperature: float | None = Field(None, description="Temperature in configured unit")
    humidity: float | None = Field(None, description="Relative humidity %")
    pressure: float | None = Field(None, description="Atmospheric pressure in hPa")

    # Target values (temperature in configured unit)
    target_temperature: float | None = Field(None, description="Target temperature in configured unit")
    target_humidity: float | None = Field(None, description="Target humidity %")
    target_pressure: float | None = Field(None, description="Target pressure in hPa")

    # Tolerance values
    temperature_tolerance: float | None = Field(None, description="Temperature tolerance ±")
    humidity_tolerance: float | None = Field(None, description="Humidity tolerance ±")
    pressure_tolerance: float | None = Field(None, description="Pressure tolerance ±")

    # Status compared to target
    temperature_status: ReadingStatus = Field(ReadingStatus.UNKNOWN, description="Temperature vs target")
    humidity_status: ReadingStatus = Field(ReadingStatus.UNKNOWN, description="Humidity vs target")
    pressure_status: ReadingStatus = Field(ReadingStatus.UNKNOWN, description="Pressure vs target")

    # Deviation from target (positive = above, negative = below)
    temperature_deviation: float | None = Field(None, description="How far from target temperature")
    humidity_deviation: float | None = Field(None, description="How far from target humidity")
    pressure_deviation: float | None = Field(None, description="How far from target pressure")

    timestamp: datetime | None = Field(None, description="Reading timestamp")
    error: str | None = Field(None, description="Error message if reading failed")


class CurrentReadingsResponse(BaseModel):
    """Response with current readings from all devices."""

    readings: list[DeviceCurrentReading] = Field(default_factory=list)
    total: int = Field(..., description="Total number of devices")


class DeviceHistoryResponse(BaseModel):
    """Historical readings for a single device."""

    device_id: int = Field(..., description="Device ID")
    device_name: str = Field(..., description="Device name")
    device_type: DeviceType = Field(..., description="Device type")
    temperature_unit: TemperatureUnit = Field(..., description="Temperature display unit")
    readings: list[EnvironmentReadingResponse] = Field(default_factory=list)
    total: int = Field(..., description="Number of readings returned")

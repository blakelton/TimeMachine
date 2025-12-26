"""Sensor reading utilities for environment monitoring.

Supports:
- DHT11/DHT22/AM2303 (GPIO, adafruit-circuitpython-dht)
- BME280 (I2C, adafruit-circuitpython-bme280)
- DS18B20 (1-Wire, w1thermsensor)
"""

import asyncio
from dataclasses import dataclass
from typing import Protocol

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SensorReading:
    """Container for sensor readings."""
    temperature: float | None = None
    humidity: float | None = None
    pressure: float | None = None
    error: str | None = None


class SensorReader(Protocol):
    """Protocol for sensor readers."""

    async def read(self) -> SensorReading:
        """Read sensor values."""
        ...

    def cleanup(self) -> None:
        """Clean up sensor resources."""
        ...


class DHTReader:
    """Reader for DHT11/DHT22/AM2303 sensors using adafruit-circuitpython-dht."""

    def __init__(self, pin: int, sensor_type: str = "dht22"):
        """Initialize DHT reader.

        Args:
            pin: GPIO pin number (BCM numbering).
            sensor_type: One of 'dht11', 'dht22', or 'am2303'.
        """
        self.pin = pin
        self.sensor_type = sensor_type.lower()
        self._sensor = None
        self._initialized = False

    def _initialize(self) -> bool:
        """Initialize the sensor (lazy initialization)."""
        if self._initialized:
            return self._sensor is not None

        self._initialized = True
        try:
            import board
            import adafruit_dht

            # Get the GPIO pin object
            pin_attr = f"D{self.pin}"
            if not hasattr(board, pin_attr):
                logger.error("dht_invalid_pin", pin=self.pin)
                return False

            gpio_pin = getattr(board, pin_attr)

            # Create sensor based on type
            if self.sensor_type == "dht11":
                self._sensor = adafruit_dht.DHT11(gpio_pin)
            else:  # dht22 or am2303 (they're the same)
                self._sensor = adafruit_dht.DHT22(gpio_pin)

            logger.info(
                "dht_sensor_initialized",
                pin=self.pin,
                type=self.sensor_type
            )
            return True

        except ImportError as e:
            logger.warning(
                "dht_library_not_available",
                error=str(e),
                hint="Install adafruit-circuitpython-dht"
            )
            return False
        except Exception as e:
            logger.error("dht_init_error", error=str(e))
            return False

    async def read(self) -> SensorReading:
        """Read temperature and humidity from DHT sensor."""
        if not self._initialize():
            return SensorReading(error="Sensor not initialized")

        try:
            # DHT sensors are slow, run in executor to avoid blocking
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self._read_sync)
            return result
        except Exception as e:
            logger.error("dht_read_error", error=str(e))
            return SensorReading(error=str(e))

    def _read_sync(self) -> SensorReading:
        """Synchronous read (run in executor)."""
        try:
            temperature = self._sensor.temperature
            humidity = self._sensor.humidity
            return SensorReading(
                temperature=round(temperature, 1) if temperature is not None else None,
                humidity=round(humidity, 1) if humidity is not None else None
            )
        except RuntimeError as e:
            # DHT sensors occasionally fail to read
            return SensorReading(error=f"Read failed: {e}")

    def cleanup(self) -> None:
        """Clean up sensor resources."""
        if self._sensor is not None:
            try:
                self._sensor.exit()
            except Exception:
                pass
            self._sensor = None


class BME280Reader:
    """Reader for BME280 sensor using adafruit-circuitpython-bme280."""

    def __init__(self, address: str = "0x76"):
        """Initialize BME280 reader.

        Args:
            address: I2C address as hex string (0x76 or 0x77).
        """
        try:
            self.address = int(address, 16) if address.startswith("0x") else int(address)
        except ValueError:
            logger.error("bme280_invalid_address", address=address)
            self.address = 0x76  # Default to standard address
        self._sensor = None
        self._initialized = False

    def _initialize(self) -> bool:
        """Initialize the sensor (lazy initialization)."""
        if self._initialized:
            return self._sensor is not None

        self._initialized = True
        try:
            import board
            import busio
            import adafruit_bme280.advanced as adafruit_bme280

            i2c = busio.I2C(board.SCL, board.SDA)
            self._sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=self.address)

            logger.info("bme280_sensor_initialized", address=hex(self.address))
            return True

        except ImportError as e:
            logger.warning(
                "bme280_library_not_available",
                error=str(e),
                hint="Install adafruit-circuitpython-bme280"
            )
            return False
        except Exception as e:
            logger.error("bme280_init_error", error=str(e))
            return False

    async def read(self) -> SensorReading:
        """Read temperature, humidity, and pressure from BME280."""
        if not self._initialize():
            return SensorReading(error="Sensor not initialized")

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self._read_sync)
            return result
        except Exception as e:
            logger.error("bme280_read_error", error=str(e))
            return SensorReading(error=str(e))

    def _read_sync(self) -> SensorReading:
        """Synchronous read (run in executor)."""
        try:
            return SensorReading(
                temperature=round(self._sensor.temperature, 1),
                humidity=round(self._sensor.humidity, 1),
                pressure=round(self._sensor.pressure, 1)
            )
        except Exception as e:
            return SensorReading(error=f"Read failed: {e}")

    def cleanup(self) -> None:
        """Clean up sensor resources."""
        self._sensor = None


class DS18B20Reader:
    """Reader for DS18B20 1-Wire temperature sensor."""

    def __init__(self, device_id: str = ""):
        """Initialize DS18B20 reader.

        Args:
            device_id: 1-Wire device ID (empty for first found).
        """
        self.device_id = device_id
        self._sensor = None
        self._initialized = False

    def _initialize(self) -> bool:
        """Initialize the sensor (lazy initialization)."""
        if self._initialized:
            return self._sensor is not None

        self._initialized = True
        try:
            from w1thermsensor import W1ThermSensor, NoSensorFoundError

            if self.device_id:
                self._sensor = W1ThermSensor(sensor_id=self.device_id)
            else:
                self._sensor = W1ThermSensor()

            logger.info(
                "ds18b20_sensor_initialized",
                device_id=self._sensor.id
            )
            return True

        except ImportError as e:
            logger.warning(
                "ds18b20_library_not_available",
                error=str(e),
                hint="Install w1thermsensor"
            )
            return False
        except NoSensorFoundError:
            logger.error(
                "ds18b20_no_sensor_found",
                device_id=self.device_id or "auto-detect"
            )
            return False
        except Exception as e:
            logger.error("ds18b20_init_error", error=str(e))
            return False

    async def read(self) -> SensorReading:
        """Read temperature from DS18B20."""
        if not self._initialize():
            return SensorReading(error="Sensor not initialized")

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self._read_sync)
            return result
        except Exception as e:
            logger.error("ds18b20_read_error", error=str(e))
            return SensorReading(error=str(e))

    def _read_sync(self) -> SensorReading:
        """Synchronous read (run in executor)."""
        try:
            temperature = self._sensor.get_temperature()
            return SensorReading(temperature=round(temperature, 1))
        except Exception as e:
            return SensorReading(error=f"Read failed: {e}")

    def cleanup(self) -> None:
        """Clean up sensor resources."""
        self._sensor = None


class MockSensorReader:
    """Mock sensor reader for testing/development."""

    def __init__(self, sensor_type: str = "dht22"):
        self.sensor_type = sensor_type
        self._counter = 0

    async def read(self) -> SensorReading:
        """Return simulated sensor readings."""
        import random
        self._counter += 1

        # Simulate some variation
        base_temp = 22.0 + random.uniform(-2, 2)
        base_humidity = 45.0 + random.uniform(-5, 5)

        if self.sensor_type in ("dht11", "dht22", "am2303"):
            return SensorReading(
                temperature=round(base_temp, 1),
                humidity=round(base_humidity, 1)
            )
        elif self.sensor_type == "bme280":
            return SensorReading(
                temperature=round(base_temp, 1),
                humidity=round(base_humidity, 1),
                pressure=round(1013.25 + random.uniform(-5, 5), 1)
            )
        elif self.sensor_type == "ds18b20":
            return SensorReading(temperature=round(base_temp, 1))
        else:
            return SensorReading(error=f"Unknown sensor type: {self.sensor_type}")

    def cleanup(self) -> None:
        """No cleanup needed for mock."""
        pass


def create_sensor_reader(device_type: str, pin_or_address: str, use_mock: bool = False) -> SensorReader:
    """Factory function to create the appropriate sensor reader.

    Args:
        device_type: One of 'dht11', 'dht22', 'am2303', 'bme280', 'ds18b20'.
        pin_or_address: GPIO pin, I2C address, or 1-Wire device ID.
        use_mock: If True, return a mock reader (for testing).

    Returns:
        Appropriate sensor reader instance.
    """
    if use_mock:
        return MockSensorReader(device_type)

    device_type = device_type.lower()

    if device_type in ("dht11", "dht22", "am2303"):
        pin = int(pin_or_address)
        return DHTReader(pin, device_type)
    elif device_type == "bme280":
        return BME280Reader(pin_or_address)
    elif device_type == "ds18b20":
        return DS18B20Reader(pin_or_address)
    else:
        logger.warning("unknown_sensor_type", device_type=device_type)
        return MockSensorReader(device_type)

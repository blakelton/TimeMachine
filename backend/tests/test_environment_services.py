"""Tests for environment services."""

import pytest

from app.services.environment.sensors import (
    MockSensorReader,
    SensorReading,
    create_sensor_reader,
)


class TestMockSensorReader:
    """Tests for MockSensorReader."""

    @pytest.mark.asyncio
    async def test_read_dht22_returns_temp_and_humidity(self):
        """Test that DHT22 mock returns temperature and humidity."""
        reader = MockSensorReader(sensor_type="dht22")
        reading = await reader.read()

        assert reading.temperature is not None
        assert reading.humidity is not None
        assert reading.error is None
        assert 18.0 <= reading.temperature <= 26.0
        assert 35.0 <= reading.humidity <= 55.0

    @pytest.mark.asyncio
    async def test_read_bme280_returns_all_values(self):
        """Test that BME280 mock returns temperature, humidity, and pressure."""
        reader = MockSensorReader(sensor_type="bme280")
        reading = await reader.read()

        assert reading.temperature is not None
        assert reading.humidity is not None
        assert reading.pressure is not None
        assert reading.error is None

    @pytest.mark.asyncio
    async def test_read_ds18b20_returns_only_temperature(self):
        """Test that DS18B20 mock returns only temperature."""
        reader = MockSensorReader(sensor_type="ds18b20")
        reading = await reader.read()

        assert reading.temperature is not None
        assert reading.humidity is None
        assert reading.pressure is None
        assert reading.error is None

    @pytest.mark.asyncio
    async def test_read_unknown_type_returns_error(self):
        """Test that unknown sensor type returns error."""
        reader = MockSensorReader(sensor_type="unknown")
        reading = await reader.read()

        assert reading.error is not None
        assert "Unknown sensor type" in reading.error

    def test_cleanup_does_not_raise(self):
        """Test that cleanup does not raise exceptions."""
        reader = MockSensorReader(sensor_type="dht22")
        reader.cleanup()  # Should not raise


class TestCreateSensorReader:
    """Tests for create_sensor_reader factory."""

    def test_creates_mock_reader_when_use_mock_true(self):
        """Test that mock reader is created when use_mock is True."""
        reader = create_sensor_reader("dht22", "4", use_mock=True)
        assert isinstance(reader, MockSensorReader)

    def test_creates_mock_for_unknown_type(self):
        """Test that mock reader is created for unknown device type."""
        reader = create_sensor_reader("unknown_sensor", "0", use_mock=True)
        assert isinstance(reader, MockSensorReader)


class TestSensorReading:
    """Tests for SensorReading dataclass."""

    def test_default_values_are_none(self):
        """Test that default values are None."""
        reading = SensorReading()
        assert reading.temperature is None
        assert reading.humidity is None
        assert reading.pressure is None
        assert reading.error is None

    def test_can_set_values(self):
        """Test that values can be set."""
        reading = SensorReading(
            temperature=22.5,
            humidity=45.0,
            pressure=1013.25,
            error=None,
        )
        assert reading.temperature == 22.5
        assert reading.humidity == 45.0
        assert reading.pressure == 1013.25
        assert reading.error is None

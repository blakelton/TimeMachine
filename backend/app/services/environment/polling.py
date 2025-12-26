"""Environment sensor polling service.

Manages background polling of configured environment sensors
and stores readings in the database.
"""

import asyncio
import threading
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.environment_device import EnvironmentDevice
from app.db.repositories.environment_device import EnvironmentDeviceRepository
from app.db.repositories.environment_reading import EnvironmentReadingRepository
from app.services.environment.sensors import SensorReader, SensorReading, create_sensor_reader

logger = get_logger(__name__)

# Lock for thread-safe access to global polling service instance
_polling_service_lock = threading.Lock()


class EnvironmentPollingService:
    """Service that polls environment sensors and stores readings."""

    def __init__(self, use_mock_sensors: bool = False):
        """Initialize the polling service.

        Args:
            use_mock_sensors: If True, use mock sensors for testing.
        """
        self._use_mock = use_mock_sensors
        self._running = False
        self._task: asyncio.Task | None = None
        self._readers: dict[int, SensorReader] = {}
        self._readers_lock = asyncio.Lock()
        self._last_readings: dict[int, SensorReading] = {}
        self._last_read_times: dict[int, datetime] = {}
        self._session_factory = None

    def set_session_factory(self, factory):
        """Set the database session factory.

        Args:
            factory: Async session factory callable.
        """
        self._session_factory = factory

    def get_latest_reading(self, device_id: int) -> SensorReading | None:
        """Get the most recent in-memory reading for a device.

        Args:
            device_id: The device ID.

        Returns:
            Latest reading or None if no readings cached.
        """
        return self._last_readings.get(device_id)

    def get_all_latest_readings(self) -> dict[int, SensorReading]:
        """Get all cached readings.

        Returns:
            Dictionary mapping device_id to latest reading.
        """
        return dict(self._last_readings)

    async def start(self):
        """Start the polling service."""
        if self._running:
            logger.warning("polling_service_already_running")
            return

        if self._session_factory is None:
            logger.error("polling_service_no_session_factory")
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("environment_polling_started")

    async def stop(self):
        """Stop the polling service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        # Clean up all sensors with lock to prevent race conditions
        async with self._readers_lock:
            for reader in self._readers.values():
                try:
                    reader.cleanup()
                except Exception as e:
                    logger.error("sensor_cleanup_error", error=str(e))
            self._readers.clear()

        logger.info("environment_polling_stopped")

    async def _poll_loop(self):
        """Main polling loop."""
        while self._running:
            try:
                await self._poll_all_devices()
            except Exception as e:
                logger.error("polling_loop_error", error=str(e))

            # Sleep for 1 second between poll cycles
            # Individual device intervals are checked in _poll_all_devices
            await asyncio.sleep(1)

    async def _poll_all_devices(self):
        """Poll all enabled devices that are due for reading."""
        async with self._session_factory() as session:
            repo = EnvironmentDeviceRepository(session)
            reading_repo = EnvironmentReadingRepository(session)

            devices = await repo.get_enabled()

            for device in devices:
                try:
                    await self._maybe_poll_device(device, reading_repo, session)
                except Exception as e:
                    logger.error(
                        "device_poll_error",
                        device_id=device.id,
                        device_name=device.name,
                        error=str(e)
                    )

    async def _maybe_poll_device(
        self,
        device: EnvironmentDevice,
        reading_repo: EnvironmentReadingRepository,
        session: AsyncSession
    ):
        """Poll a device if enough time has passed since last reading.

        Args:
            device: The device to poll.
            reading_repo: Repository for storing readings.
            session: Database session.
        """
        now = datetime.now()
        last_read = self._last_read_times.get(device.id)

        # Check if we should read this device
        if last_read is not None:
            elapsed = (now - last_read).total_seconds()
            if elapsed < device.poll_interval_seconds:
                return

        # Get or create reader for this device
        reader = await self._get_reader(device)
        if reader is None:
            return

        # Read the sensor
        reading = await reader.read()

        if reading.error:
            logger.warning(
                "sensor_read_error",
                device_id=device.id,
                device_name=device.name,
                error=reading.error
            )
            # Still update last read time to avoid hammering a broken sensor
            self._last_read_times[device.id] = now
            return

        # Store reading in database
        await reading_repo.add_reading(
            device_id=device.id,
            temperature=reading.temperature,
            humidity=reading.humidity,
            pressure=reading.pressure
        )
        await session.commit()

        # Update in-memory cache
        self._last_readings[device.id] = reading
        self._last_read_times[device.id] = now

        logger.debug(
            "sensor_reading_stored",
            device_id=device.id,
            temperature=reading.temperature,
            humidity=reading.humidity,
            pressure=reading.pressure
        )

    async def _get_reader(self, device: EnvironmentDevice) -> SensorReader | None:
        """Get or create a sensor reader for a device.

        Uses async lock to prevent race conditions during reader creation.

        Args:
            device: The device configuration.

        Returns:
            Sensor reader or None if creation failed.
        """
        # Fast path: reader already exists
        if device.id in self._readers:
            return self._readers.get(device.id)

        # Slow path: need to create reader with lock
        async with self._readers_lock:
            # Double-check after acquiring lock
            if device.id in self._readers:
                return self._readers.get(device.id)

            try:
                reader = create_sensor_reader(
                    device.device_type,
                    device.pin_or_address,
                    use_mock=self._use_mock
                )
                self._readers[device.id] = reader
                logger.info(
                    "sensor_reader_created",
                    device_id=device.id,
                    device_type=device.device_type
                )
                return reader
            except Exception as e:
                logger.error(
                    "sensor_reader_creation_failed",
                    device_id=device.id,
                    error=str(e)
                )
                return None

    async def invalidate_reader(self, device_id: int):
        """Remove a cached reader (e.g., when device config changes).

        Uses async lock to prevent race conditions with reader creation.

        Args:
            device_id: The device ID whose reader should be removed.
        """
        async with self._readers_lock:
            if device_id in self._readers:
                reader = self._readers.pop(device_id)
                try:
                    reader.cleanup()
                except Exception as e:
                    logger.debug("reader_cleanup_error", device_id=device_id, error=str(e))


# Global service instance
_polling_service: EnvironmentPollingService | None = None


def get_polling_service() -> EnvironmentPollingService:
    """Get the global polling service instance.

    Uses double-checked locking for thread safety.
    """
    global _polling_service
    if _polling_service is None:
        with _polling_service_lock:
            # Double-check after acquiring lock
            if _polling_service is None:
                _polling_service = EnvironmentPollingService()
    return _polling_service


async def start_polling_service(session_factory, use_mock: bool = False):
    """Initialize and start the polling service.

    Args:
        session_factory: Async session factory.
        use_mock: Use mock sensors for testing.
    """
    global _polling_service
    _polling_service = EnvironmentPollingService(use_mock_sensors=use_mock)
    _polling_service.set_session_factory(session_factory)
    await _polling_service.start()


async def stop_polling_service():
    """Stop the global polling service."""
    global _polling_service
    if _polling_service is not None:
        await _polling_service.stop()
        _polling_service = None

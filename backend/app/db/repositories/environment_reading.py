"""Environment reading repository."""

from datetime import datetime, timedelta

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.environment_reading import EnvironmentReading
from app.db.repositories.base import BaseRepository


class EnvironmentReadingRepository(BaseRepository[EnvironmentReading]):
    """Repository for environment reading operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(EnvironmentReading, session)

    async def get_latest_for_device(self, device_id: int) -> EnvironmentReading | None:
        """Get the most recent reading for a device.

        Args:
            device_id: The device ID.

        Returns:
            Latest EnvironmentReading instance or None if no readings exist.
        """
        result = await self.session.execute(
            select(EnvironmentReading)
            .where(EnvironmentReading.device_id == device_id)
            .order_by(desc(EnvironmentReading.timestamp))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_for_all_devices(self) -> list[EnvironmentReading]:
        """Get the most recent reading for each device.

        Returns:
            List of latest readings, one per device.
        """
        # Subquery to get max timestamp per device
        subq = (
            select(
                EnvironmentReading.device_id,
                func.max(EnvironmentReading.timestamp).label("max_ts")
            )
            .group_by(EnvironmentReading.device_id)
            .subquery()
        )

        result = await self.session.execute(
            select(EnvironmentReading)
            .join(
                subq,
                (EnvironmentReading.device_id == subq.c.device_id) &
                (EnvironmentReading.timestamp == subq.c.max_ts)
            )
        )
        return list(result.scalars().all())

    async def get_history(
        self,
        device_id: int,
        hours: int = 24,
        limit: int = 1000
    ) -> list[EnvironmentReading]:
        """Get historical readings for a device.

        Args:
            device_id: The device ID.
            hours: Number of hours of history to retrieve.
            limit: Maximum number of readings to return.

        Returns:
            List of readings ordered by timestamp (oldest first).
        """
        since = datetime.now() - timedelta(hours=hours)
        result = await self.session.execute(
            select(EnvironmentReading)
            .where(
                EnvironmentReading.device_id == device_id,
                EnvironmentReading.timestamp >= since
            )
            .order_by(EnvironmentReading.timestamp)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent(
        self,
        device_id: int,
        minutes: int = 30,
        limit: int = 500
    ) -> list[EnvironmentReading]:
        """Get recent readings for a device.

        Args:
            device_id: The device ID.
            minutes: Number of minutes of history to retrieve.
            limit: Maximum number of readings to return.

        Returns:
            List of readings ordered by timestamp (newest first).
        """
        since = datetime.now() - timedelta(minutes=minutes)
        result = await self.session.execute(
            select(EnvironmentReading)
            .where(
                EnvironmentReading.device_id == device_id,
                EnvironmentReading.timestamp >= since
            )
            .order_by(desc(EnvironmentReading.timestamp))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_reading(
        self,
        device_id: int,
        temperature: float | None = None,
        humidity: float | None = None,
        pressure: float | None = None,
    ) -> EnvironmentReading:
        """Add a new sensor reading.

        Args:
            device_id: The device ID.
            temperature: Temperature in Celsius (optional).
            humidity: Relative humidity percentage (optional).
            pressure: Pressure in hPa (optional).

        Returns:
            The created reading.
        """
        reading = EnvironmentReading(
            device_id=device_id,
            temperature=temperature,
            humidity=humidity,
            pressure=pressure,
            timestamp=datetime.now(),
        )
        self.session.add(reading)
        await self.session.flush()
        await self.session.refresh(reading)
        return reading

    async def cleanup_old_readings(self, days: int = 30) -> int:
        """Delete readings older than specified days.

        Args:
            days: Number of days to keep.

        Returns:
            Number of deleted readings.
        """
        cutoff = datetime.now() - timedelta(days=days)
        result = await self.session.execute(
            delete(EnvironmentReading)
            .where(EnvironmentReading.timestamp < cutoff)
        )
        await self.session.flush()
        return result.rowcount

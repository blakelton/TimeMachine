"""Environment device repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.environment_device import EnvironmentDevice
from app.db.repositories.base import BaseRepository


class EnvironmentDeviceRepository(BaseRepository[EnvironmentDevice]):
    """Repository for environment device operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(EnvironmentDevice, session)

    async def get_by_id(self, device_id: int) -> EnvironmentDevice | None:
        """Get device by ID (alias for get()).

        Args:
            device_id: The device ID.

        Returns:
            EnvironmentDevice instance or None if not found.
        """
        return await self.get(device_id)

    async def get_enabled(self) -> list[EnvironmentDevice]:
        """Get all enabled devices.

        Returns:
            List of enabled environment devices.
        """
        result = await self.session.execute(
            select(EnvironmentDevice).where(EnvironmentDevice.enabled == True)  # noqa: E712
        )
        return list(result.scalars().all())

    async def get_by_type(self, device_type: str) -> list[EnvironmentDevice]:
        """Get devices by type.

        Args:
            device_type: The device type (dht22, bme280, etc.).

        Returns:
            List of devices of the specified type.
        """
        result = await self.session.execute(
            select(EnvironmentDevice).where(EnvironmentDevice.device_type == device_type)
        )
        return list(result.scalars().all())

    async def get_by_pin(self, pin_or_address: str) -> EnvironmentDevice | None:
        """Get device by pin or address.

        Args:
            pin_or_address: The GPIO pin, I2C address, or device ID.

        Returns:
            EnvironmentDevice instance or None if not found.
        """
        result = await self.session.execute(
            select(EnvironmentDevice).where(
                EnvironmentDevice.pin_or_address == pin_or_address
            )
        )
        return result.scalar_one_or_none()

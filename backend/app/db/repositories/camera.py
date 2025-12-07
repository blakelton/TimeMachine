"""Camera repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.camera import Camera
from app.db.repositories.base import BaseRepository


class CameraRepository(BaseRepository[Camera]):
    """Repository for camera operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Camera, session)

    async def get_by_device_path(self, device_path: str) -> Camera | None:
        """Get camera by device path.

        Args:
            device_path: The camera device path (e.g., /dev/video0).

        Returns:
            Camera instance or None if not found.
        """
        result = await self.session.execute(
            select(Camera).where(Camera.device_path == device_path)
        )
        return result.scalar_one_or_none()

    async def get_enabled(self) -> list[Camera]:
        """Get all enabled cameras.

        Returns:
            List of enabled cameras.
        """
        result = await self.session.execute(
            select(Camera).where(Camera.enabled == True)  # noqa: E712
        )
        return list(result.scalars().all())

    async def get_by_type(self, camera_type: str) -> list[Camera]:
        """Get cameras by type.

        Args:
            camera_type: The camera type ("csi" or "usb").

        Returns:
            List of cameras of the specified type.
        """
        result = await self.session.execute(
            select(Camera).where(Camera.camera_type == camera_type)
        )
        return list(result.scalars().all())

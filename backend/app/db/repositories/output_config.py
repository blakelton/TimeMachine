"""Output configuration repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.output_config import OutputConfig
from app.db.repositories.base import BaseRepository


class OutputConfigRepository(BaseRepository[OutputConfig]):
    """Repository for output configuration operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(OutputConfig, session)

    async def get_current(self) -> OutputConfig | None:
        """Get the current output configuration.

        There should only be one configuration record.

        Returns:
            The output configuration or None if not found.
        """
        result = await self.session.execute(select(OutputConfig).limit(1))
        return result.scalar_one_or_none()

    async def get_or_create_default(self) -> OutputConfig:
        """Get current config or create default if none exists.

        Returns:
            The output configuration.
        """
        config = await self.get_current()
        if config is None:
            config = await self.create()
        return config

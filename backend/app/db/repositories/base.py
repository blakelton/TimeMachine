"""Base repository with common CRUD operations."""

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common database operations.

    Provides standard CRUD operations for SQLAlchemy models.
    """

    def __init__(self, model: type[ModelType], session: AsyncSession):
        """Initialize repository.

        Args:
            model: The SQLAlchemy model class.
            session: The database session.
        """
        self.model = model
        self.session = session

    async def get(self, id: int) -> ModelType | None:
        """Get a single record by ID.

        Args:
            id: The record ID.

        Returns:
            The model instance or None if not found.
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        """Get all records with pagination.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of model instances.
        """
        result = await self.session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, **kwargs) -> ModelType:
        """Create a new record.

        Args:
            **kwargs: Model fields as keyword arguments.

        Returns:
            The created model instance.
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: int, **kwargs) -> ModelType | None:
        """Update an existing record.

        Args:
            id: The record ID.
            **kwargs: Fields to update.

        Returns:
            The updated model instance or None if not found.
        """
        instance = await self.get(id)
        if instance is None:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: int) -> bool:
        """Delete a record.

        Args:
            id: The record ID.

        Returns:
            True if deleted, False if not found.
        """
        instance = await self.get(id)
        if instance is None:
            return False

        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def count(self) -> int:
        """Count total records.

        Returns:
            Total number of records.
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()

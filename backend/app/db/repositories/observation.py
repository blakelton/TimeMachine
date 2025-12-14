"""Observation repository."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.observation import Observation
from app.db.repositories.base import BaseRepository


class ObservationRepository(BaseRepository[Observation]):
    """Repository for observation operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Observation, session)

    async def get_by_camera(
        self, camera_id: int, limit: int | None = None
    ) -> list[Observation]:
        """Get observations for a camera.

        Args:
            camera_id: The camera ID.
            limit: Optional limit on number of results.

        Returns:
            List of observations for the camera.
        """
        query = (
            select(Observation)
            .where(Observation.camera_id == camera_id)
            .order_by(Observation.started_at.desc())
        )
        if limit:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active(self, camera_id: int | None = None) -> list[Observation]:
        """Get all active (running) observations.

        Args:
            camera_id: Optional camera ID filter.

        Returns:
            List of running observations.
        """
        query = select(Observation).where(Observation.status == "running")
        if camera_id is not None:
            query = query.where(Observation.camera_id == camera_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active_by_camera(self, camera_id: int) -> Observation | None:
        """Get the active observation for a camera.

        Args:
            camera_id: The camera ID.

        Returns:
            Active observation or None.
        """
        result = await self.session.execute(
            select(Observation).where(
                Observation.camera_id == camera_id,
                Observation.status == "running",
            )
        )
        return result.scalar_one_or_none()

    async def get_by_type(
        self,
        observation_type: str,
        camera_id: int | None = None,
        status: str | None = None,
    ) -> list[Observation]:
        """Get observations by type.

        Args:
            observation_type: The observation type ("timelapse" or "recording").
            camera_id: Optional camera ID filter.
            status: Optional status filter.

        Returns:
            List of observations of the specified type.
        """
        query = select(Observation).where(
            Observation.observation_type == observation_type
        )
        if camera_id is not None:
            query = query.where(Observation.camera_id == camera_id)
        if status is not None:
            query = query.where(Observation.status == status)
        result = await self.session.execute(
            query.order_by(Observation.started_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_folder_path(self, folder_path: str) -> Observation | None:
        """Get observation by folder path.

        Args:
            folder_path: The observation folder path.

        Returns:
            Observation or None if not found.
        """
        result = await self.session.execute(
            select(Observation).where(Observation.folder_path == folder_path)
        )
        return result.scalar_one_or_none()

    async def update_progress(
        self,
        observation_id: int,
        progress_current: int,
        size_bytes: int | None = None,
    ) -> Observation | None:
        """Update observation progress.

        Args:
            observation_id: The observation ID.
            progress_current: Current progress value.
            size_bytes: Optional updated size.

        Returns:
            Updated observation or None if not found.
        """
        update_data = {"progress_current": progress_current}
        if size_bytes is not None:
            update_data["size_bytes"] = size_bytes
        return await self.update(observation_id, **update_data)

    async def mark_completed(
        self, observation_id: int, size_bytes: int | None = None
    ) -> Observation | None:
        """Mark an observation as completed.

        Args:
            observation_id: The observation ID.
            size_bytes: Optional final size.

        Returns:
            Updated observation or None if not found.
        """
        update_data = {
            "status": "completed",
            "completed_at": datetime.utcnow(),
        }
        if size_bytes is not None:
            update_data["size_bytes"] = size_bytes
        return await self.update(observation_id, **update_data)

    async def mark_stopped(
        self, observation_id: int, size_bytes: int | None = None
    ) -> Observation | None:
        """Mark an observation as stopped (by user).

        Args:
            observation_id: The observation ID.
            size_bytes: Optional final size.

        Returns:
            Updated observation or None if not found.
        """
        update_data = {
            "status": "stopped",
            "completed_at": datetime.utcnow(),
        }
        if size_bytes is not None:
            update_data["size_bytes"] = size_bytes
        return await self.update(observation_id, **update_data)

    async def mark_failed(
        self, observation_id: int, error_message: str
    ) -> Observation | None:
        """Mark an observation as failed.

        Args:
            observation_id: The observation ID.
            error_message: Error description.

        Returns:
            Updated observation or None if not found.
        """
        return await self.update(
            observation_id,
            status="failed",
            completed_at=datetime.utcnow(),
            error_message=error_message,
        )

    async def update_notes(
        self, observation_id: int, notes: str
    ) -> Observation | None:
        """Update observation notes.

        Args:
            observation_id: The observation ID.
            notes: Notes content.

        Returns:
            Updated observation or None if not found.
        """
        return await self.update(observation_id, notes=notes)

    async def get_recent(
        self, limit: int = 10, camera_id: int | None = None
    ) -> list[Observation]:
        """Get recent observations.

        Args:
            limit: Maximum number of observations to return.
            camera_id: Optional camera ID filter.

        Returns:
            List of recent observations.
        """
        query = select(Observation).order_by(Observation.started_at.desc())
        if camera_id is not None:
            query = query.where(Observation.camera_id == camera_id)
        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def cleanup_stale_running(self) -> int:
        """Mark all running observations as failed (for startup cleanup).

        Returns:
            Number of observations cleaned up.
        """
        result = await self.session.execute(
            select(Observation).where(Observation.status == "running")
        )
        observations = list(result.scalars().all())

        for obs in observations:
            obs.status = "failed"
            obs.completed_at = datetime.utcnow()
            obs.error_message = "Observation interrupted by system restart"

        await self.session.flush()
        return len(observations)

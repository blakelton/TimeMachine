"""Job repository."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.job import Job
from app.db.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    """Repository for job operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Job, session)

    async def get_by_camera(self, camera_id: int) -> list[Job]:
        """Get all jobs for a camera.

        Args:
            camera_id: The camera ID.

        Returns:
            List of jobs for the camera.
        """
        result = await self.session.execute(
            select(Job)
            .where(Job.camera_id == camera_id)
            .order_by(Job.started_at.desc())
        )
        return list(result.scalars().all())

    async def get_running(self, camera_id: int | None = None) -> list[Job]:
        """Get all running jobs, optionally filtered by camera.

        Args:
            camera_id: Optional camera ID filter.

        Returns:
            List of running jobs.
        """
        query = select(Job).where(Job.status == "running")
        if camera_id is not None:
            query = query.where(Job.camera_id == camera_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_type(
        self, job_type: str, camera_id: int | None = None
    ) -> list[Job]:
        """Get jobs by type.

        Args:
            job_type: The job type ("recording", "timelapse", "capture").
            camera_id: Optional camera ID filter.

        Returns:
            List of jobs of the specified type.
        """
        query = select(Job).where(Job.job_type == job_type)
        if camera_id is not None:
            query = query.where(Job.camera_id == camera_id)
        result = await self.session.execute(query.order_by(Job.started_at.desc()))
        return list(result.scalars().all())

    async def get_active_by_camera_and_type(
        self, camera_id: int, job_type: str
    ) -> Job | None:
        """Get active (running) job for a camera and type.

        Args:
            camera_id: The camera ID.
            job_type: The job type.

        Returns:
            Active job or None.
        """
        result = await self.session.execute(
            select(Job).where(
                Job.camera_id == camera_id,
                Job.job_type == job_type,
                Job.status == "running",
            )
        )
        return result.scalar_one_or_none()

    async def mark_completed(
        self, job_id: int, output_path: str | None = None
    ) -> Job | None:
        """Mark a job as completed.

        Args:
            job_id: The job ID.
            output_path: Optional output file path.

        Returns:
            Updated job or None if not found.
        """
        return await self.update(
            job_id,
            status="completed",
            completed_at=datetime.utcnow(),
            output_path=output_path,
        )

    async def mark_failed(self, job_id: int, error_message: str) -> Job | None:
        """Mark a job as failed.

        Args:
            job_id: The job ID.
            error_message: Error description.

        Returns:
            Updated job or None if not found.
        """
        return await self.update(
            job_id,
            status="failed",
            completed_at=datetime.utcnow(),
            error_message=error_message,
        )

    async def mark_interrupted(self, job_id: int) -> Job | None:
        """Mark a job as interrupted (stopped by user or system).

        Args:
            job_id: The job ID.

        Returns:
            Updated job or None if not found.
        """
        return await self.update(
            job_id,
            status="interrupted",
            completed_at=datetime.utcnow(),
        )

    async def update_timelapse_progress(
        self, job_id: int, frame_count: int
    ) -> Job | None:
        """Update timelapse progress.

        Args:
            job_id: The job ID.
            frame_count: Current frame count.

        Returns:
            Updated job or None if not found.
        """
        return await self.update(job_id, timelapse_progress=frame_count)

    async def cleanup_stale_running_jobs(self) -> int:
        """Mark all running jobs as interrupted (for startup cleanup).

        Returns:
            Number of jobs cleaned up.
        """
        result = await self.session.execute(
            select(Job).where(Job.status == "running")
        )
        jobs = list(result.scalars().all())

        for job in jobs:
            job.status = "interrupted"
            job.completed_at = datetime.utcnow()
            job.error_message = "Job interrupted by system restart"

        await self.session.flush()
        return len(jobs)

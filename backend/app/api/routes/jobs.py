"""Job management API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.job import JobRepository
from app.db.session import get_session
from app.schemas.job import JobListResponse, JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = get_logger(__name__)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    session: Annotated[AsyncSession, Depends(get_session)],
    camera_id: int | None = None,
    job_type: str | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> JobListResponse:
    """List all jobs with optional filtering.

    Args:
        session: Database session
        camera_id: Filter by camera ID
        job_type: Filter by job type ('recording', 'timelapse', 'capture')
        status_filter: Filter by status ('pending', 'running', 'completed', 'failed', 'interrupted')
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of jobs and total count
    """
    repo = JobRepository(session)

    if job_type and camera_id:
        jobs = await repo.get_by_type(job_type, camera_id)
    elif job_type:
        jobs = await repo.get_by_type(job_type)
    elif camera_id:
        jobs = await repo.get_by_camera(camera_id)
    else:
        jobs = await repo.get_all(skip=skip, limit=limit)

    # Apply status filter if provided
    if status_filter:
        jobs = [j for j in jobs if j.status == status_filter]

    total = await repo.count()

    logger.info(
        "jobs_listed",
        total=total,
        camera_id=camera_id,
        job_type=job_type,
        status_filter=status_filter,
    )

    return JobListResponse(
        jobs=[JobResponse.model_validate(job) for job in jobs], total=total
    )


@router.get("/running", response_model=JobListResponse)
async def list_running_jobs(
    session: Annotated[AsyncSession, Depends(get_session)],
    camera_id: int | None = None,
) -> JobListResponse:
    """List all currently running jobs.

    Args:
        session: Database session
        camera_id: Optional camera ID filter

    Returns:
        List of running jobs
    """
    repo = JobRepository(session)
    jobs = await repo.get_running(camera_id)

    logger.info("running_jobs_listed", count=len(jobs), camera_id=camera_id)

    return JobListResponse(
        jobs=[JobResponse.model_validate(job) for job in jobs], total=len(jobs)
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> JobResponse:
    """Get a specific job by ID.

    Args:
        job_id: Job ID
        session: Database session

    Returns:
        Job details

    Raises:
        HTTPException: 404 if job not found
    """
    repo = JobRepository(session)
    job = await repo.get(job_id)

    if job is None:
        logger.warning("job_not_found", job_id=job_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    logger.info("job_retrieved", job_id=job_id, job_type=job.job_type, status=job.status)
    return JobResponse.model_validate(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> None:
    """Delete a job record.

    Note: This only deletes the job record, not the output files.

    Args:
        job_id: Job ID
        session: Database session

    Raises:
        HTTPException: 404 if job not found, 400 if job is running
    """
    repo = JobRepository(session)
    job = await repo.get(job_id)

    if job is None:
        logger.warning("job_delete_not_found", job_id=job_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    if job.status == "running":
        logger.warning("job_delete_running", job_id=job_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running job. Stop it first.",
        )

    await repo.delete(job_id)
    await session.commit()

    logger.info("job_deleted", job_id=job_id)

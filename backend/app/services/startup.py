"""Startup and shutdown cleanup services."""

import asyncio
import os
import signal
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.db.repositories.job import JobRepository
from app.db.session import AsyncSessionLocal
from app.services.camera import (
    preview_service,
    recording_service,
    timelapse_service,
)

logger = get_logger(__name__)


async def cleanup_stale_jobs() -> int:
    """Mark any running jobs as interrupted on startup.

    This handles cases where the application crashed or was restarted
    while jobs were running. Those jobs are no longer valid and should
    be marked as interrupted.

    Returns:
        Number of jobs cleaned up
    """
    async with AsyncSessionLocal() as session:
        job_repo = JobRepository(session)
        count = await job_repo.cleanup_stale_running_jobs()
        await session.commit()

    if count > 0:
        logger.info("stale_jobs_cleaned", count=count)

    return count


async def cleanup_orphan_gstreamer_processes() -> int:
    """Find and kill orphan GStreamer processes from previous runs.

    Looks for gst-launch-1.0 processes that may have been left running
    after a crash or restart.

    Returns:
        Number of processes killed
    """
    killed_count = 0

    try:
        # Find gst-launch processes
        proc = await asyncio.create_subprocess_shell(
            "pgrep -f 'gst-launch-1.0'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()

        if stdout:
            pids = stdout.decode().strip().split("\n")
            for pid_str in pids:
                if pid_str:
                    try:
                        pid = int(pid_str)
                        os.kill(pid, signal.SIGTERM)
                        killed_count += 1
                        logger.info("orphan_gstreamer_killed", pid=pid)
                    except (ValueError, ProcessLookupError, PermissionError) as e:
                        logger.warning(
                            "orphan_gstreamer_kill_failed", pid=pid_str, error=str(e)
                        )

    except Exception as e:
        logger.error("orphan_gstreamer_cleanup_failed", error=str(e))

    if killed_count > 0:
        logger.info("orphan_gstreamer_cleanup_complete", killed=killed_count)

    return killed_count


async def cleanup_orphan_libcamera_processes() -> int:
    """Find and kill orphan libcamera processes from previous runs.

    Returns:
        Number of processes killed
    """
    killed_count = 0

    try:
        # Find libcamera-still and libcamera-vid processes
        for process_name in ["libcamera-still", "libcamera-vid"]:
            proc = await asyncio.create_subprocess_shell(
                f"pgrep -f '{process_name}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()

            if stdout:
                pids = stdout.decode().strip().split("\n")
                for pid_str in pids:
                    if pid_str:
                        try:
                            pid = int(pid_str)
                            os.kill(pid, signal.SIGTERM)
                            killed_count += 1
                            logger.info(
                                "orphan_libcamera_killed",
                                pid=pid,
                                process=process_name,
                            )
                        except (ValueError, ProcessLookupError, PermissionError) as e:
                            logger.warning(
                                "orphan_libcamera_kill_failed",
                                pid=pid_str,
                                error=str(e),
                            )

    except Exception as e:
        logger.error("orphan_libcamera_cleanup_failed", error=str(e))

    if killed_count > 0:
        logger.info("orphan_libcamera_cleanup_complete", killed=killed_count)

    return killed_count


def ensure_media_directories() -> list[Path]:
    """Ensure all required media directories exist.

    Returns:
        List of created directories
    """
    created = []
    media_path = Path(settings.media_path)

    directories = [
        media_path / "recordings",
        media_path / "stills",
        media_path / "timelapses",
    ]

    for directory in directories:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created.append(directory)
            logger.info("media_directory_created", path=str(directory))

    return created


async def startup_cleanup() -> dict:
    """Perform all startup cleanup tasks.

    Returns:
        Summary of cleanup actions
    """
    logger.info("startup_cleanup_starting")

    summary = {
        "stale_jobs": 0,
        "orphan_gstreamer": 0,
        "orphan_libcamera": 0,
        "directories_created": [],
    }

    # Ensure media directories exist
    summary["directories_created"] = [
        str(d) for d in ensure_media_directories()
    ]

    # Cleanup stale jobs in database
    summary["stale_jobs"] = await cleanup_stale_jobs()

    # Cleanup orphan processes
    summary["orphan_gstreamer"] = await cleanup_orphan_gstreamer_processes()
    summary["orphan_libcamera"] = await cleanup_orphan_libcamera_processes()

    logger.info("startup_cleanup_complete", **summary)

    return summary


async def shutdown_cleanup() -> dict:
    """Perform graceful shutdown cleanup.

    Stops all active camera operations before shutdown.

    Returns:
        Summary of cleanup actions
    """
    logger.info("shutdown_cleanup_starting")

    summary = {
        "previews_stopped": 0,
        "recordings_stopped": 0,
        "timelapses_stopped": 0,
    }

    # Stop all previews
    try:
        await preview_service.stop_all_previews()
        summary["previews_stopped"] = len(preview_service._previews) if hasattr(preview_service, '_previews') else 0
    except Exception as e:
        logger.error("shutdown_preview_stop_failed", error=str(e))

    # Stop all recordings with Job tracking
    try:
        async with AsyncSessionLocal() as session:
            results = await recording_service.stop_all_recordings(session)
            summary["recordings_stopped"] = len([r for r in results if r[1]])
    except Exception as e:
        logger.error("shutdown_recording_stop_failed", error=str(e))

    # Stop all timelapses with Job tracking
    try:
        async with AsyncSessionLocal() as session:
            results = await timelapse_service.stop_all_timelapses(session)
            summary["timelapses_stopped"] = len([r for r in results if r[1]])
    except Exception as e:
        logger.error("shutdown_timelapse_stop_failed", error=str(e))

    logger.info("shutdown_cleanup_complete", **summary)

    return summary

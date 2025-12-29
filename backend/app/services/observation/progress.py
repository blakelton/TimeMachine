"""Progress tracking and completion monitoring for observations."""

import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.observation import Observation
from app.db.repositories.observation import ObservationRepository
from app.services.camera.pipeline import PipelineState
from app.services.camera.recording import recording_service
from app.services.camera.timelapse import timelapse_service

from .completion import CompletionReason, CompletionResult

logger = get_logger(__name__)


async def check_pipeline_running(
    camera_id: int,
    observation_type: str,
) -> tuple[bool, int]:
    """Check if the observation pipeline is still running.

    Returns:
        (is_running, current_progress)
    """
    if observation_type == "timelapse":
        is_running = timelapse_service.is_running(camera_id)
        progress = timelapse_service.get_timelapse_progress(camera_id)
        actual_progress = progress[0] if progress else 0
    else:  # recording
        state = recording_service.get_recording_state(camera_id)
        is_running = state == PipelineState.RUNNING
        uptime = recording_service.get_recording_uptime(camera_id)
        actual_progress = int(uptime) if uptime else 0

    return is_running, actual_progress


async def analyze_timelapse_completion(
    camera_id: int,
    observation: Observation,
    actual_progress: int,
) -> CompletionResult:
    """Analyze why a timelapse stopped and determine completion status.

    DURATION IS KING: Duration completion is always success, even if
    we didn't get all expected frames.
    """
    health = timelapse_service.get_timelapse_health(camera_id)
    completed_by_duration = health.get("completed_by_duration", False) if health else False
    frames_incomplete = health.get("frames_incomplete", False) if health else False

    # DURATION IS KING: Duration completion is always success
    if completed_by_duration:
        if frames_incomplete:
            note = (
                f"Completed by duration. Captured {actual_progress} frames "
                f"(expected {observation.progress_total}). "
                "Some frames missed due to camera issues."
            )
        else:
            note = f"Completed by duration with {actual_progress} frames."

        return CompletionResult(
            completed=True,
            reason=CompletionReason.DURATION_REACHED,
            actual_progress=actual_progress,
            health_info=health,
            note=note,
        )

    # Check frame count completion
    if observation.progress_total and actual_progress >= observation.progress_total:
        return CompletionResult(
            completed=True,
            reason=CompletionReason.FRAMES_REACHED,
            actual_progress=actual_progress,
            health_info=health,
            note=f"Target of {observation.progress_total} frames reached.",
        )

    # Pipeline crashed
    return CompletionResult(
        completed=False,
        reason=CompletionReason.PIPELINE_CRASHED,
        actual_progress=actual_progress,
        health_info=health,
        note=f"Pipeline stopped unexpectedly after {actual_progress} frames",
    )


async def analyze_recording_completion(
    observation: Observation,
    actual_progress: int,
) -> CompletionResult:
    """Analyze why a recording stopped."""
    if observation.progress_total and actual_progress >= observation.progress_total:
        return CompletionResult(
            completed=True,
            reason=CompletionReason.DURATION_REACHED,
            actual_progress=actual_progress,
            health_info=None,
            note=f"Recording reached target duration of {actual_progress}s.",
        )

    return CompletionResult(
        completed=False,
        reason=CompletionReason.PIPELINE_CRASHED,
        actual_progress=actual_progress,
        health_info=None,
        note=f"Recording stopped unexpectedly after {actual_progress}s",
    )


async def handle_successful_completion(
    observation_id: int,
    camera_id: int,
    observation: Observation,
    result: CompletionResult,
    session: AsyncSession,
    assemble_timelapse_fn,
    get_observation_size_fn,
) -> None:
    """Handle successful observation completion."""
    obs_repo = ObservationRepository(session)

    # Log completion with appropriate event name
    if result.reason == CompletionReason.DURATION_REACHED and observation.observation_type == "timelapse":
        logger.info(
            "observation_completed_by_duration",
            observation_id=observation_id,
            camera_id=camera_id,
            frame_count=result.actual_progress,
            expected_frames=observation.progress_total,
            frames_incomplete=result.health_info.get("frames_incomplete", False) if result.health_info else False,
        )
    else:
        logger.info(
            "observation_completed",
            observation_id=observation_id,
            camera_id=camera_id,
            reason=result.reason.name if result.reason else "unknown",
            progress=result.actual_progress,
        )

    # Assemble video for timelapses
    if observation.observation_type == "timelapse":
        await assemble_timelapse_fn(
            observation_id, camera_id, session
        )

    # Calculate final folder size
    size_bytes = await get_observation_size_fn(observation.folder_path)

    # Update database
    if result.note:
        await obs_repo.update(
            observation_id,
            progress_current=result.actual_progress,
            notes=result.note,
        )
    await obs_repo.mark_completed(observation_id, size_bytes)
    await session.commit()


async def handle_failed_completion(
    observation_id: int,
    camera_id: int,
    observation: Observation,
    result: CompletionResult,
    session: AsyncSession,
    assemble_timelapse_fn,
) -> None:
    """Handle observation that stopped unexpectedly."""
    obs_repo = ObservationRepository(session)

    logger.warning(
        "observation_pipeline_crashed",
        observation_id=observation_id,
        camera_id=camera_id,
        observation_type=observation.observation_type,
        actual_progress=result.actual_progress,
    )

    # Try to salvage what we can for timelapses
    if observation.observation_type == "timelapse" and result.actual_progress > 0:
        await assemble_timelapse_fn(
            observation_id, camera_id, session, partial=True
        )

    await obs_repo.mark_failed(observation_id, result.note or "Unknown error")
    await session.commit()


async def progress_tracker_loop(
    observation_id: int,
    camera_id: int,
    observation_type: str,
    handle_successful_completion_fn,
    handle_failed_completion_fn,
    cleanup_after_completion_fn,
) -> None:
    """Background loop that monitors observation health.

    Detects when the underlying pipeline has crashed and updates
    the observation status accordingly.
    """
    from app.db.session import SessionFactory

    check_interval = 3.0  # Check every 3 seconds
    await asyncio.sleep(2.0)  # Grace period for pipeline to start

    while True:
        try:
            # Check if pipeline is still running
            is_running, actual_progress = await check_pipeline_running(
                camera_id, observation_type
            )

            if not is_running:
                # Pipeline stopped - analyze why and handle completion
                async with SessionFactory() as session:
                    obs_repo = ObservationRepository(session)
                    observation = await obs_repo.get(observation_id)

                    if not observation:
                        logger.error("observation_not_found", observation_id=observation_id)
                        break

                    # Analyze completion
                    if observation_type == "timelapse":
                        result = await analyze_timelapse_completion(
                            camera_id, observation, actual_progress
                        )
                    else:
                        result = await analyze_recording_completion(
                            observation, actual_progress
                        )

                    # Handle based on completion status
                    if result.completed:
                        await handle_successful_completion_fn(
                            observation_id, camera_id, observation, result, session
                        )
                    else:
                        await handle_failed_completion_fn(
                            observation_id, camera_id, observation, result, session
                        )

                # Cleanup
                await cleanup_after_completion_fn(camera_id)
                break

            await asyncio.sleep(check_interval)

        except asyncio.CancelledError:
            logger.debug("progress_tracker_cancelled", observation_id=observation_id)
            break
        except Exception as e:
            logger.error("progress_tracker_error", observation_id=observation_id, error=str(e))
            await asyncio.sleep(check_interval)

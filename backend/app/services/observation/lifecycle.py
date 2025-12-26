"""Observation lifecycle management - starting and stopping observations."""

import asyncio
from datetime import timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ObservationStatus
from app.core.logging import get_logger
from app.db.models.observation import Observation
from app.db.repositories.camera import CameraRepository
from app.db.repositories.observation import ObservationRepository
from app.db.repositories.output_config import OutputConfigRepository
from app.schemas.observation import (
    RecordingObservationConfig,
    TimelapseObservationConfig,
)
from app.services.camera.pipeline import PipelineState
from app.services.camera.preview import preview_service
from app.services.camera.recording import recording_service
from app.services.camera.timelapse import TimelapseConfig, timelapse_service

from .utils import (
    calculate_end_datetime,
    calculate_total_frames,
    interval_to_seconds,
    now,
)

logger = get_logger(__name__)


async def start_timelapse_observation(
    camera,
    folder_path: Path,
    config: TimelapseObservationConfig | None,
    session: AsyncSession,
    active_observations: dict,
    preview_stopped_for: dict,
    start_progress_tracker_fn,
    start_live_preview_generator_fn,
) -> tuple[bool, str, Observation | None]:
    """Start a timelapse observation."""
    if not config:
        config = TimelapseObservationConfig()

    # Calculate interval in seconds
    interval_seconds = interval_to_seconds(config.interval_value, config.interval_unit)

    # Calculate total frames and target end time
    total_frames = calculate_total_frames(
        interval_seconds,
        config.end_mode,
        config.end_datetime,
        config.duration_value,
        config.duration_unit,
    )
    target_end_at = calculate_end_datetime(
        config.end_mode,
        config.end_datetime,
        config.duration_value,
        config.duration_unit,
    )

    # Create frames directory within observation folder
    frames_dir = folder_path / "frames"
    frames_dir.mkdir(exist_ok=True)

    # Get environment device info for overlay if configured
    env_device_type: str | None = None
    env_temp_unit: str = "C"
    polling_service = None

    if config.env_overlay_device_id is not None:
        # Import and get the environment polling service
        from app.services.environment.polling import get_polling_service
        from app.db.repositories.environment_device import EnvironmentDeviceRepository

        polling_service = get_polling_service()

        # Get device info for sensor type and temp unit
        device_repo = EnvironmentDeviceRepository(session)
        env_device = await device_repo.get(config.env_overlay_device_id)
        if env_device:
            env_device_type = env_device.device_type
            env_temp_unit = env_device.temperature_unit or "C"

    # Create timelapse config for existing service
    tl_config = TimelapseConfig(
        camera_id=camera.id,
        interval_seconds=interval_seconds,
        total_frames=total_frames,
        quality=config.quality,
        resolution=(config.resolution_width, config.resolution_height),
        output_fps=config.output_fps,
        env_overlay_device_id=config.env_overlay_device_id,
        env_overlay_position=config.env_overlay_position,
        env_overlay_show_graph=config.env_overlay_show_graph,
        env_overlay_device_type=env_device_type,
        env_overlay_temp_unit=env_temp_unit,
    )

    # For USB cameras, stop the preview stream to free the device for capture
    # The preview will be restarted when the observation stops
    if camera.camera_type == "usb":
        preview_state = preview_service.get_preview_state(camera.id)
        if preview_state == PipelineState.RUNNING:
            preview_port = preview_service.get_preview_port(camera.id)
            # Get FPS from output config for later restart
            config_repo = OutputConfigRepository(session)
            output_config = await config_repo.get_current()
            preview_fps = output_config.dashboard_preview_fps if output_config else 10

            logger.info(
                "observation_stopping_preview",
                camera_id=camera.id,
                reason="timelapse_capture_requires_device",
            )
            await preview_service.stop_preview(camera.id)
            # Track so we can restart when observation stops
            preview_stopped_for[camera.id] = {
                "port": preview_port,
                "device_path": camera.device_path,
                "camera_type": camera.camera_type,
                "fps": preview_fps,
            }
            # Give the device time to be released
            await asyncio.sleep(0.5)

    # Create observation record first
    obs_repo = ObservationRepository(session)
    observation = await obs_repo.create(
        camera_id=camera.id,
        observation_type="timelapse",
        status=ObservationStatus.RUNNING,
        folder_path=str(folder_path),
        config=config.model_dump(),
        progress_current=0,
        progress_total=total_frames,
        size_bytes=0,
        target_end_at=target_end_at,
    )
    await session.commit()

    # Start the timelapse using existing service
    # Pass our frames directory to store frames in the observation folder
    # Include hardware_id for USB camera recovery support
    # Include target_end_at for timeout during recovery mode
    # Include polling_service for environment overlay
    success, message, job_id = await timelapse_service.start_timelapse(
        camera_id=camera.id,
        device_path=camera.device_path,
        camera_type=camera.camera_type,
        config=tl_config,
        session=session,
        frames_dir=frames_dir,
        hardware_id=camera.hardware_id,
        target_end_time=target_end_at,
        polling_service=polling_service,
    )

    if not success:
        # Mark observation as failed
        await obs_repo.mark_failed(observation.id, message)
        await session.commit()
        return False, message, None

    # Link job to observation
    observation = await obs_repo.update(observation.id, job_id=job_id)
    await session.commit()

    # Track active observation
    active_observations[camera.id] = observation.id

    # Wait briefly and verify the timelapse is running
    await asyncio.sleep(0.5)
    progress = timelapse_service.get_timelapse_progress(camera.id)
    if progress is None:
        # Timelapse failed immediately
        logger.warning(
            "timelapse_immediate_failure",
            observation_id=observation.id,
            camera_id=camera.id,
        )
        await obs_repo.mark_failed(
            observation.id,
            "Timelapse failed to start - check camera connection",
        )
        await session.commit()
        del active_observations[camera.id]
        return False, "Timelapse failed to start - check camera connection", None

    # Start progress tracking task (watchdog for crash detection)
    start_progress_tracker_fn(observation.id, camera.id, "timelapse")

    # Start live preview generator for real-time timelapse preview
    # Generates preview initially, then every output_fps frames (1 second of footage)
    start_live_preview_generator_fn(observation.id, folder_path, output_fps=config.output_fps)

    logger.info(
        "timelapse_observation_started",
        observation_id=observation.id,
        camera_id=camera.id,
        folder=str(folder_path),
        interval=interval_seconds,
        total_frames=total_frames,
        preview_stopped=camera.id in preview_stopped_for,
    )

    return True, "Timelapse observation started", observation


async def start_recording_observation(
    camera,
    folder_path: Path,
    config: RecordingObservationConfig | None,
    session: AsyncSession,
    active_observations: dict,
    preview_stopped_for: dict,
    start_progress_tracker_fn,
) -> tuple[bool, str, Observation | None]:
    """Start a recording observation."""
    if not config:
        config = RecordingObservationConfig()

    # Calculate duration and target end
    duration_seconds: int | None = None
    target_end_at = None

    if config.end_mode == "duration" and config.duration_value and config.duration_unit:
        duration_seconds = interval_to_seconds(config.duration_value, config.duration_unit)
        target_end_at = now() + timedelta(seconds=duration_seconds)
    elif config.end_mode == "datetime" and config.end_datetime:
        target_end_at = config.end_datetime
        duration_seconds = int((target_end_at - now()).total_seconds())

    # For USB cameras, stop the preview stream to free the device for recording
    # The preview will be restarted when the observation stops
    if camera.camera_type == "usb":
        preview_state = preview_service.get_preview_state(camera.id)
        if preview_state == PipelineState.RUNNING:
            preview_port = preview_service.get_preview_port(camera.id)
            # Get FPS from output config for later restart
            config_repo = OutputConfigRepository(session)
            output_config = await config_repo.get_current()
            preview_fps = output_config.dashboard_preview_fps if output_config else 10

            logger.info(
                "observation_stopping_preview",
                camera_id=camera.id,
                reason="recording_requires_device",
            )
            await preview_service.stop_preview(camera.id)
            # Track so we can restart when observation stops
            preview_stopped_for[camera.id] = {
                "port": preview_port,
                "device_path": camera.device_path,
                "camera_type": camera.camera_type,
                "fps": preview_fps,
            }
            # Give the device time to be released
            await asyncio.sleep(0.5)

    # Create observation record
    obs_repo = ObservationRepository(session)
    observation = await obs_repo.create(
        camera_id=camera.id,
        observation_type="recording",
        status=ObservationStatus.RUNNING,
        folder_path=str(folder_path),
        config=config.model_dump(),
        progress_current=0,
        progress_total=duration_seconds,
        size_bytes=0,
        target_end_at=target_end_at,
    )
    await session.commit()

    # Output file goes in observation folder
    output_file = folder_path / "output"

    # Start recording using existing service
    success, message, job_id = await recording_service.start_recording(
        camera_id=camera.id,
        device_path=camera.device_path,
        camera_type=camera.camera_type,
        session=session,
        duration_seconds=duration_seconds,
        filename=str(output_file),
    )

    if not success:
        await obs_repo.mark_failed(observation.id, message)
        await session.commit()
        return False, message, None

    # Link job to observation
    observation = await obs_repo.update(observation.id, job_id=job_id)
    await session.commit()

    # Track active observation
    active_observations[camera.id] = observation.id

    # Wait briefly and verify the pipeline is still running
    # GStreamer pipelines can crash immediately if codec/resolution is unsupported
    await asyncio.sleep(0.5)
    pipeline_state = recording_service.get_recording_state(camera.id)
    if pipeline_state != PipelineState.RUNNING:
        # Pipeline crashed immediately after starting
        logger.warning(
            "recording_pipeline_immediate_crash",
            observation_id=observation.id,
            camera_id=camera.id,
            pipeline_state=pipeline_state.value if pipeline_state else "none",
        )
        await obs_repo.mark_failed(
            observation.id,
            "Recording failed to start - camera may not support h264 encoding at this resolution",
        )
        await session.commit()
        del active_observations[camera.id]
        return False, "Recording failed - camera may not support h264 encoding at this resolution", None

    # Start progress tracking task (watchdog for crash detection)
    start_progress_tracker_fn(observation.id, camera.id, "recording")

    logger.info(
        "recording_observation_started",
        observation_id=observation.id,
        camera_id=camera.id,
        folder=str(folder_path),
        duration=duration_seconds,
        preview_stopped=camera.id in preview_stopped_for,
    )

    return True, "Recording observation started", observation


async def stop_observation(
    observation_id: int,
    session: AsyncSession,
    assemble_video: bool,
    active_observations: dict,
    stop_progress_tracker_fn,
    stop_live_preview_generator_fn,
    calculate_folder_size_fn,
    restart_preview_if_stopped_fn,
    update_observation_metadata_fn,
) -> tuple[bool, str, str | None]:
    """Stop an observation.

    Args:
        observation_id: Observation ID
        session: Database session
        assemble_video: Whether to assemble timelapse frames into video
        active_observations: Dict of active observations
        stop_progress_tracker_fn: Function to stop progress tracker
        stop_live_preview_generator_fn: Function to stop preview generator
        calculate_folder_size_fn: Function to calculate folder size
        restart_preview_if_stopped_fn: Function to restart preview if stopped
        update_observation_metadata_fn: Function to update observation metadata

    Returns:
        Tuple of (success, message, output_path)
    """
    obs_repo = ObservationRepository(session)
    observation = await obs_repo.get(observation_id)

    if not observation:
        return False, f"Observation {observation_id} not found", None

    if observation.status != ObservationStatus.RUNNING:
        return False, f"Observation {observation_id} is not running", None

    camera_id = observation.camera_id
    folder_path = Path(observation.folder_path)

    # Stop progress tracker
    stop_progress_tracker_fn(observation_id)

    # Stop live preview generator if running
    stop_live_preview_generator_fn(observation_id)

    # Stop underlying service
    if observation.observation_type == "timelapse":
        success, message, output_path = await timelapse_service.stop_timelapse(
            camera_id, session, assemble_video
        )
    else:
        success, message, output_path = await recording_service.stop_recording(
            camera_id, session
        )

    # Calculate final size (async to avoid blocking)
    size_bytes = await calculate_folder_size_fn(folder_path)

    # Update observation status
    if success:
        await obs_repo.mark_stopped(observation_id, size_bytes)
    else:
        await obs_repo.mark_failed(observation_id, message)
    await session.commit()

    # Refresh observation for metadata update
    observation = await obs_repo.get(observation_id)
    if observation:
        update_observation_metadata_fn(folder_path, observation)

    # Remove from active tracking
    if camera_id in active_observations:
        del active_observations[camera_id]

    # Restart preview if we stopped it for this observation
    await restart_preview_if_stopped_fn(camera_id)

    logger.info(
        "observation_stopped",
        observation_id=observation_id,
        camera_id=camera_id,
        success=success,
        output_path=output_path,
    )

    return success, message, output_path

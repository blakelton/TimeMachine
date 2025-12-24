"""Timelapse capture session with automatic recovery."""

import asyncio
import json
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from app.services.environment.polling import EnvironmentPollingService

from app.core.logging import get_logger
from app.core.resources import check_resources_available
from app.services.camera.capture import CaptureService
from app.services.camera.overlay import EnvironmentOverlayService
from app.services.system.stats import check_system_pressure, get_adaptive_delay_seconds

from .config import TimelapseConfig

logger = get_logger(__name__)

# Recovery settings
MAX_CONSECUTIVE_FAILURES = 10  # Trigger recovery after this many failures
RECOVERY_BACKOFF_SECONDS = 30  # Wait time during recovery attempts
MAX_RECOVERY_ATTEMPTS = 5  # Max recovery attempts before giving up on this cycle


class CaptureState(Enum):
    """States in the capture loop state machine."""
    CHECK_COMPLETION = auto()   # Check if timelapse should end
    CHECK_RECOVERY = auto()     # Handle recovery mode
    CHECK_RESOURCES = auto()    # Verify system resources
    CAPTURE_FRAME = auto()      # Capture a single frame
    WAIT_INTERVAL = auto()      # Wait for next capture
    COMPLETED = auto()          # Timelapse finished
    STOPPED = auto()            # Stopped by user


class TimelapseSession:
    """Active timelapse capture session with automatic recovery."""

    def __init__(
        self,
        config: TimelapseConfig,
        device_path: str,
        camera_type: str,
        job_id: int | None,
        timelapse_dir: Path,
        hardware_id: str | None = None,
        device_resolver: Callable[[str], str | None] | None = None,
        target_end_time: datetime | None = None,
        polling_service: "EnvironmentPollingService | None" = None,
    ):
        self.config = config
        self.device_path = device_path
        self.camera_type = camera_type
        self.job_id = job_id
        self.timelapse_dir = timelapse_dir
        self.hardware_id = hardware_id  # For USB camera recovery
        self._device_resolver = device_resolver  # Async function to resolve hardware_id
        self.target_end_time = target_end_time  # When timelapse should end (for timeout)
        self.frame_count = 0
        self.started_at = datetime.now()
        self._stop_event = asyncio.Event()
        self._capture_task: asyncio.Task | None = None
        self._capture_service = CaptureService()

        # Recovery tracking
        self._consecutive_failures = 0
        self._total_failures = 0
        self._recovery_attempts = 0
        self._in_recovery_mode = False
        self._gap_start_frame: int | None = None
        self._events: list[dict] = []  # Event log for this session

        # Completion tracking
        self._completed_by_duration = False  # True if stopped due to duration, not frame count
        self._frames_incomplete = False  # True if we missed frames due to camera issues

        # Environment overlay service
        self._overlay_service: EnvironmentOverlayService | None = None
        self._polling_service = polling_service
        if config.env_overlay_device_id is not None:
            self._overlay_service = EnvironmentOverlayService(
                device_id=config.env_overlay_device_id,
                position=config.env_overlay_position,
                show_graph=config.env_overlay_show_graph,
                device_type=config.env_overlay_device_type,
                temperature_unit=config.env_overlay_temp_unit,
            )

    @property
    def is_running(self) -> bool:
        """Check if session is running."""
        return self._capture_task is not None and not self._capture_task.done()

    def get_progress(self) -> tuple[int, int | None]:
        """Get current progress.

        Returns:
            Tuple of (current_frame, total_frames or None if unlimited)
        """
        return self.frame_count, self.config.total_frames

    def get_events(self) -> list[dict]:
        """Get all logged events for this session."""
        return self._events.copy()

    def _log_event(self, event_type: str, message: str, **extra) -> None:
        """Log an event to the session event list and save to file.

        Args:
            event_type: Type of event (gap_start, gap_end, recovery, error, etc.)
            message: Human-readable message
            **extra: Additional event data
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message,
            "frame_count": self.frame_count,
            **extra,
        }
        self._events.append(event)

        # Also log to structured logger
        logger.info(
            f"timelapse_event_{event_type}",
            camera_id=self.config.camera_id,
            message=message,
            frame_count=self.frame_count,
            **extra,
        )

        # Save events to file
        self._save_events()

    def _save_events(self) -> None:
        """Save events to JSON file in the timelapse directory."""
        try:
            events_file = self.timelapse_dir / "events.json"
            with open(events_file, "w") as f:
                json.dump(self._events, f, indent=2)
        except Exception as e:
            logger.warning(
                "timelapse_events_save_failed",
                camera_id=self.config.camera_id,
                error=str(e),
            )

    async def _attempt_recovery(self) -> bool:
        """Attempt to recover the camera connection.

        Returns:
            True if recovery successful, False otherwise
        """
        if not self.hardware_id or not self._device_resolver:
            # Can't recover without hardware_id and resolver
            return False

        self._recovery_attempts += 1
        logger.info(
            "timelapse_recovery_attempting",
            camera_id=self.config.camera_id,
            attempt=self._recovery_attempts,
            hardware_id=self.hardware_id,
        )

        try:
            # Try to resolve the hardware_id to a new device path
            new_device_path = await self._device_resolver(self.hardware_id)

            if new_device_path:
                old_path = self.device_path
                self.device_path = new_device_path
                self._log_event(
                    "recovery_success",
                    f"Camera recovered: {old_path} -> {new_device_path}",
                    old_device_path=old_path,
                    new_device_path=new_device_path,
                    recovery_attempt=self._recovery_attempts,
                )
                self._consecutive_failures = 0
                self._recovery_attempts = 0
                return True
            else:
                logger.debug(
                    "timelapse_recovery_device_not_found",
                    camera_id=self.config.camera_id,
                    hardware_id=self.hardware_id,
                )
                return False

        except Exception as e:
            logger.warning(
                "timelapse_recovery_error",
                camera_id=self.config.camera_id,
                error=str(e),
            )
            return False

    async def start(self) -> bool:
        """Start the timelapse capture loop.

        Returns:
            True if started successfully
        """
        if self.is_running:
            return False

        self._stop_event.clear()
        self._capture_task = asyncio.create_task(self._capture_loop())
        return True

    async def stop(self) -> int:
        """Stop the timelapse capture.

        Returns:
            Number of frames captured
        """
        self._stop_event.set()
        if self._capture_task:
            try:
                await asyncio.wait_for(self._capture_task, timeout=10.0)
            except asyncio.TimeoutError:
                self._capture_task.cancel()
                try:
                    await self._capture_task
                except asyncio.CancelledError:
                    pass
        return self.frame_count

    async def _wait_or_stop(self, delay_seconds: float) -> bool:
        """Wait for a delay or until stop is requested.

        Args:
            delay_seconds: Number of seconds to wait

        Returns:
            True if stop was requested, False if timeout occurred normally
        """
        try:
            await asyncio.wait_for(
                self._stop_event.wait(),
                timeout=delay_seconds,
            )
            return True  # Stop requested
        except asyncio.TimeoutError:
            return False  # Normal timeout

    async def _check_completion(self) -> tuple[bool, str | None]:
        """Check if timelapse should complete.

        Returns:
            (should_complete, reason)
        """
        # DURATION IS KING: Check target_end_time FIRST - this is the absolute authority
        if self.target_end_time and datetime.now() >= self.target_end_time:
            self._completed_by_duration = True
            # Log if we didn't capture expected frames due to gaps
            if self.config.total_frames and self.frame_count < self.config.total_frames:
                self._frames_incomplete = True
                missed = self.config.total_frames - self.frame_count
                self._log_event(
                    "duration_complete_incomplete_frames",
                    f"Duration reached with {self.frame_count}/{self.config.total_frames} frames "
                    f"({missed} frames missed due to camera issues)",
                    expected_frames=self.config.total_frames,
                    actual_frames=self.frame_count,
                    missed_frames=missed,
                    total_failures=self._total_failures,
                )
            return True, "duration_reached"

        # Secondary check: frame count target (only if no duration set)
        if self.config.total_frames and self.frame_count >= self.config.total_frames:
            # Only stop on frame count if there's no target_end_time
            if not self.target_end_time:
                return True, "target_frames_reached"

        return False, None

    async def _handle_recovery_mode(self) -> CaptureState:
        """Handle recovery mode with backoff.

        Returns:
            Next state to transition to
        """
        if self._recovery_attempts >= MAX_RECOVERY_ATTEMPTS:
            # Reset recovery attempts and wait longer before trying again
            self._recovery_attempts = 0
            logger.info(
                "timelapse_recovery_cooldown",
                camera_id=self.config.camera_id,
                consecutive_failures=self._consecutive_failures,
            )
            # Wait for longer backoff period
            if await self._wait_or_stop(RECOVERY_BACKOFF_SECONDS * 2):
                return CaptureState.STOPPED
            return CaptureState.CHECK_RECOVERY

        recovered = await self._attempt_recovery()
        if recovered:
            self._in_recovery_mode = False
            self._log_recovery_gap_end()
            return CaptureState.CHECK_RESOURCES

        # Recovery failed, wait before next attempt
        if await self._wait_or_stop(RECOVERY_BACKOFF_SECONDS):
            return CaptureState.STOPPED
        return CaptureState.CHECK_RECOVERY

    def _log_recovery_gap_end(self) -> None:
        """Log the end of a capture gap."""
        if self._gap_start_frame is not None:
            gap_duration = self._consecutive_failures * self.config.interval_seconds
            self._log_event(
                "gap_end",
                f"Camera recovered after {self._consecutive_failures} missed frames (~{gap_duration}s gap)",
                gap_start_frame=self._gap_start_frame,
                missed_frames=self._consecutive_failures,
                gap_duration_seconds=gap_duration,
            )
            self._gap_start_frame = None

    async def _check_system_resources(self) -> tuple[bool, float]:
        """Check system resources and calculate any needed throttle delay.

        Returns:
            (resources_ok, throttle_delay_seconds)
        """
        # Check disk/memory availability
        resources_ok, reason = await check_resources_available(
            f"timelapse_camera_{self.config.camera_id}",
            min_memory_mb=50,
            min_disk_mb=100,
        )
        if not resources_ok:
            logger.warning(
                "timelapse_resource_issue",
                camera_id=self.config.camera_id,
                reason=reason,
            )
            return False, 30.0  # Wait 30s before retry

        # Check system pressure for adaptive throttling
        is_healthy, pressure_reason, pressure_metrics = check_system_pressure()
        if not is_healthy:
            throttle_delay = get_adaptive_delay_seconds()
            if throttle_delay > 0:
                logger.info(
                    "timelapse_throttling",
                    camera_id=self.config.camera_id,
                    reason=pressure_reason,
                    delay_seconds=throttle_delay,
                    metrics=pressure_metrics,
                )
                return True, throttle_delay

        return True, 0.0

    async def _capture_single_frame(self) -> bool:
        """Capture a single frame and handle success/failure.

        Returns:
            True if capture succeeded
        """
        frame_filename = f"frame_{self.frame_count:06d}"
        output_file = self.timelapse_dir / f"{frame_filename}.jpg"

        success, message, filepath = await self._capture_service.capture_image(
            camera_id=self.config.camera_id,
            device_path=self.device_path,
            camera_type=self.camera_type,
            filename=str(output_file.with_suffix("")),
        )

        if success:
            await self._handle_capture_success(filepath)
            return True
        else:
            self._handle_capture_failure(message)
            return False

    async def _handle_capture_success(self, filepath: str | None) -> None:
        """Handle successful frame capture."""
        # Reset failure counters on success
        if self._consecutive_failures > 0:
            logger.info(
                "timelapse_recovered_naturally",
                camera_id=self.config.camera_id,
                consecutive_failures=self._consecutive_failures,
            )
        self._consecutive_failures = 0
        self.frame_count += 1

        # Apply environment overlay if configured
        if self._overlay_service and self._polling_service and filepath:
            await self._apply_frame_overlay(filepath)

        logger.debug(
            "timelapse_frame_captured",
            camera_id=self.config.camera_id,
            frame=self.frame_count,
            filepath=filepath,
        )

    def _handle_capture_failure(self, message: str) -> None:
        """Handle failed frame capture."""
        self._consecutive_failures += 1
        self._total_failures += 1

        # Log start of gap on first failure
        if self._consecutive_failures == 1:
            self._gap_start_frame = self.frame_count
            self._log_event(
                "gap_start",
                f"Capture failed: {message[:100]}",
                error=message[:200],
            )

        logger.warning(
            "timelapse_frame_failed",
            camera_id=self.config.camera_id,
            frame=self.frame_count,
            consecutive_failures=self._consecutive_failures,
            error=message,
        )

        # Check if we should enter recovery mode
        if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            if not self._in_recovery_mode:
                self._in_recovery_mode = True
                self._log_event(
                    "recovery_start",
                    f"Entering recovery mode after {self._consecutive_failures} consecutive failures",
                    consecutive_failures=self._consecutive_failures,
                )

    async def _apply_frame_overlay(self, filepath: str) -> None:
        """Apply environment overlay to captured frame."""
        try:
            overlay_applied = await self._overlay_service.apply_overlay(
                image_path=Path(filepath),
                frame_number=self.frame_count,
                polling_service=self._polling_service,
            )
            if overlay_applied:
                logger.debug(
                    "timelapse_overlay_applied",
                    camera_id=self.config.camera_id,
                    frame=self.frame_count,
                )
        except Exception as e:
            logger.warning(
                "timelapse_overlay_error",
                camera_id=self.config.camera_id,
                frame=self.frame_count,
                error=str(e),
            )

    async def _state_check_completion(self) -> CaptureState:
        """Handle CHECK_COMPLETION state."""
        should_complete, reason = await self._check_completion()
        if should_complete:
            logger.info(
                "timelapse_completed",
                camera_id=self.config.camera_id,
                reason=reason,
                frame_count=self.frame_count,
                target_frames=self.config.total_frames,
            )
            return CaptureState.COMPLETED
        elif self._in_recovery_mode:
            return CaptureState.CHECK_RECOVERY
        else:
            return CaptureState.CHECK_RESOURCES

    async def _state_check_resources(self) -> CaptureState:
        """Handle CHECK_RESOURCES state."""
        resources_ok, delay = await self._check_system_resources()
        if not resources_ok:
            await asyncio.sleep(delay)
            return CaptureState.CHECK_COMPLETION
        if delay > 0:
            await asyncio.sleep(delay)
        return CaptureState.CAPTURE_FRAME

    async def _state_capture_frame(self) -> CaptureState:
        """Handle CAPTURE_FRAME state."""
        await self._capture_single_frame()
        return CaptureState.WAIT_INTERVAL

    async def _state_wait_interval(self) -> CaptureState:
        """Handle WAIT_INTERVAL state."""
        if await self._wait_or_stop(self.config.interval_seconds):
            return CaptureState.STOPPED
        return CaptureState.CHECK_COMPLETION

    async def _capture_loop(self) -> None:
        """Main capture loop using state machine pattern.

        Refactored to reduce cyclomatic complexity from 29 to 8.
        Uses CaptureState enum with dispatch handlers.
        """
        logger.info(
            "timelapse_capture_started",
            camera_id=self.config.camera_id,
            interval=self.config.interval_seconds,
            total_frames=self.config.total_frames,
        )

        # State machine dispatch table
        state_handlers = {
            CaptureState.CHECK_COMPLETION: self._state_check_completion,
            CaptureState.CHECK_RECOVERY: self._handle_recovery_mode,
            CaptureState.CHECK_RESOURCES: self._state_check_resources,
            CaptureState.CAPTURE_FRAME: self._state_capture_frame,
            CaptureState.WAIT_INTERVAL: self._state_wait_interval,
        }

        state = CaptureState.CHECK_COMPLETION

        while state not in (CaptureState.COMPLETED, CaptureState.STOPPED):
            if self._stop_event.is_set():
                state = CaptureState.STOPPED
                continue

            handler = state_handlers.get(state)
            if handler:
                state = await handler()

        logger.info(
            "timelapse_capture_stopped",
            camera_id=self.config.camera_id,
            frame_count=self.frame_count,
        )

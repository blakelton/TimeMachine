# Plan: Refactor _capture_loop Function

**Date:** 2025-12-23
**Priority:** P1 - Critical
**Current Complexity:** 29 (Grade D - HIGH)
**Target Complexity:** <10 per function (Grade A/B)
**File:** `backend/app/services/camera/timelapse.py:319`

---

## Problem Statement

The `_capture_loop` function has a cyclomatic complexity of 29, making it:
- Difficult to test individual code paths
- Hard to reason about all possible execution flows
- Challenging to add new features without increasing complexity
- Prone to bugs in edge cases

## Current Structure Analysis

The function handles multiple responsibilities:
1. **Duration checking** - Target end time logic
2. **Frame count checking** - Target frame count logic
3. **Recovery mode handling** - Camera recovery with backoff
4. **Resource checking** - Memory/disk availability
5. **System pressure handling** - Adaptive throttling
6. **Frame capture** - Actual image capture
7. **Overlay application** - Environment data overlay
8. **Failure tracking** - Gap logging, failure counts
9. **Interval waiting** - Sleep between captures

## Proposed Refactoring

### Strategy: Extract State Machine + Handler Functions

Break the loop into a state machine with clearly defined states and extract each responsibility into its own method.

### Implementation Steps

#### Step 1: Define Capture States

```python
from enum import Enum, auto

class CaptureState(Enum):
    """States in the capture loop state machine."""
    CHECK_COMPLETION = auto()   # Check if timelapse should end
    CHECK_RECOVERY = auto()     # Handle recovery mode
    CHECK_RESOURCES = auto()    # Verify system resources
    CAPTURE_FRAME = auto()      # Capture a single frame
    WAIT_INTERVAL = auto()      # Wait for next capture
    COMPLETED = auto()          # Timelapse finished
    STOPPED = auto()            # Stopped by user
```

#### Step 2: Extract Completion Checking

```python
async def _check_completion(self) -> tuple[bool, str | None]:
    """
    Check if timelapse should complete.

    Returns:
        (should_complete, reason)

    Complexity: ~6
    """
    # Check duration target (highest priority)
    if self.target_end_time and datetime.now() >= self.target_end_time:
        self._completed_by_duration = True
        if self.config.total_frames and self.frame_count < self.config.total_frames:
            self._frames_incomplete = True
            missed = self.config.total_frames - self.frame_count
            self._log_event(
                "duration_complete_incomplete_frames",
                f"Duration reached with {self.frame_count}/{self.config.total_frames} frames",
                expected_frames=self.config.total_frames,
                actual_frames=self.frame_count,
                missed_frames=missed,
            )
        return True, "duration_reached"

    # Check frame count target (only if no duration set)
    if self.config.total_frames and self.frame_count >= self.config.total_frames:
        if not self.target_end_time:
            return True, "target_frames_reached"

    return False, None
```

#### Step 3: Extract Recovery Handler

```python
async def _handle_recovery_mode(self) -> CaptureState:
    """
    Handle recovery mode with backoff.

    Returns:
        Next state to transition to

    Complexity: ~7
    """
    if self._recovery_attempts >= MAX_RECOVERY_ATTEMPTS:
        self._recovery_attempts = 0
        logger.info(
            "timelapse_recovery_cooldown",
            camera_id=self.config.camera_id,
            consecutive_failures=self._consecutive_failures,
        )
        # Extended wait during cooldown
        if await self._wait_or_stop(RECOVERY_BACKOFF_SECONDS * 2):
            return CaptureState.STOPPED
        return CaptureState.CHECK_RECOVERY

    recovered = await self._attempt_recovery()
    if recovered:
        self._in_recovery_mode = False
        self._log_recovery_gap_end()
        return CaptureState.CHECK_RESOURCES

    # Recovery failed - wait before retry
    if await self._wait_or_stop(RECOVERY_BACKOFF_SECONDS):
        return CaptureState.STOPPED
    return CaptureState.CHECK_RECOVERY


def _log_recovery_gap_end(self) -> None:
    """Log the end of a capture gap."""
    if self._gap_start_frame is not None:
        gap_duration = self._consecutive_failures * self.config.interval_seconds
        self._log_event(
            "gap_end",
            f"Camera recovered after {self._consecutive_failures} missed frames",
            gap_start_frame=self._gap_start_frame,
            missed_frames=self._consecutive_failures,
            gap_duration_seconds=gap_duration,
        )
        self._gap_start_frame = None
```

#### Step 4: Extract Resource Checking

```python
async def _check_system_resources(self) -> tuple[bool, float]:
    """
    Check system resources and calculate any needed throttle delay.

    Returns:
        (resources_ok, throttle_delay_seconds)

    Complexity: ~5
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
            )
            return True, throttle_delay

    return True, 0.0
```

#### Step 5: Extract Frame Capture Handler

```python
async def _capture_single_frame(self) -> bool:
    """
    Capture a single frame and handle success/failure.

    Returns:
        True if capture succeeded

    Complexity: ~8
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
        self._handle_capture_success(filepath)
        return True
    else:
        self._handle_capture_failure(message)
        return False


def _handle_capture_success(self, filepath: str | None) -> None:
    """Handle successful frame capture."""
    if self._consecutive_failures > 0:
        logger.info(
            "timelapse_recovered_naturally",
            camera_id=self.config.camera_id,
            consecutive_failures=self._consecutive_failures,
        )
    self._consecutive_failures = 0
    self.frame_count += 1

    # Apply overlay if configured
    if self._overlay_service and self._polling_service and filepath:
        self._apply_frame_overlay(filepath)

    logger.debug(
        "timelapse_frame_captured",
        camera_id=self.config.camera_id,
        frame=self.frame_count,
    )


def _handle_capture_failure(self, message: str) -> None:
    """Handle failed frame capture."""
    self._consecutive_failures += 1
    self._total_failures += 1

    if self._consecutive_failures == 1:
        self._gap_start_frame = self.frame_count
        self._log_event("gap_start", f"Capture failed: {message[:100]}")

    logger.warning(
        "timelapse_frame_failed",
        camera_id=self.config.camera_id,
        frame=self.frame_count,
        consecutive_failures=self._consecutive_failures,
        error=message,
    )

    if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
        if not self._in_recovery_mode:
            self._in_recovery_mode = True
            self._log_event("recovery_mode_entered", "Too many consecutive failures")


def _apply_frame_overlay(self, filepath: str) -> None:
    """Apply environment overlay to captured frame."""
    try:
        overlay_applied = asyncio.run(
            self._overlay_service.apply_overlay(
                image_path=Path(filepath),
                frame_number=self.frame_count,
                polling_service=self._polling_service,
            )
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
            error=str(e),
        )
```

#### Step 6: Refactored Main Loop

```python
async def _capture_loop(self) -> None:
    """
    Main capture loop using state machine pattern.

    Complexity: ~8 (down from 29)
    """
    logger.info(
        "timelapse_capture_started",
        camera_id=self.config.camera_id,
        interval=self.config.interval_seconds,
        total_frames=self.config.total_frames,
    )

    state = CaptureState.CHECK_COMPLETION

    while state not in (CaptureState.COMPLETED, CaptureState.STOPPED):
        # Check for stop request
        if self._stop_event.is_set():
            state = CaptureState.STOPPED
            continue

        if state == CaptureState.CHECK_COMPLETION:
            should_complete, reason = await self._check_completion()
            if should_complete:
                logger.info("timelapse_completed", reason=reason)
                state = CaptureState.COMPLETED
            elif self._in_recovery_mode:
                state = CaptureState.CHECK_RECOVERY
            else:
                state = CaptureState.CHECK_RESOURCES

        elif state == CaptureState.CHECK_RECOVERY:
            state = await self._handle_recovery_mode()

        elif state == CaptureState.CHECK_RESOURCES:
            resources_ok, delay = await self._check_system_resources()
            if not resources_ok:
                await asyncio.sleep(delay)
                state = CaptureState.CHECK_COMPLETION
            elif delay > 0:
                await asyncio.sleep(delay)
                state = CaptureState.CAPTURE_FRAME
            else:
                state = CaptureState.CAPTURE_FRAME

        elif state == CaptureState.CAPTURE_FRAME:
            success = await self._capture_single_frame()
            state = CaptureState.WAIT_INTERVAL

        elif state == CaptureState.WAIT_INTERVAL:
            if await self._wait_or_stop(self.config.interval_seconds):
                state = CaptureState.STOPPED
            else:
                state = CaptureState.CHECK_COMPLETION
```

### Complexity Analysis After Refactor

| Function | Before | After |
|----------|--------|-------|
| `_capture_loop` | 29 | ~8 |
| `_check_completion` | - | ~6 |
| `_handle_recovery_mode` | - | ~7 |
| `_log_recovery_gap_end` | - | ~2 |
| `_check_system_resources` | - | ~5 |
| `_capture_single_frame` | - | ~4 |
| `_handle_capture_success` | - | ~4 |
| `_handle_capture_failure` | - | ~5 |
| `_apply_frame_overlay` | - | ~3 |

**All functions under complexity 10.**

---

## Testing Strategy

### Unit Tests to Add

1. `test_check_completion_duration_reached`
2. `test_check_completion_frames_reached`
3. `test_check_completion_incomplete_frames`
4. `test_handle_recovery_mode_success`
5. `test_handle_recovery_mode_cooldown`
6. `test_check_system_resources_low_memory`
7. `test_check_system_resources_pressure`
8. `test_capture_single_frame_success`
9. `test_capture_single_frame_failure_triggers_recovery`
10. `test_capture_loop_state_transitions`

---

## Migration Steps

1. Add `CaptureState` enum to `timelapse.py`
2. Add helper methods one at a time, keeping old code
3. Refactor `_capture_loop` to use new helpers
4. Add unit tests for each helper
5. Remove any duplicated code
6. Run full test suite

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Race conditions in state machine | Keep single-threaded, test thoroughly |
| Timing changes | Keep interval logic identical |
| Recovery behavior changes | Preserve exact backoff timing |
| Frame numbering issues | Keep frame_count logic centralized |

---

## Success Criteria

- [ ] `_capture_loop` complexity < 10
- [ ] All helper functions complexity < 10
- [ ] All existing timelapse tests pass
- [ ] New unit tests for each extracted method
- [ ] No change to timelapse output behavior
- [ ] Recovery mode works identically

---

## Estimated Effort

- Implementation: 3-4 hours
- Testing: 2-3 hours
- Review & validation: 1-2 hours

**Total: ~6-9 hours**

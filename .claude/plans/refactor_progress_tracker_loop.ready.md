# Plan: Refactor _progress_tracker_loop Function

**Date:** 2025-12-23
**Priority:** P1 - Critical
**Current Complexity:** 26 (Grade D - HIGH)
**Target Complexity:** <10 per function (Grade A/B)
**File:** `backend/app/services/observation/service.py:802`

---

## Problem Statement

The `_progress_tracker_loop` function has a cyclomatic complexity of 26, making it:
- A challenge to understand all completion scenarios
- Difficult to add new completion conditions
- Hard to test edge cases
- Prone to bugs when modifying completion logic

## Current Structure Analysis

The function handles:
1. **Pipeline state monitoring** - Check if timelapse/recording is running
2. **Duration completion** - Handle "DURATION IS KING" logic
3. **Frame count completion** - Handle target frame completion
4. **Crash detection** - Detect unexpected pipeline stops
5. **Video assembly** - Trigger FFmpeg assembly for timelapses
6. **Folder size calculation** - Calculate final observation size
7. **Database updates** - Mark observation completed/failed
8. **Cleanup** - Remove tracking, restart preview

## Proposed Refactoring

### Strategy: Extract Completion Handlers + Result Pattern

Use a result-based pattern where each completion scenario returns a structured result, and the main loop simply dispatches based on pipeline state.

### Implementation Steps

#### Step 1: Define Completion Result

```python
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class CompletionReason(Enum):
    """Reasons an observation completed."""
    DURATION_REACHED = auto()      # Target time reached
    FRAMES_REACHED = auto()        # Target frame count reached
    PIPELINE_CRASHED = auto()      # Unexpected stop
    USER_STOPPED = auto()          # Manual stop


@dataclass
class CompletionResult:
    """Result of checking for observation completion."""
    completed: bool
    reason: CompletionReason | None
    actual_progress: int
    health_info: dict | None
    note: str | None
```

#### Step 2: Extract Pipeline State Checker

```python
async def _check_pipeline_running(
    self,
    camera_id: int,
    observation_type: str,
) -> tuple[bool, int]:
    """
    Check if the observation pipeline is still running.

    Returns:
        (is_running, current_progress)

    Complexity: ~4
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
```

#### Step 3: Extract Completion Analyzers

```python
async def _analyze_timelapse_completion(
    self,
    camera_id: int,
    observation: Observation,
    actual_progress: int,
) -> CompletionResult:
    """
    Analyze why a timelapse stopped and determine completion status.

    Complexity: ~7
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


async def _analyze_recording_completion(
    self,
    observation: Observation,
    actual_progress: int,
) -> CompletionResult:
    """
    Analyze why a recording stopped.

    Complexity: ~4
    """
    if observation.progress_total and actual_progress >= observation.progress_total:
        return CompletionResult(
            completed=True,
            reason=CompletionReason.FRAMES_REACHED,
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
```

#### Step 4: Extract Completion Handlers

```python
async def _handle_successful_completion(
    self,
    observation_id: int,
    camera_id: int,
    observation: Observation,
    result: CompletionResult,
    session: AsyncSession,
) -> None:
    """
    Handle successful observation completion.

    Complexity: ~6
    """
    obs_repo = ObservationRepository(session)

    logger.info(
        "observation_completed",
        observation_id=observation_id,
        camera_id=camera_id,
        reason=result.reason.name if result.reason else "unknown",
        progress=result.actual_progress,
    )

    # Assemble video for timelapses
    if observation.observation_type == "timelapse":
        await self._assemble_timelapse_video(
            observation_id, camera_id, session
        )

    # Calculate final folder size
    size_bytes = await self._get_observation_size(observation.folder_path)

    # Update database
    if result.note:
        await obs_repo.update(
            observation_id,
            progress_current=result.actual_progress,
            notes=result.note,
        )
    await obs_repo.mark_completed(observation_id, size_bytes)
    await session.commit()


async def _handle_failed_completion(
    self,
    observation_id: int,
    camera_id: int,
    observation: Observation,
    result: CompletionResult,
    session: AsyncSession,
) -> None:
    """
    Handle observation that stopped unexpectedly.

    Complexity: ~5
    """
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
        await self._assemble_timelapse_video(
            observation_id, camera_id, session, partial=True
        )

    await obs_repo.mark_failed(observation_id, result.note or "Unknown error")
    await session.commit()


async def _assemble_timelapse_video(
    self,
    observation_id: int,
    camera_id: int,
    session: AsyncSession,
    partial: bool = False,
) -> None:
    """Assemble timelapse frames into video."""
    success, msg, output_path = await timelapse_service.stop_timelapse(
        camera_id, session, assemble_video=True
    )
    log_event = "observation_timelapse_partial_assembly" if partial else "observation_timelapse_assembly_result"
    logger.info(
        log_event,
        observation_id=observation_id,
        success=success,
        output_path=output_path,
    )


async def _get_observation_size(self, folder_path: str | None) -> int | None:
    """Calculate observation folder size."""
    if not folder_path:
        return None
    path = Path(folder_path)
    if path.exists():
        return await self._calculate_folder_size(path)
    return None
```

#### Step 5: Refactored Main Loop

```python
async def _progress_tracker_loop(
    self,
    observation_id: int,
    camera_id: int,
    observation_type: str,
) -> None:
    """
    Background loop that monitors observation health.

    Complexity: ~8 (down from 26)
    """
    from app.db.session import SessionFactory

    check_interval = 3.0
    await asyncio.sleep(2.0)  # Grace period for pipeline to start

    while True:
        try:
            # Check if pipeline is still running
            is_running, actual_progress = await self._check_pipeline_running(
                camera_id, observation_type
            )

            if not is_running:
                # Pipeline stopped - analyze why and handle completion
                async with SessionFactory() as session:
                    obs_repo = ObservationRepository(session)
                    observation = await obs_repo.get_by_id(observation_id)

                    if not observation:
                        logger.error("observation_not_found", observation_id=observation_id)
                        break

                    # Analyze completion
                    if observation_type == "timelapse":
                        result = await self._analyze_timelapse_completion(
                            camera_id, observation, actual_progress
                        )
                    else:
                        result = await self._analyze_recording_completion(
                            observation, actual_progress
                        )

                    # Handle based on completion status
                    if result.completed:
                        await self._handle_successful_completion(
                            observation_id, camera_id, observation, result, session
                        )
                    else:
                        await self._handle_failed_completion(
                            observation_id, camera_id, observation, result, session
                        )

                # Cleanup
                await self._cleanup_after_completion(camera_id)
                break

            await asyncio.sleep(check_interval)

        except asyncio.CancelledError:
            logger.debug("progress_tracker_cancelled", observation_id=observation_id)
            break
        except Exception as e:
            logger.error("progress_tracker_error", observation_id=observation_id, error=str(e))
            await asyncio.sleep(check_interval)


async def _cleanup_after_completion(self, camera_id: int) -> None:
    """Clean up tracking state after observation completes."""
    if camera_id in self._active_observations:
        del self._active_observations[camera_id]
    await self._restart_preview_if_stopped(camera_id)
```

### Complexity Analysis After Refactor

| Function | Before | After |
|----------|--------|-------|
| `_progress_tracker_loop` | 26 | ~8 |
| `_check_pipeline_running` | - | ~4 |
| `_analyze_timelapse_completion` | - | ~7 |
| `_analyze_recording_completion` | - | ~4 |
| `_handle_successful_completion` | - | ~6 |
| `_handle_failed_completion` | - | ~5 |
| `_assemble_timelapse_video` | - | ~2 |
| `_get_observation_size` | - | ~3 |
| `_cleanup_after_completion` | - | ~2 |

**All functions under complexity 10.**

---

## Testing Strategy

### Unit Tests to Add

1. `test_check_pipeline_running_timelapse`
2. `test_check_pipeline_running_recording`
3. `test_analyze_timelapse_duration_complete`
4. `test_analyze_timelapse_frames_complete`
5. `test_analyze_timelapse_crashed`
6. `test_analyze_recording_complete`
7. `test_analyze_recording_crashed`
8. `test_handle_successful_completion`
9. `test_handle_failed_completion_with_salvage`
10. `test_progress_tracker_full_cycle`

---

## Migration Steps

1. Add `CompletionReason` and `CompletionResult` dataclasses
2. Extract `_check_pipeline_running` method
3. Extract analysis methods
4. Extract handler methods
5. Refactor main loop to use new methods
6. Add unit tests
7. Run integration tests

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| "DURATION IS KING" logic change | Keep exact priority in analyzer |
| Video assembly timing | Keep assembly calls in same order |
| Database transaction issues | Keep session management identical |
| Preview restart timing | Keep cleanup sequence |

---

## Success Criteria

- [ ] Main loop complexity < 10
- [ ] All helper functions complexity < 10
- [ ] All completion scenarios work identically
- [ ] New unit tests with >80% coverage
- [ ] "DURATION IS KING" behavior preserved
- [ ] Partial video assembly still works

---

## Estimated Effort

- Implementation: 3-4 hours
- Testing: 2-3 hours
- Review & validation: 1-2 hours

**Total: ~6-9 hours**

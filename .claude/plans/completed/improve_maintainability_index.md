# Plan: Improve Maintainability Index

**Date:** 2025-12-23
**Priority:** P1 - Critical
**Target Files:**
- `backend/app/services/observation/service.py` - MI: 20.20 (CRITICAL)
- `backend/app/services/camera/timelapse.py` - MI: 25.93 (HIGH)

**Healthy MI Score:** > 40 (ideally > 60)

---

## Problem Statement

The Maintainability Index (MI) is a composite metric that considers:
- **Cyclomatic Complexity** - Number of decision paths
- **Halstead Volume** - Code size and vocabulary
- **Lines of Code** - Raw size
- **Comment Ratio** - Documentation coverage

Scores below 20 indicate code that is very difficult to maintain. Both critical files score dangerously low.

---

## Understanding the MI Formula

```
MI = 171 - 5.2 * ln(HV) - 0.23 * CC - 16.2 * ln(LOC)

Where:
- HV = Halstead Volume (function of operators/operands)
- CC = Cyclomatic Complexity
- LOC = Lines of Code
```

### Improvement Levers

1. **Reduce LOC** → Split into smaller files/functions
2. **Reduce CC** → Simplify conditionals, extract methods
3. **Reduce HV** → Use clearer naming, fewer unique operations
4. **Add comments** → Some MI formulas include comment bonus

---

## File 1: observation/service.py (MI: 20.20)

### Current Issues

| Metric | Current | Target |
|--------|---------|--------|
| Lines of Code | 1,365 | <500 |
| Max Complexity | 26 | <10 |
| Methods | 28 | <15 |
| Halstead Volume | Very High | Reduce 50% |

### Improvement Plan

#### Step 1: Apply Previous Refactors

The following plans directly improve this file's MI:
- `refactor_progress_tracker_loop.ready.md` - Reduces CC from 26 to ~8
- `split_large_files.ready.md` - Reduces LOC from 1,365 to ~400

#### Step 2: Extract Data Classes

Move inline data structures to dedicated module:

```python
# observation/types.py
from dataclasses import dataclass
from enum import Enum

class ObservationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"

@dataclass
class ObservationProgress:
    current: int
    total: int | None
    percentage: float | None
    size_bytes: int
    size_formatted: str
    elapsed_seconds: int
    has_preview: bool

@dataclass
class TimelapseConfig:
    interval_seconds: float
    total_frames: int | None
    duration_seconds: int | None
    output_fps: int
    # ...
```

#### Step 3: Add Documentation

Add module and method docstrings (improves some MI calculations):

```python
"""
Observation Service
===================

Core service for managing timelapse and recording observations.

Responsibilities:
- Starting/stopping observations
- Progress tracking and monitoring
- Video assembly coordination
- Preview generation

Architecture:
- Delegates to TimelapseHandler and RecordingHandler
- Uses ProgressTracker for health monitoring
- Uses PreviewGenerator for live previews

Usage:
    from app.services.observation import observation_service

    success, msg, obs = await observation_service.start_observation(
        camera_id=1,
        observation_type="timelapse",
        config=config,
        session=session,
    )
"""
```

#### Step 4: Simplify Complex Methods

Replace nested conditionals with early returns:

```python
# Before (high complexity)
async def get_status(self, obs_id: int) -> dict:
    obs = await self._get_observation(obs_id)
    if obs:
        if obs.status == "running":
            if obs.observation_type == "timelapse":
                progress = self._get_timelapse_progress(obs.camera_id)
                if progress:
                    return {"status": "running", "progress": progress}
                else:
                    return {"status": "running", "progress": None}
            else:
                return {"status": "running", "progress": None}
        else:
            return {"status": obs.status}
    return None

# After (lower complexity)
async def get_status(self, obs_id: int) -> dict | None:
    obs = await self._get_observation(obs_id)
    if not obs:
        return None

    if obs.status != "running":
        return {"status": obs.status}

    progress = None
    if obs.observation_type == "timelapse":
        progress = self._get_timelapse_progress(obs.camera_id)

    return {"status": "running", "progress": progress}
```

### Expected MI After Improvements

| Change | LOC Impact | CC Impact | MI Delta |
|--------|------------|-----------|----------|
| Split to handlers | -500 | -10 | +15 |
| Extract data classes | -50 | -2 | +3 |
| Progress tracker extraction | -180 | -18 | +8 |
| Simplify conditionals | 0 | -5 | +4 |
| Add docstrings | +50 | 0 | +2 |

**Projected MI: ~50-55 (from 20.20)**

---

## File 2: timelapse.py (MI: 25.93)

### Current Issues

| Metric | Current | Target |
|--------|---------|--------|
| Lines of Code | 1,168 | <500 |
| Max Complexity | 29 | <10 |
| Classes | 2 | 3-5 (smaller) |

### Improvement Plan

#### Step 1: Apply Previous Refactors

The following plans directly improve this file's MI:
- `refactor_capture_loop.ready.md` - Reduces CC from 29 to ~8
- `split_large_files.ready.md` - Splits into timelapse/ package

#### Step 2: Extract TimelapseState Logic

The massive `TimelapseState` class should be decomposed:

```python
# timelapse/state.py - Core state only (~150 lines)
class TimelapseState:
    """Manages state for an active timelapse session."""

    def __init__(self, config: TimelapseConfig, ...):
        self.config = config
        self.frame_count = 0
        self._stop_event = asyncio.Event()
        self._capture_handler = CaptureHandler(config)
        self._recovery_handler = RecoveryHandler(config)

    async def run(self) -> None:
        """Execute timelapse capture loop."""
        await self._capture_handler.run(
            stop_event=self._stop_event,
            recovery_handler=self._recovery_handler,
        )

    def stop(self) -> None:
        """Signal timelapse to stop."""
        self._stop_event.set()
```

#### Step 3: Use Composition Over Inheritance

Current pattern creates complexity through deep method chains.
New pattern uses composition for clearer responsibilities:

```python
# Composition pattern
class TimelapseState:
    def __init__(self, ...):
        self._capture = CaptureLoop(config)
        self._recovery = RecoveryManager(config)
        self._assembly = VideoAssembler(config)
        self._overlay = OverlayApplicator(config)
```

### Expected MI After Improvements

| Change | LOC Impact | CC Impact | MI Delta |
|--------|------------|-----------|----------|
| Split to package | -700 | -15 | +18 |
| Extract capture loop | -200 | -21 | +10 |
| Extract recovery | -100 | -5 | +4 |
| Composition refactor | 0 | -3 | +3 |

**Projected MI: ~55-60 (from 25.93)**

---

## Verification Commands

### Check Current MI

```bash
cd /home/blake/projects/TimeMachine/backend
/opt/timemachine/venv/bin/radon mi app/services/observation/service.py -s
/opt/timemachine/venv/bin/radon mi app/services/camera/timelapse.py -s
```

### Check After Refactoring

Run same commands after each refactor phase to track improvement.

### Target Thresholds

| MI Score | Grade | Status |
|----------|-------|--------|
| 0-9 | F | Unmaintainable |
| 10-19 | D | Very difficult |
| 20-29 | C | Difficult |
| 30-39 | B | Moderate |
| 40-59 | A | Good |
| 60+ | A+ | Excellent |

**Target: All files ≥ 40 (Grade A)**

---

## Implementation Order

### Phase 1: Apply Complexity Refactors (Week 1)
1. `refactor_check_camera_health.ready.md`
2. `refactor_capture_loop.ready.md`
3. `refactor_progress_tracker_loop.ready.md`
4. `refactor_get_observation_media.ready.md`

### Phase 2: File Splitting (Week 2)
1. Split cameras.py into package
2. Split observation/service.py into package
3. Split timelapse.py into package

### Phase 3: Polish (Week 3)
1. Add comprehensive docstrings
2. Extract remaining data classes
3. Simplify remaining conditionals
4. Re-measure MI scores

---

## Testing Strategy

### Before Each Change
1. Record current MI: `radon mi <file> -s`
2. Record current CC: `radon cc <file> -s`
3. Run existing tests

### After Each Change
1. Run existing tests
2. Measure new MI
3. Ensure MI improved or stayed same
4. Document improvement in commit message

### Final Verification
1. All files MI ≥ 40
2. All functions CC ≤ 10
3. All tests pass
4. No new linting errors

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| MI gets worse temporarily | Make atomic commits, can revert |
| Tests fail | Fix before continuing |
| Feature regression | Manual smoke testing |
| Over-abstraction | Keep interfaces simple |

---

## Success Criteria

- [ ] observation/service.py MI ≥ 40
- [ ] timelapse.py MI ≥ 40
- [ ] No file exceeds 500 LOC
- [ ] No function exceeds CC 10
- [ ] All tests pass
- [ ] Code review approval

---

## Estimated Effort

This plan aggregates work from other refactor plans:

| Task | Reference Plan | Hours |
|------|----------------|-------|
| check_camera_health | refactor_check_camera_health | 4-6 |
| _capture_loop | refactor_capture_loop | 6-9 |
| _progress_tracker_loop | refactor_progress_tracker_loop | 6-9 |
| get_observation_media | refactor_get_observation_media | 3-4 |
| File splitting | split_large_files | 12-17 |
| Polish & verification | This plan | 4-6 |

**Total: ~35-51 hours (4-6 working days)**

---

## Tracking Progress

Create a tracking table and update after each phase:

| File | Initial MI | After Phase 1 | After Phase 2 | Final |
|------|------------|---------------|---------------|-------|
| observation/service.py | 20.20 | ? | ? | ≥40 |
| timelapse.py | 25.93 | ? | ? | ≥40 |
| cameras.py | 32.15 | - | ? | ≥40 |
| observations.py | 38.42 | ? | - | ≥40 |

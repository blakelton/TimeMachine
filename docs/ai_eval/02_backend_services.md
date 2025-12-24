# Backend Services Evaluation Report

**Date:** 2025-12-23
**Analyzer:** Claude Opus 4.5
**Component:** Backend Services (`backend/app/services/`)

---

## Executive Summary

The services layer contains the core business logic for camera operations, observations, environment monitoring, and system management. While the architecture is sound with good separation of concerns, several services contain highly complex methods that need refactoring. The timelapse and observation services are particularly complex.

---

## Files Analyzed

### Camera Services (`services/camera/`)

| File | Lines | Maintainability Index | Grade |
|------|-------|----------------------|-------|
| timelapse.py | 1,168 | 25.93 | A (borderline) |
| discovery.py | 495 | 47.81 | A |
| recording.py | 433 | 53.29 | A |
| preview.py | 401 | 58.61 | A |
| pipeline.py | 393 | 52.57 | A |
| overlay.py | 379 | 51.48 | A |
| capture.py | 165 | 74.94 | A |
| resolver.py | 130 | 72.75 | A |

### Other Services

| File | Lines | Maintainability Index | Grade |
|------|-------|----------------------|-------|
| observation/service.py | 1,365 | 20.20 | A (critical) |
| storage/service.py | 515 | 38.22 | A |
| startup.py | 328 | 56.84 | A |
| environment/sensors.py | 335 | 44.68 | A |
| environment/polling.py | 269 | 60.69 | A |
| thumbnail/service.py | 290 | 58.56 | A |
| system/stats.py | 242 | 58.02 | A |
| websocket/manager.py | 123 | 81.24 | A |
| camera_device_monitor.py | 115 | 74.32 | A |

---

## Critical Issues

### 1. Extreme Cyclomatic Complexity (Grade D)

**File:** `timelapse.py:319` - `TimelapseSession._capture_loop`
**Complexity:** 29 (Grade D - High Risk)
**Lines:** ~120

**Problems:**
- Handles capture, recovery, adaptive throttling, overlay, and state management in one loop
- 12+ conditional branches
- Difficult to unit test individual behaviors

**Recommendation:**
```python
# Decompose into:
async def _perform_capture(self) -> tuple[bool, str | None]
async def _handle_capture_success(self, filepath: str)
async def _handle_capture_failure(self)
async def _check_recovery_needed(self) -> bool
async def _apply_overlay_if_configured(self, filepath: str)
async def _calculate_next_delay(self) -> float
```

### 2. Extreme Cyclomatic Complexity (Grade D)

**File:** `observation/service.py:802` - `ObservationService._progress_tracker_loop`
**Complexity:** 26 (Grade D - High Risk)
**Lines:** ~180

**Problems:**
- Monitors multiple observation types simultaneously
- Complex state machine logic
- Handles completion, failure, and timeout scenarios

**Recommendation:**
```python
# Extract into strategy pattern:
class TimelapseProgressTracker:
    async def check_progress(self, obs) -> ProgressUpdate

class RecordingProgressTracker:
    async def check_progress(self, obs) -> ProgressUpdate

# Main loop becomes simple dispatch
for obs in active_observations:
    tracker = self._get_tracker(obs.type)
    update = await tracker.check_progress(obs)
```

---

## High Complexity Functions (Grade C)

| Function | File | Complexity | Description |
|----------|------|------------|-------------|
| discover_usb_cameras | discovery.py:212 | 20 | USB camera enumeration |
| start_timelapse | timelapse.py:556 | 17 | Timelapse initialization |
| ManagedPipeline.stop | pipeline.py:195 | 16 | Pipeline shutdown |
| generate_timelapse_preview | observation/service.py:1215 | 15 | Preview generation |
| _get_by_path_for_device | discovery.py:29 | 15 | Device path resolution |
| list_files | storage/service.py:274 | 15 | Directory listing |
| _start_timelapse_observation | observation/service.py:256 | 10 | Observation startup |

---

## Moderate Issues

### 3. Service File Sizes

| File | Lines | Status | Action |
|------|-------|--------|--------|
| observation/service.py | 1,365 | CRITICAL | Must split |
| timelapse.py | 1,168 | WARNING | Should split |
| storage/service.py | 515 | ACCEPTABLE | Monitor |
| discovery.py | 495 | ACCEPTABLE | Monitor |

### 4. Maintainability Index Concerns

Files with MI < 40 (approaching problematic):

| File | MI Score | Risk |
|------|----------|------|
| observation/service.py | 20.20 | HIGH - approaching unmaintainable |
| timelapse.py | 25.93 | MEDIUM - needs attention |
| storage/service.py | 38.22 | LOW - monitor |

---

## Architecture Analysis

### Dependency Graph

```
                    ┌─────────────────┐
                    │ ObservationSvc  │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    ┌──────▼──────┐  ┌───────▼───────┐  ┌──────▼──────┐
    │ TimelapseSvc │  │ RecordingSvc  │  │ PreviewSvc  │
    └──────┬──────┘  └───────┬───────┘  └──────┬──────┘
           │                 │                 │
           └─────────────────┼─────────────────┘
                             │
                    ┌────────▼────────┐
                    │ ManagedPipeline │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  CaptureService │
                    └─────────────────┘
```

### Service Responsibilities

| Service | Primary Responsibility | Secondary Responsibilities |
|---------|----------------------|---------------------------|
| ObservationService | Observation lifecycle | Progress tracking, preview generation |
| TimelapseService | Timelapse capture | Recovery, video assembly |
| RecordingService | Video recording | Process management |
| PreviewService | Live preview streams | Port management |
| DiscoveryService | Camera detection | Hardware identification |
| StorageService | File management | Retention enforcement |
| EnvironmentPollingService | Sensor data collection | Reader management |

---

## Code Quality Observations

### Positive Aspects

1. **State Machine Pattern**: `ManagedPipeline` uses proper state machine for lifecycle
2. **Async Design**: All I/O operations are properly async
3. **Error Recovery**: Timelapse service has robust recovery mechanisms
4. **Logging**: Comprehensive structured logging throughout
5. **Resource Management**: Proper use of async context managers
6. **Singleton Pattern**: Services properly instantiated as module-level singletons

### Areas for Improvement

1. **Service Interfaces**: No abstract base classes defining service contracts
2. **Dependency Injection**: Services directly import each other (tight coupling)
3. **Configuration**: Some magic numbers embedded in services
4. **Testing Hooks**: Difficult to mock internal methods for unit testing

---

## Thread Safety Analysis

| Service | Thread Safety | Notes |
|---------|--------------|-------|
| TimelapseService | SAFE | Uses asyncio locks |
| RecordingService | SAFE | Single-threaded async |
| PreviewService | SAFE | Dict operations are atomic |
| ObservationService | SAFE | Asyncio-based |
| EnvironmentPollingService | SAFE | Async with locks |

---

## Resource Management

### Memory Concerns

1. **observation/service.py**: Stores observation metadata in memory - potential leak for long sessions
2. **timelapse.py**: Events list grows unbounded during capture
3. **overlay.py**: Graph caching may accumulate if not cleaned

### Process Management

1. **GStreamer Processes**: Properly tracked and cleaned up
2. **libcamera Processes**: Startup cleanup handles orphans
3. **Subprocess Timeouts**: Implemented but some edge cases remain

---

## Recommendations

### Immediate Actions (Priority 1)

1. **Refactor `_capture_loop`**:
   - Extract capture logic into separate methods
   - Create `CaptureStrategy` class hierarchy
   - Target: Reduce complexity from 29 to <10

2. **Refactor `_progress_tracker_loop`**:
   - Implement tracker strategy pattern
   - Separate observation type handling
   - Target: Reduce complexity from 26 to <10

3. **Split `observation/service.py`**:
   ```
   observation/
   ├── __init__.py
   ├── service.py (main orchestration, <400 lines)
   ├── timelapse_handler.py (timelapse-specific logic)
   ├── recording_handler.py (recording-specific logic)
   ├── progress_tracker.py (progress monitoring)
   └── preview_generator.py (preview generation)
   ```

### Short-term Actions (Priority 2)

4. **Create Service Interfaces**:
   ```python
   class ICameraService(Protocol):
       async def start(self, config: Config) -> Result
       async def stop(self, camera_id: int) -> Result
       def get_status(self, camera_id: int) -> Status
   ```

5. **Add Event Cleanup**: Implement periodic cleanup of timelapse event logs

6. **Extract Constants**: Move magic numbers to configuration

### Long-term Actions (Priority 3)

7. **Dependency Injection Container**: Consider using `dependency-injector` library
8. **Service Registry**: Implement service locator pattern for loose coupling
9. **Metrics Collection**: Add Prometheus metrics for service health

---

## Metrics Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Total Lines | 6,151 | <5,000 | WARN |
| Avg Complexity | 4.1 | <5 | PASS |
| Max Complexity | 29 | <15 | FAIL |
| Files > 500 LOC | 3 | 0 | FAIL |
| Avg Maintainability | 54.2 | >50 | PASS |
| Min Maintainability | 20.2 | >30 | FAIL |

---

*Report generated by automated code analysis*

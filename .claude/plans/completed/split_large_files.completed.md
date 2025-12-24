# Plan: Split Large Files

**Date:** 2025-12-23
**Priority:** P1 - Critical
**Target:** Files exceeding 500 LOC
**Files Affected:**
- `backend/app/api/routes/cameras.py` (1,703 lines)
- `backend/app/services/observation/service.py` (1,365 lines)
- `backend/app/services/camera/timelapse.py` (1,168 lines)
- `backend/app/api/routes/observations.py` (802 lines)
- `frontend/src/components/settings/EnvironmentPanel.tsx` (611 lines)

---

## Problem Statement

Large files are:
- Difficult to navigate and understand
- Prone to merge conflicts
- Hard to maintain clear mental models
- Challenging for new developers
- Slower to load in IDEs

## Recommended Maximum: 500 lines per file

---

## File 1: cameras.py (1,703 lines)

### Current Structure

```
cameras.py
├── Imports (~30 lines)
├── Router setup (~5 lines)
├── Dashboard endpoint (~100 lines)
├── CRUD endpoints (~200 lines)
│   ├── list_cameras
│   ├── get_camera
│   ├── create_camera
│   ├── update_camera
│   └── delete_camera
├── Health check endpoint (~150 lines)
├── Discovery endpoints (~200 lines)
├── Preview endpoints (~400 lines)
│   ├── start_preview
│   ├── stop_preview
│   ├── get_preview_status
│   └── stream_preview
├── Recording endpoints (~250 lines)
├── Timelapse endpoints (~250 lines)
└── Capture endpoints (~100 lines)
```

### Proposed Split

```
backend/app/api/routes/cameras/
├── __init__.py          # Router aggregation, exports main router
├── crud.py              # CRUD operations (~200 lines)
├── health.py            # Health check endpoint (~150 lines)
├── discovery.py         # Discovery endpoints (~200 lines)
├── preview.py           # Preview management (~400 lines)
├── recording.py         # Recording control (~250 lines)
├── timelapse.py         # Timelapse control (~250 lines)
├── capture.py           # Still capture (~100 lines)
└── dashboard.py         # Dashboard batch endpoint (~100 lines)
```

### Implementation

#### `__init__.py`:
```python
"""Camera API routes package."""

from fastapi import APIRouter

from .crud import router as crud_router
from .health import router as health_router
from .discovery import router as discovery_router
from .preview import router as preview_router
from .recording import router as recording_router
from .timelapse import router as timelapse_router
from .capture import router as capture_router
from .dashboard import router as dashboard_router

router = APIRouter(prefix="/cameras", tags=["cameras"])

# Include all sub-routers
router.include_router(dashboard_router)
router.include_router(crud_router)
router.include_router(health_router)
router.include_router(discovery_router)
router.include_router(preview_router)
router.include_router(recording_router)
router.include_router(timelapse_router)
router.include_router(capture_router)
```

#### Each sub-router file:
```python
"""Camera preview endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
# ... other imports

router = APIRouter()

@router.post("/{camera_id}/preview/start")
async def start_preview(...): ...

@router.post("/{camera_id}/preview/stop")
async def stop_preview(...): ...
```

---

## File 2: observation/service.py (1,365 lines)

### Current Structure

```
service.py
├── Imports (~50 lines)
├── Helper functions (~50 lines)
├── ObservationService class (~1,265 lines)
│   ├── __init__ (~20 lines)
│   ├── start_observation (~100 lines)
│   ├── _start_timelapse_observation (~100 lines)
│   ├── _start_recording_observation (~80 lines)
│   ├── stop_observation (~80 lines)
│   ├── get_observation_status (~50 lines)
│   ├── get_observation_list (~40 lines)
│   ├── Progress tracking methods (~200 lines)
│   ├── Preview generation methods (~250 lines)
│   ├── Metadata methods (~80 lines)
│   ├── Cleanup methods (~100 lines)
│   └── Utility methods (~150 lines)
```

### Proposed Split

```
backend/app/services/observation/
├── __init__.py           # Exports, service singleton
├── service.py            # Core ObservationService (~400 lines)
├── timelapse_handler.py  # Timelapse-specific logic (~200 lines)
├── recording_handler.py  # Recording-specific logic (~150 lines)
├── progress_tracker.py   # Progress monitoring (~250 lines)
├── preview_generator.py  # Live preview generation (~200 lines)
├── metadata.py           # Folder/metadata helpers (~100 lines)
└── media.py              # Media file discovery (~100 lines)
```

### Implementation

#### Core service.py (slimmed down):
```python
"""Core observation service for managing timelapse and recording sessions."""

from .timelapse_handler import TimelapseHandler
from .recording_handler import RecordingHandler
from .progress_tracker import ProgressTracker
from .preview_generator import PreviewGenerator


class ObservationService:
    """Service for managing observations."""

    def __init__(self):
        self._timelapse_handler = TimelapseHandler()
        self._recording_handler = RecordingHandler()
        self._progress_tracker = ProgressTracker()
        self._preview_generator = PreviewGenerator()
        self._active_observations: dict[int, int] = {}

    async def start_observation(
        self,
        camera_id: int,
        observation_type: str,
        config: dict,
        session: AsyncSession,
    ) -> tuple[bool, str, Observation | None]:
        """Start a new observation."""
        if observation_type == "timelapse":
            return await self._timelapse_handler.start(camera_id, config, session)
        else:
            return await self._recording_handler.start(camera_id, config, session)

    async def stop_observation(self, observation_id: int, ...) -> ...:
        """Stop an active observation."""
        ...
```

#### timelapse_handler.py:
```python
"""Timelapse observation handler."""

class TimelapseHandler:
    """Handles timelapse-specific observation logic."""

    async def start(self, camera_id: int, config: dict, session: AsyncSession):
        """Start a timelapse observation."""
        ...

    async def stop(self, observation_id: int, assemble_video: bool):
        """Stop a timelapse and optionally assemble video."""
        ...
```

---

## File 3: timelapse.py (1,168 lines)

### Current Structure

```
timelapse.py
├── Imports (~30 lines)
├── Constants (~20 lines)
├── TimelapseConfig dataclass (~30 lines)
├── TimelapseState class (~950 lines)
│   ├── State management
│   ├── Capture loop
│   ├── Recovery logic
│   ├── Overlay handling
│   └── Video assembly
├── TimelapseService class (~100 lines)
└── Singleton instance (~10 lines)
```

### Proposed Split

```
backend/app/services/camera/timelapse/
├── __init__.py           # Exports service singleton
├── config.py             # TimelapseConfig, constants (~50 lines)
├── state.py              # TimelapseState class, slimmed (~400 lines)
├── capture.py            # Capture loop logic (~250 lines)
├── recovery.py           # Recovery/reconnection logic (~200 lines)
├── assembly.py           # Video assembly with FFmpeg (~150 lines)
└── service.py            # TimelapseService class (~100 lines)
```

---

## File 4: observations.py (802 lines)

### Current Structure

Already close to target. After extracting media finder (from previous plan), this will be ~700 lines.

### Minimal Changes Needed

1. Extract media discovery to `services/observation/media.py` (already planned)
2. Consider extracting listing/pagination logic if still over 500 lines

---

## File 5: EnvironmentPanel.tsx (611 lines)

### Current Structure

```
EnvironmentPanel.tsx
├── Imports (~20 lines)
├── Types (~30 lines)
├── Component (~560 lines)
│   ├── State management (~50 lines)
│   ├── API queries (~100 lines)
│   ├── Form handling (~80 lines)
│   ├── Event handlers (~100 lines)
│   └── JSX render (~230 lines)
```

### Proposed Split

```
frontend/src/components/settings/environment/
├── index.ts                    # Exports
├── EnvironmentPanel.tsx        # Main container (~150 lines)
├── DeviceList.tsx              # Device list display (~100 lines)
├── DeviceForm.tsx              # Add/edit form (~150 lines)
├── ReadingsDisplay.tsx         # Current readings (~100 lines)
├── TargetSettings.tsx          # Target value config (~80 lines)
└── types.ts                    # Shared types (~30 lines)
```

### Implementation

#### EnvironmentPanel.tsx (container):
```tsx
import { DeviceList } from './DeviceList';
import { DeviceForm } from './DeviceForm';
import { ReadingsDisplay } from './ReadingsDisplay';

export function EnvironmentPanel() {
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [isFormOpen, setIsFormOpen] = useState(false);

  return (
    <div className="environment-panel">
      <DeviceList
        onSelect={setSelectedDevice}
        onAdd={() => setIsFormOpen(true)}
      />
      {selectedDevice && (
        <ReadingsDisplay device={selectedDevice} />
      )}
      <DeviceForm
        isOpen={isFormOpen}
        device={selectedDevice}
        onClose={() => setIsFormOpen(false)}
      />
    </div>
  );
}
```

---

## Migration Strategy

### Phase 1: Backend API Routes (cameras.py)
1. Create `cameras/` directory
2. Move dashboard endpoint to `dashboard.py`
3. Move CRUD to `crud.py`
4. Move preview endpoints to `preview.py`
5. Update imports in `api/routes/__init__.py`
6. Run tests after each file move

### Phase 2: Observation Service
1. Extract `media.py` (from previous plan)
2. Extract `progress_tracker.py`
3. Extract `preview_generator.py`
4. Extract handlers
5. Slim down main `service.py`

### Phase 3: Timelapse Service
1. Create `timelapse/` directory
2. Extract `config.py`
3. Extract `recovery.py`
4. Extract `assembly.py`
5. Slim down state class

### Phase 4: Frontend Components
1. Create `environment/` directory
2. Extract sub-components
3. Update imports

---

## Testing Requirements

### For Each File Move:
1. Run existing unit tests
2. Run integration tests
3. Verify API responses unchanged
4. Check import paths work

### Post-Migration:
1. Full test suite pass
2. Manual smoke testing
3. API documentation check (OpenAPI schema unchanged)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular imports | Use dependency injection, lazy imports |
| Missing imports | IDE refactoring tools, grep verification |
| Breaking changes | Keep external API unchanged |
| Test failures | Fix imports, re-run after each move |

---

## Success Criteria

- [ ] All files under 500 lines
- [ ] No circular import errors
- [ ] All tests pass
- [ ] API schemas unchanged
- [ ] No performance regression
- [ ] IDE navigation works

---

## Estimated Effort

| Phase | Effort |
|-------|--------|
| Phase 1: cameras.py | 3-4 hours |
| Phase 2: observation/service.py | 4-6 hours |
| Phase 3: timelapse.py | 3-4 hours |
| Phase 4: EnvironmentPanel.tsx | 2-3 hours |

**Total: ~12-17 hours (spread over multiple sessions)**

---

## Priority Order

1. **cameras.py** - Largest file, most endpoints, highest impact
2. **observation/service.py** - Core complexity, blocking other refactors
3. **timelapse.py** - Tied to _capture_loop refactor
4. **EnvironmentPanel.tsx** - Lower priority, frontend only

---

## Notes

- Keep git commits atomic (one file move per commit)
- Use IDE refactoring tools when possible
- Run linter after each move to catch import issues
- Update any documentation referencing old paths

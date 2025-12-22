# Phase 4: Advanced Scheduling

> Time-based triggers for camera operations

**Status**: ready
**Created**: 2025-12-21
**Parent**: [masterplan.md](masterplan.md)
**Depends On**: Phase 0 (Code Quality Remediation)

---

## Objective

Implement a scheduling system that enables time-based triggers for camera operations (recording, timelapse, capture) and temperature profiles. Allow users to automate observation routines without manual intervention.

## Prerequisites

- [ ] Phase 0 complete (code quality issues resolved)
- [ ] Camera operations working (already complete)
- [ ] Optional: Phase 2 complete (for temperature profile triggers)

---

## Deliverables

### 1. Backend: APScheduler Integration

**Purpose**: Core scheduling engine

**Tasks**:
- [ ] Add APScheduler dependency
- [ ] Configure SQLite job store for persistence
- [ ] Integrate with FastAPI lifespan
- [ ] Handle missed jobs on startup (run late vs skip)
- [ ] Add scheduler health monitoring
- [ ] Create executor pool for job execution

**Configuration**:
```python
# Scheduler setup
scheduler = AsyncIOScheduler(
    jobstores={
        'default': SQLAlchemyJobStore(url=DATABASE_URL)
    },
    executors={
        'default': AsyncIOExecutor()
    },
    job_defaults={
        'coalesce': True,  # Combine missed runs
        'max_instances': 1,
        'misfire_grace_time': 300  # 5 minutes
    }
)
```

**Files**:
- `backend/app/services/scheduler/engine.py` (new)
- `backend/app/services/scheduler/__init__.py` (new)
- `backend/requirements.txt` (add APScheduler)

---

### 2. Backend: Schedule Database Model

**Purpose**: Store user-defined schedules

**Tasks**:
- [ ] Create Schedule model
- [ ] Support schedule types (one-time, recurring, cron)
- [ ] Support action types (record, timelapse, capture, temp profile)
- [ ] Link schedules to cameras
- [ ] Track schedule execution history

**Schema**:
```python
class Schedule:
    id: int
    name: str
    description: str | None
    enabled: bool

    # Schedule type and timing
    schedule_type: str  # "once" | "interval" | "cron"

    # For "once" type
    run_at: datetime | None

    # For "interval" type
    interval_seconds: int | None

    # For "cron" type
    cron_expression: str | None  # e.g., "0 8 * * *" (8am daily)

    # Action configuration
    action_type: str  # "recording" | "timelapse" | "capture" | "temp_profile"
    camera_id: int | None
    action_params: dict  # JSON blob with action-specific settings

    # Duration (for recording/timelapse)
    duration_seconds: int | None

    # Metadata
    created_at: datetime
    updated_at: datetime
    last_run_at: datetime | None
    next_run_at: datetime | None

class ScheduleRun:
    id: int
    schedule_id: int
    started_at: datetime
    completed_at: datetime | None
    status: str  # "running" | "completed" | "failed"
    job_id: int | None  # Link to Job if recording/timelapse
    error: str | None
```

**Files**:
- `backend/app/db/models/schedule.py` (new)
- `backend/app/db/repositories/schedule.py` (new)

---

### 3. Backend: Schedule Executor

**Purpose**: Execute scheduled actions

**Tasks**:
- [ ] Create executor for each action type
- [ ] Handle recording start/stop by duration
- [ ] Handle timelapse start/stop by frame count
- [ ] Handle still capture
- [ ] Handle temperature profile activation
- [ ] Link to Job system for tracking
- [ ] Handle execution errors gracefully

**Interface**:
```python
class ScheduleExecutor:
    async def execute_recording(schedule: Schedule) -> Job
    async def execute_timelapse(schedule: Schedule) -> Job
    async def execute_capture(schedule: Schedule) -> str  # file path
    async def execute_temp_profile(schedule: Schedule) -> None
```

**Files**:
- `backend/app/services/scheduler/executor.py` (new)

---

### 4. Backend: Conflict Detection

**Purpose**: Prevent scheduling conflicts

**Tasks**:
- [ ] Detect overlapping recordings on same camera
- [ ] Detect timelapse/recording conflicts
- [ ] Warn on resource conflicts (H.264 encoder limit)
- [ ] Provide conflict resolution suggestions
- [ ] Allow force-override with warning

**Files**:
- `backend/app/services/scheduler/conflicts.py` (new)

---

### 5. Backend: API Endpoints

**Purpose**: Manage schedules via API

**Endpoints**:
```
GET    /api/v1/schedules              → List all schedules
POST   /api/v1/schedules              → Create schedule
GET    /api/v1/schedules/{id}         → Get schedule details
PUT    /api/v1/schedules/{id}         → Update schedule
DELETE /api/v1/schedules/{id}         → Delete schedule
POST   /api/v1/schedules/{id}/enable  → Enable schedule
POST   /api/v1/schedules/{id}/disable → Disable schedule
POST   /api/v1/schedules/{id}/run-now → Run schedule immediately
GET    /api/v1/schedules/{id}/history → Execution history
GET    /api/v1/schedules/upcoming     → Next N scheduled runs
GET    /api/v1/schedules/conflicts    → Check for conflicts
```

**Tasks**:
- [ ] Create schedules router
- [ ] Implement all CRUD endpoints
- [ ] Add validation (cron syntax, conflicts)
- [ ] Add upcoming/history endpoints
- [ ] Update OpenAPI schema

**Files**:
- `backend/app/api/routes/schedules.py` (new)
- `backend/app/schemas/schedule.py` (new)

---

### 6. Frontend: Schedule List

**Purpose**: View and manage schedules

**Tasks**:
- [ ] Create `SchedulesPage.tsx`
- [ ] List schedules with status indicators
- [ ] Show next run time
- [ ] Enable/disable toggle
- [ ] Edit/delete buttons
- [ ] "Run Now" button

**Files**:
- `frontend/src/pages/SchedulesPage.tsx` (new)
- `frontend/src/pages/SchedulesPage.css` (new)
- `frontend/src/App.tsx` (add route)
- `frontend/src/components/Layout.tsx` (add nav)

---

### 7. Frontend: Schedule Form

**Purpose**: Create and edit schedules

**Tasks**:
- [ ] Create `ScheduleForm.tsx` component
- [ ] Schedule type selector (once/interval/cron)
- [ ] Date/time picker for one-time
- [ ] Interval input for recurring
- [ ] Cron expression builder (with presets)
- [ ] Action type selector
- [ ] Camera selector
- [ ] Action-specific options
- [ ] Duration input
- [ ] Validation and error messages

**Cron Presets**:
- Daily at specific time
- Weekdays only
- Weekends only
- Hourly
- Custom expression

**Files**:
- `frontend/src/components/ScheduleForm.tsx` (new)
- `frontend/src/components/ScheduleForm.css` (new)

---

### 8. Frontend: Calendar/Timeline View

**Purpose**: Visual schedule overview

**Tasks**:
- [ ] Create `ScheduleCalendar.tsx` component
- [ ] Day/week/month views
- [ ] Show scheduled runs as blocks
- [ ] Highlight conflicts
- [ ] Click to edit schedule
- [ ] Drag to reschedule (optional)

**Files**:
- `frontend/src/components/ScheduleCalendar.tsx` (new)
- `frontend/src/components/ScheduleCalendar.css` (new)

---

### 9. Frontend: Conflict Warnings

**Purpose**: Show scheduling conflicts

**Tasks**:
- [ ] Create conflict indicator component
- [ ] Show in schedule form when conflict detected
- [ ] Show in calendar view
- [ ] Provide resolution suggestions

**Files**:
- `frontend/src/components/ScheduleConflict.tsx` (new)

---

### 10. Frontend: Quick Schedule

**Purpose**: Easily schedule from camera page

**Tasks**:
- [ ] Add "Schedule" button to camera tabs
- [ ] Quick schedule modal
- [ ] Pre-fill camera and action
- [ ] Common presets (start in 1 hour, daily at this time)

**Files**:
- `frontend/src/components/camera/*.tsx` (extend)
- `frontend/src/components/QuickScheduleModal.tsx` (new)

---

## Action Types

### Recording Action
```json
{
  "action_type": "recording",
  "camera_id": 1,
  "action_params": {
    "quality": "high",
    "format": "mp4"
  },
  "duration_seconds": 3600
}
```

### Timelapse Action
```json
{
  "action_type": "timelapse",
  "camera_id": 1,
  "action_params": {
    "interval_seconds": 30,
    "total_frames": 120,
    "quality": "high"
  }
}
```

### Capture Action
```json
{
  "action_type": "capture",
  "camera_id": 1,
  "action_params": {
    "quality": 95
  }
}
```

### Temperature Profile Action
```json
{
  "action_type": "temp_profile",
  "camera_id": null,
  "action_params": {
    "profile_id": 1
  }
}
```

---

## Testing Requirements

### Backend Tests
- [ ] Unit tests for scheduler engine
- [ ] Test schedule execution for each action type
- [ ] Test cron parsing and next-run calculation
- [ ] Test conflict detection
- [ ] Test missed job handling
- [ ] API endpoint tests

### Frontend Tests
- [ ] Component tests for ScheduleForm
- [ ] Test cron preset generation
- [ ] Test calendar view rendering

### Integration Tests
- [ ] Create schedule, wait for execution, verify result
- [ ] Test schedule enable/disable
- [ ] Test schedule modification while running

---

## Quality Gate

- [ ] Schedules execute reliably within ±30 seconds
- [ ] Conflicts detected before saving
- [ ] No HIGH or CRITICAL issues
- [ ] Missed jobs handled appropriately

---

## Success Criteria

1. Can schedule recording to start at specific time
2. Recurring schedules execute reliably
3. Conflicts detected and reported
4. Schedules persist across restarts
5. History viewable for troubleshooting

---

## Notes

- APScheduler's SQLAlchemy job store provides persistence
- Cron expressions can be complex; provide good presets
- Consider timezone handling (store in UTC, display local)
- Rate-limit executions to prevent flooding

---

**Estimated Effort**: 3-4 days
**Dependencies**: Phase 0 complete
**Parallel**: Can run alongside Phase 1/2

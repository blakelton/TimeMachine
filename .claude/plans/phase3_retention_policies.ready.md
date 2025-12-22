# Phase 3: Retention Policies

> Automatic cleanup of old media files

**Status**: ready
**Created**: 2025-12-21
**Parent**: [masterplan.md](masterplan.md)
**Depends On**: Phase 0 (Code Quality Remediation)

---

## Objective

Implement automatic cleanup of media files based on configurable retention policies. Enable unattended long-running operation without manual disk space management.

## Prerequisites

- [ ] Phase 0 complete (code quality issues resolved)
- [ ] Storage service working (already complete)

---

## Deliverables

### 1. Backend: Retention Policy Model

**Purpose**: Define and store retention policies

**Tasks**:
- [ ] Create RetentionPolicy database model
- [ ] Support policy types: age, size, count
- [ ] Support per-camera policies
- [ ] Support global default policy
- [ ] Add policy priority/ordering

**Schema**:
```python
class RetentionPolicy:
    id: int
    name: str
    description: str | None
    policy_type: str  # "age" | "size" | "count"
    enabled: bool
    priority: int  # Lower = higher priority

    # Age-based settings
    max_age_days: int | None

    # Size-based settings
    max_size_gb: float | None
    target_size_gb: float | None  # Delete until this size reached

    # Count-based settings
    max_file_count: int | None

    # Scope
    camera_id: int | None  # None = global
    file_types: list[str]  # ["video", "image", "timelapse"] or ["*"]

    # Protection
    protect_starred: bool  # Don't delete starred/favorited files
    protect_newest_count: int  # Always keep N newest files

    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_run_at: datetime | None
```

**Files**:
- `backend/app/db/models/retention.py` (new)
- `backend/app/db/repositories/retention.py` (new)

---

### 2. Backend: Cleanup Service

**Purpose**: Execute retention policies

**Tasks**:
- [ ] Create `backend/app/services/retention/cleanup.py`
- [ ] Implement age-based cleanup
- [ ] Implement size-based cleanup
- [ ] Implement count-based cleanup
- [ ] Add dry-run mode for preview
- [ ] Add protection checks (starred, newest)
- [ ] Log all deletions
- [ ] Handle deletion errors gracefully

**Interface**:
```python
class CleanupService:
    async def run_policy(policy_id: int, dry_run: bool = False) -> CleanupResult
    async def run_all_policies(dry_run: bool = False) -> list[CleanupResult]
    async def preview_cleanup(policy_id: int) -> list[FileInfo]
    async def get_candidates(policy: RetentionPolicy) -> list[FileInfo]

@dataclass
class CleanupResult:
    policy_id: int
    files_deleted: int
    bytes_freed: int
    errors: list[str]
    dry_run: bool
```

**Files**:
- `backend/app/services/retention/cleanup.py` (new)
- `backend/app/services/retention/__init__.py` (new)

---

### 3. Backend: Scheduled Cleanup

**Purpose**: Run cleanup automatically on schedule

**Tasks**:
- [ ] Create cleanup scheduler (daily, hourly, or configurable)
- [ ] Integrate with FastAPI lifespan
- [ ] Add health check for scheduler
- [ ] Handle long-running cleanup gracefully
- [ ] Avoid cleanup during active recording

**Files**:
- `backend/app/services/retention/scheduler.py` (new)
- `backend/app/main.py` (integrate)

---

### 4. Backend: API Endpoints

**Purpose**: Manage retention policies via API

**Endpoints**:
```
GET    /api/v1/retention/policies          → List all policies
POST   /api/v1/retention/policies          → Create policy
GET    /api/v1/retention/policies/{id}     → Get policy details
PUT    /api/v1/retention/policies/{id}     → Update policy
DELETE /api/v1/retention/policies/{id}     → Delete policy
POST   /api/v1/retention/policies/{id}/run → Run policy now
GET    /api/v1/retention/policies/{id}/preview → Preview what would be deleted
GET    /api/v1/retention/history           → Cleanup history/logs
GET    /api/v1/retention/stats             → Retention statistics
```

**Tasks**:
- [ ] Create retention router
- [ ] Implement all CRUD endpoints
- [ ] Add run/preview endpoints
- [ ] Add validation
- [ ] Update OpenAPI schema

**Files**:
- `backend/app/api/routes/retention.py` (new)
- `backend/app/schemas/retention.py` (new)

---

### 5. Backend: Cleanup History

**Purpose**: Log and track cleanup operations

**Tasks**:
- [ ] Create CleanupRun model for history
- [ ] Log each cleanup execution
- [ ] Track files deleted, bytes freed, errors
- [ ] Provide history query API

**Schema**:
```python
class CleanupRun:
    id: int
    policy_id: int
    started_at: datetime
    completed_at: datetime | None
    status: str  # "running" | "completed" | "failed"
    files_deleted: int
    bytes_freed: int
    errors: list[str] | None
    dry_run: bool
```

**Files**:
- `backend/app/db/models/retention.py` (extend)

---

### 6. Frontend: Retention Settings Panel

**Purpose**: Configure retention policies

**Tasks**:
- [ ] Create `RetentionPanel.tsx` component
- [ ] List existing policies with edit/delete
- [ ] Add policy creation form
- [ ] Policy type selector (age/size/count)
- [ ] Camera scope selector
- [ ] Protection options
- [ ] Run now button
- [ ] Preview button (show what would be deleted)

**Files**:
- `frontend/src/components/settings/RetentionPanel.tsx` (new)
- `frontend/src/components/settings/RetentionPanel.css` (new)
- `frontend/src/pages/SystemPage.tsx` (integrate)

---

### 7. Frontend: Policy Form

**Purpose**: Create/edit retention policies

**Tasks**:
- [ ] Create `RetentionPolicyForm.tsx` component
- [ ] Form fields for all policy options
- [ ] Validation (sensible limits)
- [ ] Help text explaining each option
- [ ] Modal or inline form

**Files**:
- `frontend/src/components/settings/RetentionPolicyForm.tsx` (new)

---

### 8. Frontend: Cleanup Preview

**Purpose**: Show what will be deleted before running

**Tasks**:
- [ ] Create preview modal/page
- [ ] List files that would be deleted
- [ ] Show total size to be freed
- [ ] Confirm/cancel buttons
- [ ] Loading state for large previews

**Files**:
- `frontend/src/components/RetentionPreview.tsx` (new)

---

### 9. Frontend: Cleanup History

**Purpose**: View past cleanup operations

**Tasks**:
- [ ] Add history section to retention panel
- [ ] Show recent cleanup runs
- [ ] Display files deleted, space freed
- [ ] Show any errors

**Files**:
- `frontend/src/components/settings/RetentionHistory.tsx` (new)

---

### 10. Frontend: Storage Warnings

**Purpose**: Alert users about disk space

**Tasks**:
- [ ] Enhance existing disk space warnings
- [ ] Show when cleanup is needed
- [ ] Suggest policy adjustments
- [ ] Link to retention settings

**Files**:
- `frontend/src/components/SystemStats.tsx` (enhance)

---

## Policy Examples

### Example 1: Age-Based (30-day retention)
```json
{
  "name": "Default 30-day cleanup",
  "policy_type": "age",
  "max_age_days": 30,
  "file_types": ["*"],
  "protect_starred": true,
  "protect_newest_count": 10
}
```

### Example 2: Size-Based (Keep under 50GB)
```json
{
  "name": "Storage limit 50GB",
  "policy_type": "size",
  "max_size_gb": 50,
  "target_size_gb": 45,
  "file_types": ["video"],
  "protect_starred": true
}
```

### Example 3: Count-Based (Keep 100 timelapses)
```json
{
  "name": "Timelapse limit",
  "policy_type": "count",
  "max_file_count": 100,
  "camera_id": 1,
  "file_types": ["timelapse"]
}
```

---

## Testing Requirements

### Backend Tests
- [ ] Unit tests for cleanup service (all policy types)
- [ ] Test protection logic (starred, newest)
- [ ] Test dry-run mode
- [ ] Test edge cases (empty directories, permission errors)
- [ ] API endpoint tests
- [ ] Scheduler tests

### Frontend Tests
- [ ] Component tests for RetentionPanel
- [ ] Form validation tests
- [ ] Preview display tests

### Integration Tests
- [ ] Create files, run cleanup, verify deletion
- [ ] Test policy priority ordering
- [ ] Test per-camera vs global policies

---

## Quality Gate

- [ ] No accidental deletion of recent/protected files
- [ ] Dry-run accurately predicts deletions
- [ ] All cleanup actions logged
- [ ] No HIGH or CRITICAL issues

---

## Success Criteria

1. Disk space stays within configured limits
2. No accidental deletion of protected files
3. Cleanup logs accessible in UI
4. Dry-run preview works accurately
5. Scheduled cleanup runs reliably

---

## Notes

- Always implement dry-run first; test thoroughly
- Consider file system locking during cleanup
- Log deletions to separate file for audit trail
- Protect newest N files as safety net

---

**Estimated Effort**: 2-3 days
**Dependencies**: Phase 0 complete
**Parallel**: Can run alongside Phase 1/2

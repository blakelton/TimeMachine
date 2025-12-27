# Development Progress Log

This file is the **mandatory audit trail** of all development work in this project.

## Purpose

Track all:
- Plan status changes (ready → in_progress → completed)
- Session starts and pauses
- Unplanned changes
- Documentation audits

## Entry Guidelines

### Planned Work (Plan Status Changes)

```markdown
### [YYYY-MM-DD HH:MM] Plan Status: `plan_name`
**Transition**: [from_status] → [to_status]
**Reason**: [Why this change]
**Files Affected**: [Key files]
**Notes**: [Additional context]
```

### Session Events

```markdown
### [YYYY-MM-DD HH:MM] Session: [Started|Paused|Resumed]
**Plan**: `plan_name` (if applicable)
**Progress**: [Summary of progress]
**Next Steps**: [What to do next]
**Blockers**: [Any blockers, or "None"]
```

### Unplanned Work

```markdown
### [YYYY-MM-DD HH:MM] Unplanned: `brief_description`
**Type**: Bug Fix | Feature | Refactor | Config | Documentation
**Files Affected**: [List of files]
**Reason**: [Why this was done outside formal planning]
**Impact**: [What changed]
**Notes**: [Additional context]
```

### Documentation Audits

```markdown
### [YYYY-MM-DD HH:MM] Documentation Audit
**Command**: /document
**Plans Reviewed**: [N]
**Plans Moved**: [N] to old/
**Changes Documented**: [N]
**Docs Updated**: [List or "None"]
```

---

## Log Entries

<!-- New entries should be added at the top, below this line -->

### [2025-12-26 23:00] Bug Fix: Camera Preview Navigation - FINAL FIX
**Type**: Bug Fix
**Status**: COMPLETED
**Source**: User report - camera previews break after navigating between pages

**Root Cause (FINAL)**:
Browser connection pooling with MJPEG streams. Browsers have ~6 connection limit per domain. MJPEG streams are long-lived HTTP connections that don't close immediately when React navigates away. Connection pool becomes exhausted with stale connections, preventing new streams from loading.

**Key User Observations**:
- Clicking browser Stop button always fixed the issue
- Browser refresh worked fine, but React navigation broke streams
- Issue varied between browsers/systems (connection pool behavior differs)

**Final Fix Applied**:
Added `window.stop()` to LiveThumbnail cleanup function. This mimics clicking the browser Stop button, forcefully aborting all pending HTTP requests and freeing the connection pool.

**Additional Fixes During Investigation**:
1. Component key includes `navigationKey` from `useLocation().key` for forced remounts
2. 500ms mount delay gives browser time to close previous connections
3. Timestamp in stream URL prevents cache reuse
4. `imgMounted` state controls DOM presence for clean unmount/remount
5. PreviewTab treats "already running" as success instead of error

**Files Changed**:
- `frontend/src/components/LiveThumbnail.tsx` - window.stop() cleanup, imgMounted state, mount delay
- `frontend/src/pages/HomePage.tsx` - navigationKey in CameraPreviewCard keys
- `frontend/src/components/CameraPreviewCard.tsx` - refreshKey prop pass-through
- `frontend/src/components/camera/PreviewTab.tsx` - "already running" handling

**Troubleshooting Documentation**:
- `.claude/troubleshooting/camera_preview_navigation.md` - Full investigation log with 9 fix attempts documented

**Quality Evaluation**:
- CRITICAL: 0
- HIGH: 1 - `window.stop()` is aggressive (affects all requests on page). Acknowledged as intentional - user testing confirmed browser Stop button is the only reliable fix for MJPEG connection pool exhaustion.
- MEDIUM: 3 - Duplicate state reset logic, state during render, fragile string matching for error detection
- LOW: 5 - Type inconsistencies, magic numbers, redundant patterns
- Overall: No blockers. HIGH issue is intentional design decision based on user testing.

---

### [2025-12-26 17:50] Bug Fix: Dashboard Camera Previews Disappear After Navigation
**Type**: Bug Fix
**Status**: COMPLETED
**Source**: User report - cameras not showing on kiosk, previews disappear after navigating

**User Acceptance Criteria**:
- Navigate: home → Micro 1 → Micro 2 → home → repeat
- All video feeds should work without interruption across navigation

**Root Cause Analysis**:
1. Backend confirmed all streams were running (`preview_state: "running"`, ports listening)
2. Nginx logs showed NO stream requests being made by frontend after navigation
3. The `LiveThumbnail` component's error state ("No signal") persisted across navigation
4. React preserved component instances with stale state because the component key was stable
5. Key `live-${camera_id}` didn't change when navigating away and back to dashboard

**Fix Applied**:
1. **Modified `CameraPreviewCard.tsx`** - Changed LiveThumbnail key to include refreshKey:
   - From: `key={live-${camera_id}}`
   - To: `key={live-${camera_id}-${refreshKey ?? "default"}}`
2. **Used `useMemo` in `HomePage.tsx`** - Creates unique `mountKey` on each mount:
   - `const mountKey = useMemo(() => Date.now().toString(), [])`
   - This key changes when user navigates away and back, forcing LiveThumbnail remount

**Files Changed**:
- `frontend/src/components/CameraPreviewCard.tsx` - Added refreshKey to LiveThumbnail key
- `frontend/src/components/LiveThumbnail.tsx` - Removed debug console.log
- `frontend/src/pages/HomePage.tsx` - Added mountKey generation

**Test Created**:
- `scripts/test-camera-navigation.sh` - Automated test using xdotool to navigate and verify streams

**Quality Evaluation**:
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 0 (debug logs removed)
- LOW: 2 (code simplification opportunities, not blockers)

---

### [2025-12-26 04:35] Bug Fix: Camera Preview Navigation Instability (Third Fix)
**Type**: Bug Fix
**Status**: COMPLETED
**Source**: User report - preview shows "Preview not running" after navigating between cameras

**User Test Case**:
- Navigate: home → Micro 1 → Micro 2 → home → Micro 2
- By the second visit to Micro 2, preview showed "Preview not running" despite backend reporting "running"

**Root Cause Analysis**:
1. Backend confirmed all streams were running and producing data (verified via curl and netcat)
2. Issue isolated to frontend React component state management
3. When navigating between cameras, React reused the PreviewTab component instance instead of remounting
4. State from previous camera could interfere with new camera initialization
5. React hooks order violation - `isInitializing` state was declared inside an effect block

**Fixes Applied**:
1. **Added `key={cameraIdNum}` to PreviewTab** - Forces complete unmount/remount when navigating between cameras
2. **Fixed React hooks order** - Moved `isInitializing` state declaration to component top level with other state
3. **Added loading state during initialization** - Shows "Checking camera..." while status API call is in flight
4. **Cleaned up console.log statements** - Removed debug logging after validation

**Files Changed**:
- `frontend/src/components/camera/PreviewTab.tsx` - Fixed hooks order, added isInitializing state
- `frontend/src/pages/CameraPage.tsx` - Added key prop to force remount

**Quality Evaluation**:
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 4 (stale ref in CameraControls - pre-existing, not related to this fix)
- LOW: 6 (console.log removed, type assertions documented)

---

### [2025-12-26 03:16] Bug Fix: Camera Preview Intermittent Disappearance (Second Fix)
**Type**: Bug Fix
**Status**: COMPLETED
**Source**: User report - issue persisted after first fix

**Discovery**:
Initial fix (removing cleanup effect, increasing timeouts) was insufficient. Logs showed:
- `port_ready: False` despite increased timeouts
- Port opens immediately when GStreamer starts, but no data flows for several seconds
- Frontend connects to open port but receives no MJPEG frames
- The `_wait_for_port` check (socket connect) passed, but stream wasn't producing data

**Root Cause Refined**:
GStreamer's `tcpserversink` opens the TCP port immediately when pipeline starts, but actual MJPEG frame production requires full pipeline negotiation (~2-5 seconds). The socket check returned success prematurely.

**Second Fix Applied**:
1. **Renamed `_wait_for_port` → `_wait_for_stream_ready`** - Now actually connects to the stream and reads data to verify MJPEG frames are flowing
2. **Increased timeouts** - 6s for USB, 8s for CSI to accommodate slower cameras
3. **Improved LiveThumbnail retry logic** - Increased retries from 3 to 5, reduced delay from 2000ms to 1500ms for faster recovery
4. **Removed unused `socket` import** - Cleanup after refactoring

**Files Changed**:
- `backend/app/services/camera/preview.py` - New `_wait_for_stream_ready()` that verifies data flow
- `frontend/src/components/LiveThumbnail.tsx` - More retries, faster recovery

**Testing Results**:
- All cameras now show `port_ready: True` in logs
- Stream verification takes 0.5-1.5 seconds (data actually flowing)
- Dashboard immediately shows working previews

**Quality Evaluation**:
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 0
- LOW: 0

---

### [2025-12-26 03:06] Bug Fix: Camera Preview Intermittent Disappearance (Initial Attempt)
**Type**: Bug Fix
**Status**: SUPERSEDED by second fix above
**Source**: User report - cameras show on dashboard, disappear when navigating

**Root Cause**:
Race condition between two preview management systems:
1. PreviewTab.tsx cleanup effect stopped previews on component unmount
2. Dashboard watchdog auto-started previews for idle cameras
3. When navigating between pages, stop→start→stop→start cycles caused:
   - `preview_stream_connection_refused` errors (frontend connects before port ready)
   - `preview_stream_not_running` warnings
   - Preview gaps of 5-7 seconds

**Fix Applied**:
1. **Removed cleanup effect from PreviewTab.tsx** - Previews are now a shared resource managed by the dashboard watchdog. They only stop when:
   - User explicitly clicks "Stop Preview"
   - A capture/recording/timelapse operation needs the camera
   - The camera is disabled

2. **Increased port wait timeouts in preview.py** - Backend now waits longer for GStreamer to initialize before returning success:
   - USB cameras: 0.8s → 4.0s
   - CSI cameras: 2.5s → 5.0s

3. **Fixed deprecated asyncio API** - Changed `asyncio.get_event_loop()` to `asyncio.get_running_loop()` for Python 3.10+ compatibility

**Files Changed**:
- `frontend/src/components/camera/PreviewTab.tsx` - Removed unmount cleanup effect
- `backend/app/services/camera/preview.py` - Increased timeouts, fixed deprecated API

**Note**: This fix was insufficient - user reported issue persisting. See second fix above.

---

### [2025-12-26 01:35] Improvement: Test Coverage and TypeScript API Wrappers
**Type**: Testing / Type Safety
**Status**: COMPLETED
**Source**: AI Evaluation Executive Report recommendations

**Description**:
Expanded backend test coverage from 18 to 59 tests, and created typed TypeScript API wrapper functions to eliminate `as any` casts throughout the frontend.

**Backend Test Files Created**:
- `backend/tests/test_repositories.py` (30 tests):
  - CameraRepository: create, get, update, get_enabled, get_all
  - ObservationRepository: create, get_active, mark_completed/failed/stopped, update_progress, get_completed, eager loading, cleanup_stale_running, count, delete
  - JobRepository: get_running, mark_completed/failed/interrupted, cleanup_stale_running, timelapse_progress, filter by camera/type

- `backend/tests/test_validation_service.py` (11 tests):
  - CameraInUseResult dataclass tests
  - check_camera_in_use: detects DB observations, recording service, timelapse service
  - require_camera_available: raises HTTPException 409 with proper messages

**Frontend TypeScript Files Created**:
- `frontend/src/api/camera.ts` - 14 typed wrapper functions:
  - captureImage, startPreview, stopPreview, getPreviewStatus
  - startRecording, stopRecording, getRecordingStatus
  - startTimelapse, stopTimelapse, getTimelapseStatus
  - checkCameraHealth, getCamera, updateCamera, deleteCamera

- `frontend/src/api/observations.ts` - 14 typed wrapper functions:
  - startObservation, getActiveObservationByCamera, getObservation
  - getObservationStatus, stopObservation, deleteObservation
  - updateObservationNotes, getObservationThumbnail, getObservationPreview
  - generateObservationPreview, getObservationMedia, batchDeleteObservations
  - listActiveObservations, listCompletedObservations

- `frontend/src/api/index.ts` - Barrel export for all API functions

**Benefits**:
- Test coverage increased 3x (18 → 59 tests)
- Repository layer fully tested including eager loading
- Validation service 100% test coverage
- TypeScript wrappers provide proper typing for path-parameterized endpoints
- Frontend code can now use typed wrapper functions instead of `as any` casts
- All wrappers match OpenAPI spec exactly (PUT vs PATCH, query vs body params)

**Quality Evaluation**:
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 1 (fixed - unused MagicMock import)
- LOW: 7 (optional improvements noted)
- 59 tests passing, frontend builds successfully

---

### [2025-12-25 20:15] Refactor: Extract Camera In-Use Validation to Service Layer
**Type**: Refactor
**Status**: COMPLETED
**Source**: AI Evaluation Executive Report recommendation

**Description**:
Extracted duplicated camera in-use validation logic from API routes into a reusable service module.

**Files Created**:
- `backend/app/services/camera/validation.py`:
  - `CameraInUseResult` dataclass for structured results
  - `check_camera_in_use()` - checks database + in-memory services
  - `require_camera_available()` - raises HTTPException if in use

**Files Modified**:
- `backend/app/api/routes/cameras/crud.py`:
  - Removed ~60 lines of duplicated validation code from `update_camera` and `delete_camera`
  - Now uses `require_camera_available()` single function call
  - Removed unused imports (`recording_service`, `timelapse_service`, `PipelineState`, `ObservationRepository`)

**Before (in each endpoint)**:
```python
# Check database
active_obs = await obs_repo.get_active_by_camera(camera_id)
if active_obs: raise HTTPException(...)

# Check recording service
if recording_service.get_recording_state(camera_id) == PipelineState.RUNNING:
    raise HTTPException(...)

# Check timelapse service
if timelapse_service.is_running(camera_id):
    raise HTTPException(...)
```

**After**:
```python
await require_camera_available(camera_id, session, operation="edit camera")
```

**Benefits**:
- Single source of truth for camera validation logic
- Consistent error messages across endpoints
- Easier to test and maintain
- Reduced route handler complexity

**Quality**: All 18 tests passing, syntax verified

---

### [2025-12-25 20:00] Refactor: Reduce capture_image Endpoint Complexity
**Type**: Refactor
**Status**: COMPLETED
**Source**: AI Evaluation Executive Report recommendation

**Description**:
Refactored the `capture_image` endpoint in `cameras/capture.py` to reduce cyclomatic complexity by extracting helper functions.

**Extracted Functions**:
- `PreviewState` dataclass - captures preview state for restoration
- `_stop_preview_for_capture()` - stops preview and waits for device release
- `_wait_for_device_release()` - dispatches to USB or CSI wait logic
- `_wait_for_usb_device_release()` - polls fuser for device release
- `_restart_preview()` - restarts preview with timeout protection
- `_execute_capture()` - performs capture and creates observation record

**Main Endpoint Simplification**:
- Before: ~100 lines with nested try/finally, loops, and conditionals
- After: ~50 lines with clear delegation to helper functions

**Additional Improvements**:
- Fixed inverted exception handling in USB device wait logic
- Changed shell command injection risk: `create_subprocess_shell` → `create_subprocess_exec`
- Added clear documentation that `_restart_preview()` intentionally suppresses exceptions
- Added named constant for max USB release attempts

**Quality**: All 18 tests passing, syntax verified

---

### [2025-12-25 19:45] Refactor: Eager Loading to Fix N+1 Queries
**Type**: Performance / Refactor
**Status**: COMPLETED
**Source**: AI Evaluation Executive Report recommendation

**Description**:
Added eager loading support to repository methods to prevent N+1 database queries. The `list_completed_observations` endpoint was making 1 query per observation to fetch camera names, resulting in 51 queries for 50 observations.

**Changes**:
- `backend/app/db/repositories/observation.py`:
  - Added `selectinload` import
  - Added `eager_load_camera: bool = False` parameter to `get_completed()`
  - When enabled, uses SQLAlchemy's `selectinload()` to batch-fetch camera relationships

- `backend/app/db/repositories/job.py`:
  - Added `selectinload` import
  - Added `eager_load_camera: bool = False` parameter to `get_running()`

- `backend/app/api/routes/observations/crud.py`:
  - Updated `list_completed_observations` to use `eager_load_camera=True`
  - Changed camera access from `await camera_repo.get(obs.camera_id)` to `obs.camera`
  - Removed unused `CameraRepository` import

**Performance Impact**:
- Before: 51 queries (1 + N) for 50 observations
- After: 2 queries (observations + cameras via selectinload)
- ~96% reduction in database queries for pagination endpoint

**Quality**: All 18 tests passing, syntax verified

---

### [2025-12-25 19:30] Refactor: Status Enums for Observations and Jobs
**Type**: Refactor
**Status**: COMPLETED
**Source**: AI Evaluation Executive Report recommendation

**Description**:
Created Python `StrEnum` classes for observation and job status values to replace magic string literals throughout the codebase.

**Enums Created** (in `backend/app/core/constants.py`):
- `ObservationStatus`: RUNNING, COMPLETED, FAILED, STOPPED
- `JobStatus`: PENDING, RUNNING, COMPLETED, FAILED, INTERRUPTED

**Files Modified**:
- `backend/app/core/constants.py` - Added enum definitions
- `backend/app/db/models/observation.py` - Import and re-export enum
- `backend/app/db/models/job.py` - Import and re-export enum
- `backend/app/db/repositories/observation.py` - Use enum values
- `backend/app/db/repositories/job.py` - Use enum values
- `backend/app/services/observation/lifecycle.py` - Use enum values
- `backend/app/services/observation/metadata.py` - Use enum values
- `backend/app/services/camera/recording.py` - Use enum values
- `backend/app/services/camera/timelapse/service.py` - Use enum values
- `backend/app/api/routes/jobs.py` - Use enum values
- `backend/app/api/routes/observations/batch.py` - Use enum values
- `backend/app/api/routes/cameras/capture.py` - Use enum values

**Benefits**:
- Type-safe status comparisons (IDE autocomplete, typo prevention)
- Centralized status definitions
- StrEnum serializes as string for database compatibility
- Easier refactoring if status values change

**Quality**: All 18 tests passing, syntax verified

---

### [2025-12-25 18:50] Documentation Audit
**Command**: /document
**Plans Reviewed**: 14 (6 active, 7 completed, 1 master)
**Plans Moved**: 1 to completed/
**Changes Documented**: 0 (all recent changes already logged)
**Docs Updated**: README.md, masterplan.md

**Actions Taken**:
1. Moved `phase1_temperature_monitoring.ready.md` → `completed/phase1_temperature_monitoring.md`
   - Phase 1 was fully implemented as Environment Monitoring System
   - Work documented in progress log on 2025-12-23
2. Updated `masterplan.md`:
   - Marked Phase 1 deliverables as complete
   - Added completion notes with sensor types supported
   - Updated "Last updated" timestamp
3. Updated `README.md`:
   - Changed status to "Phase 1 Complete (Environment Monitoring)"
   - Added Environment Monitoring features section
   - Added Environment API endpoints table
   - Added test infrastructure mention

**Integrity Check**:
- [x] All active plans validated (phases 2-6 ready)
- [x] No orphaned pause files
- [x] Progress log current
- [x] Documentation synced with code

---

### [2025-12-25 18:30] Plan Status: `refactor_get_observation_media`
**Transition**: ready → completed
**Reason**: Strategy pattern implementation already complete in media.py
**Files**:
- `backend/app/services/observation/media.py` - Strategy pattern with TimelapseMediaFinder, RecordingMediaFinder, StillMediaFinder
- `backend/app/api/routes/observations/media.py` - Using find_observation_media from strategy module
**Complexity**: Reduced from 22 to ~5 in route handler
**Notes**: Plan was created when work was already done; verified and moved to completed

### [2025-12-25 18:35] Plan Status: `improve_maintainability_index`
**Transition**: ready → completed
**Reason**: MI targets achieved through previous refactoring work
**Metrics**:
| File | Original MI | Current MI | Target | Status |
|------|-------------|------------|--------|--------|
| observation/service.py | 20.20 (D) | 48.10 (A) | ≥40 | ✅ |
| camera/timelapse.py | 25.93 (C) | 100.00 (A+) | ≥40 | ✅ |
**Notes**: Previous refactors (split_large_files, refactor_capture_loop, refactor_progress_tracker_loop) achieved all MI targets

---

### [2025-12-25 15:25] Bug Fix: `timelapse_video_only_2_seconds`
**Root Cause**: Stale timelapse observations marked as "failed" during system restart cleanup did not have their videos assembled. The media finder fell back to `preview.mp4` (2-second live preview) instead of the full `frames.mp4`.
**Fix**:
1. Modified `cleanup_stale_observations()` to attempt video assembly before marking as failed
2. Added `repair_observation()` service method for manual video assembly
3. Added `POST /observations/{id}/repair` API endpoint
4. Changed live preview from fixed 60 frames to "last 5 seconds of footage"
**Files Changed**:
- `backend/app/services/observation/service.py` - Added repair and assembly logic
- `backend/app/services/observation/preview.py` - Changed to 5-second preview
- `backend/app/api/routes/observations/lifecycle.py` - Added repair endpoint
- `backend/app/db/repositories/observation.py` - Added get_stale_running method
**Quality**: Evaluated - No CRITICAL issues. Medium: deprecated asyncio.get_event_loop usage noted for future fix.
**Manual Recovery**: Assembled videos for 2 failed observations (now 117s and 124s instead of 2s)

---

### [2025-12-25 14:50] Feature: `inline_environment_graphs`
**Summary**: Added inline temperature and humidity graphs with color-coded labels to timelapse overlay
**Files Changed**:
- `backend/app/services/camera/overlay.py` - Separate temp/humidity graphs, colored labels
- `backend/app/services/camera/timelapse.py` - Pre-load graph history from database
- `backend/app/db/repositories/environment_reading.py` - Added get_recent method
- `frontend/src/components/camera/StartObservationModal.tsx` - Changed label to "Add Graphs"
**Quality**: Evaluated - No CRITICAL/HIGH issues

---

### [2025-12-25 15:20] Documentation: `orchestration_rewrite`
**Summary**: Rewrote CLAUDE.md to make orchestration non-negotiable with mandatory gates
**Files Changed**: `.claude/CLAUDE.md`
**Quality**: N/A (documentation)

---

### [2025-12-23 22:20] Plan Status: `split_large_files`
**Transition**: ready → completed
**Reason**: Split 5 large files exceeding 500-line threshold into smaller focused modules
**Files Created**:

**Backend cameras.py → package (1,703 → 9 modules):**
- `backend/app/api/routes/cameras/__init__.py` (26 lines)
- `backend/app/api/routes/cameras/crud.py` (323 lines)
- `backend/app/api/routes/cameras/health.py` (67 lines)
- `backend/app/api/routes/cameras/discovery.py` (95 lines)
- `backend/app/api/routes/cameras/preview.py` (294 lines)
- `backend/app/api/routes/cameras/recording.py` (162 lines)
- `backend/app/api/routes/cameras/timelapse.py` (374 lines)
- `backend/app/api/routes/cameras/capture.py` (243 lines)
- `backend/app/api/routes/cameras/dashboard.py` (129 lines)

**Backend observation/service.py → split modules (1,481 → 9 modules):**
- `backend/app/services/observation/service.py` (499 lines)
- `backend/app/services/observation/lifecycle.py` (424 lines)
- `backend/app/services/observation/preview.py` (329 lines)
- `backend/app/services/observation/progress.py` (264 lines)
- `backend/app/services/observation/metadata.py` (147 lines)
- `backend/app/services/observation/completion.py` (22 lines)
- `backend/app/services/observation/utils.py` (64 lines)

**Backend timelapse.py → package (1,277 → 5 modules):**
- `backend/app/services/camera/timelapse/__init__.py` (29 lines)
- `backend/app/services/camera/timelapse/service.py` (563 lines)
- `backend/app/services/camera/timelapse/session.py` (538 lines)
- `backend/app/services/camera/timelapse/config.py` (95 lines)
- `backend/app/services/camera/timelapse/assembly.py` (114 lines)

**Backend observations.py → package (766 → 5 modules):**
- `backend/app/api/routes/observations/__init__.py` (18 lines)
- `backend/app/api/routes/observations/crud.py` (269 lines)
- `backend/app/api/routes/observations/lifecycle.py` (148 lines)
- `backend/app/api/routes/observations/media.py` (222 lines)
- `backend/app/api/routes/observations/batch.py` (166 lines)

**Frontend EnvironmentPanel.tsx → split components (611 → 4 components):**
- `frontend/src/components/settings/EnvironmentPanel.tsx` (365 lines)
- `frontend/src/components/environment/EnvironmentDeviceCard.tsx` (86 lines)
- `frontend/src/components/environment/EnvironmentDeviceForm.tsx` (211 lines)
- `frontend/src/components/environment/EnvironmentDeviceList.tsx` (88 lines)

**Files Removed**:
- `backend/app/api/routes/cameras.py` (replaced by package)
- `backend/app/api/routes/observations.py` (replaced by package)

**Architecture Improvements**:
- All modules now under 500 lines (React components under 300 lines)
- Clear separation of concerns per module
- Backward compatibility maintained via package __init__.py exports
- No functional changes - pure refactoring

**Notes**: Fixed FastAPI empty path route issue (`""` → `"/"`) in crud.py files

---

### [2025-12-23 21:30] Plan Status: `refactor_get_observation_media`
**Transition**: ready → completed
**Reason**: Reduce cyclomatic complexity from 22 to under 10

**Files Created**:
- `backend/app/services/observation/media.py` - Media file discovery service with Strategy Pattern

**Files Modified**:
- `backend/app/api/routes/observations.py` - Simplified get_observation_media endpoint

**Complexity Reduction Results**:
- `get_observation_media` endpoint: 22 (Grade D) → 4 (Grade A)
- TimelapseMediaFinder: ~3 complexity
- RecordingMediaFinder: ~5 complexity
- StillMediaFinder: ~5 complexity

**Architecture**: Strategy Pattern with TimelapseMediaFinder, RecordingMediaFinder, StillMediaFinder classes

---

### [2025-12-23 21:15] Plan Status: `refactor_progress_tracker_loop`
**Transition**: ready → completed
**Reason**: Reduce cyclomatic complexity from 26 to under 10

**Files Modified**:
- `backend/app/services/observation/service.py` - Refactored _progress_tracker_loop

**Complexity Reduction Results**:
- `_progress_tracker_loop`: 26 (Grade D) → 8 (Grade B)

**Architecture**: Extracted helper methods:
- `_check_pipeline_running()`
- `_analyze_timelapse_completion()`
- `_analyze_recording_completion()`
- `_handle_completion()`
- Added `CompletionReason` enum and `CompletionResult` dataclass

---

### [2025-12-23 21:00] Plan Status: `refactor_capture_loop`
**Transition**: ready → completed
**Reason**: Reduce cyclomatic complexity from 29 to under 10

**Files Modified**:
- `backend/app/services/camera/timelapse.py` - Refactored _capture_loop with State Machine

**Complexity Reduction Results**:
- `_capture_loop`: 29 (Grade E - CRITICAL) → 4 (Grade A)

**Architecture**: State Machine Pattern with CaptureState enum:
- INITIALIZING, WAITING, CAPTURING, PROCESSING, CHECKING_COMPLETION, RECOVERY, COMPLETED, ERROR
- Extracted helpers: `_check_completion()`, `_handle_recovery_mode()`, `_check_system_resources()`, `_execute_capture()`, `_process_captured_frame()`

---

### [2025-12-23 20:45] Created Implementation Plans for Critical Issues
**Type**: Planning
**Plans Created**:
1. `refactor_check_camera_health.ready.md` - Complexity 32 → <10
2. `refactor_capture_loop.ready.md` - Complexity 29 → <10
3. `refactor_progress_tracker_loop.ready.md` - Complexity 26 → <10
4. `refactor_get_observation_media.ready.md` - Complexity 22 → <10
5. `split_large_files.ready.md` - 5 files over 500 lines
6. `improve_maintainability_index.ready.md` - Maintainability improvements

**Source**: docs/ai_eval/executive_summary.md critical issues

---

### [2025-12-23 20:15] Unplanned: Dashboard Timelapse Preview Fix
**Type**: Bug Fix
**Files Modified**:
- `frontend/src/components/CameraPreviewCard.tsx`

**Reason**: Timelapse preview video not updating on dashboard during active observation
**Impact**: Added cache-busting with timestamp state that refreshes every 15 frames
**Solution**: Added `previewTimestamp` state and `lastFrameCount` tracking, video URL now includes `?t=${previewTimestamp}` query param

---

### [2025-12-23 20:30] Plan Status: `refactor_check_camera_health`
**Transition**: ready → in_progress → completed
**Reason**: Reduce cyclomatic complexity of check_camera_health endpoint from 32 to under 10
**Files Created**:
- `backend/app/services/camera/health.py` - Camera health checking service module

**Files Modified**:
- `backend/app/api/routes/cameras.py` - Simplified check_camera_health endpoint to use health service

**Complexity Reduction Results**:
- `check_camera_health` endpoint: 32 (Grade E - CRITICAL) → 3 (Grade A)
- Average complexity across new health.py module: 4.77 (Grade A)
- All individual functions in health.py: Grade A/B/C (all under 10)

**Architecture Improvements**:
- Extracted CSI camera health checking to `CSIHealthChecker` class
- Extracted USB camera health checking to `USBHealthChecker` class
- Implemented Strategy Pattern with `CameraHealthChecker` protocol
- Created reusable helper functions: `check_device_exists()`, `check_device_accessible()`
- Factory function `get_health_checker()` for type-specific checker selection
- Used `asyncio.to_thread()` for all subprocess calls to maintain async compatibility

**Functionality Preserved**:
- All subprocess calls identical (rpicam-hello, dmesg, v4l2-ctl)
- All error messages and details unchanged
- Same API response format (CameraHealthResponse)
- All timeouts and error handling preserved

**Quality Standards Met**:
- PEP 8 compliant
- Type hints on all functions
- Comprehensive docstrings
- Max complexity per function: 10 (all under target)
- Files compile without syntax errors

---

### [2025-12-23 19:45] Feature: Environment Overlay for Timelapse - Complete
**Type**: Feature
**Status**: COMPLETED

**Description**:
Added ability to stamp environmental sensor data (temperature, humidity, pressure) onto timelapse frames as they are captured.

**Features**:
- Optional environment device selection when starting timelapse
- Configurable overlay position (top-left, top-right, bottom-left, bottom-right)
- Optional mini temperature graph showing last 30 minutes of readings
- Sensor-specific data display (only shows what the sensor measures)
- Graph cached and regenerated every 10 frames for performance

**Files Created**:
- `backend/app/services/camera/overlay.py` - EnvironmentOverlayService using PIL/Pillow

**Files Modified**:
- `backend/app/services/camera/timelapse.py` - Integrated overlay into capture loop
- `backend/app/services/observation/service.py` - Pass overlay config to timelapse
- `backend/app/schemas/observation.py` - Added overlay fields to TimelapseObservationConfig
- `frontend/src/components/camera/StartObservationModal.tsx` - Added overlay UI

**Performance**:
- Overlay without graph: ~5ms per frame
- Overlay with graph: ~10ms per frame (graph cached)

---

### [2025-12-23 17:00] Feature: Touch-Friendly Observation Modal - Complete
**Type**: Feature
**Status**: COMPLETED

**Description**:
Redesigned the observation start modal to be fully touch-screen friendly with no keyboard input required.

**Features**:
- TouchNumberInput component with +/- stepper buttons
- TouchSelect component with segmented button style
- Preset buttons for common intervals (10s, 30s, 1m, 5m, 10m)
- Preset buttons for common durations (1h, 2h, 6h, 12h, 24h)

**Files Created**:
- `frontend/src/components/TouchNumberInput.tsx`
- `frontend/src/components/TouchNumberInput.css`
- `frontend/src/components/TouchSelect.tsx`
- `frontend/src/components/TouchSelect.css`

**Files Modified**:
- `frontend/src/components/camera/StartObservationModal.tsx`
- `frontend/src/components/camera/StartObservationModal.css`

---

### [2025-12-23 16:00] Feature: System Pressure Detection & Adaptive Throttling
**Type**: Feature
**Status**: COMPLETED

**Description**:
Added system health monitoring and adaptive throttling to prevent resource exhaustion on the Raspberry Pi.

**Features**:
- `check_system_pressure()` monitors memory/swap usage
- `get_adaptive_delay_seconds()` calculates recommended delays based on load
- Timelapse captures throttled when system is under pressure
- Reduced frontend polling intervals (3s→5s) with staleTime caching

**Files Modified**:
- `backend/app/services/system/stats.py` - Added pressure detection functions
- `backend/app/services/camera/timelapse.py` - Added adaptive throttling
- `frontend/src/pages/HomePage.tsx` - Reduced polling interval
- `frontend/src/components/SystemStats.tsx` - Reduced polling interval
- `frontend/src/pages/CameraPage.tsx` - Reduced polling interval
- `frontend/src/components/camera/ObservationInProgress.tsx` - Reduced polling interval
- `frontend/src/components/settings/CamerasPanel.tsx` - Reduced polling interval

---

### [2025-12-23 12:00] Feature: Environment Monitoring System - Complete
**Type**: Feature (Phase 1 Implementation)
**Status**: COMPLETED
**Plan**: phase1_temperature_monitoring.ready.md

**Description**:
Full implementation of environment sensor monitoring for DHT11/DHT22/AM2302/BME280 sensors.

**Features**:
- Environment device management (add/edit/delete sensors)
- Real-time sensor polling service with automatic retries
- Historical readings storage and retrieval
- Live dashboard with current readings and graphs
- Target value alerts (visual indicators when out of range)
- Temperature unit preference (Celsius/Fahrenheit) per device

**Files Created**:
- `backend/app/db/models/environment_device.py`
- `backend/app/db/models/environment_reading.py`
- `backend/app/db/repositories/environment_device.py`
- `backend/app/db/repositories/environment_reading.py`
- `backend/app/schemas/environment.py`
- `backend/app/api/routes/environment.py`
- `backend/app/services/environment/__init__.py`
- `backend/app/services/environment/polling.py`
- `backend/app/services/environment/sensors.py`
- `backend/app/db/migrations/versions/20241223_0005_add_environment_devices.py`
- `backend/app/db/migrations/versions/20241223_0006_add_environment_readings.py`
- `backend/app/db/migrations/versions/20241223_0007_add_temperature_unit.py`
- `backend/app/db/migrations/versions/20241223_0008_add_target_values.py`
- `frontend/src/pages/EnvironmentPage.tsx`
- `frontend/src/pages/EnvironmentPage.css`
- `frontend/src/components/environment/SensorCard.tsx`
- `frontend/src/components/environment/SensorCard.css`
- `frontend/src/components/environment/SensorGraph.tsx`
- `frontend/src/components/environment/SensorGraph.css`
- `frontend/src/components/environment/index.ts`
- `frontend/src/components/settings/EnvironmentPanel.tsx`
- `frontend/src/components/settings/EnvironmentPanel.css`

**Files Modified**:
- `backend/app/main.py` - Added environment polling startup
- `backend/app/api/routes/__init__.py` - Added environment router
- `backend/app/db/models/__init__.py` - Exported new models
- `backend/app/services/startup.py` - Start polling service
- `frontend/src/App.tsx` - Added Environment route
- `frontend/src/components/Layout.tsx` - Added Environment nav link
- `frontend/src/components/settings/index.ts` - Export EnvironmentPanel
- `scripts/install.sh` - Added adafruit-circuitpython-dht dependency

**Hardware Support**:
- DHT11 temperature/humidity sensor
- DHT22/AM2302 temperature/humidity sensor
- BME280 temperature/humidity/pressure sensor (via I2C)

---

### [2025-12-21 22:15] Feature: Persistent Camera Identification - Complete
**Type**: Feature
**Status**: COMPLETED

**Problem Solved**:
USB cameras can have different `/dev/videoN` paths after system reboots depending on USB enumeration order. This caused cameras to become misconfigured or unavailable after reboots.

**Solution Implemented**:
Added a `hardware_id` field that stores a stable identifier for each camera:
- **USB cameras**: Store the by-path symlink name (e.g., `platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.2.1:1.0-video-index0`)
- **CSI cameras**: Store `libcamera:N` which is already stable

On startup, the system resolves each `hardware_id` to the current `/dev/videoN` path and updates the database automatically.

**Files Created**:
- `backend/app/services/camera/resolver.py` - Resolves hardware_id to device_path
- `backend/app/db/migrations/versions/20241221_0003_add_camera_hardware_id.py` - Database migration

**Files Modified**:
- `backend/app/db/models/camera.py` - Added `hardware_id` field
- `backend/app/services/camera/discovery.py` - Captures hardware_id during discovery
- `backend/app/services/startup.py` - Added `reconcile_camera_device_paths()` function
- `backend/app/schemas/camera.py` - Added hardware_id to API schemas
- `backend/app/api/routes/cameras.py` - Updated create/discover endpoints
- `backend/app/db/repositories/camera.py` - Added `get_by_hardware_id()` and `update_device_path()`

**Verification**:
- Database migration ran successfully
- Startup reconciliation logs: `camera_reconciliation: {resolved: 2, updated: 0, unavailable: 0, legacy: 0}`
- All cameras working correctly

---

### [2025-12-21 21:30] Unplanned: SystemPage Hamburger Menu Fix
**Type**: Bug Fix
**Files Affected**:
- `frontend/src/pages/SystemPage.tsx`
- `frontend/src/pages/SystemPage.css`

**Reason**: User was trapped in hamburger menu on touchscreen - could not exit
**Impact**: Removed hamburger menu logic entirely, sidebar is now always visible on all screen sizes with responsive widths

---

### [2025-12-21 21:35] Unplanned: Nginx Cache Configuration
**Type**: Config
**Files Affected**: `/etc/nginx/sites-enabled/timemachine`

**Reason**: Browser caching old frontend assets after deployments
**Impact**:
- Added `location = /index.html` with no-cache headers
- Assets in `/assets/` cached for 1 year (they have content hashes)
- Future frontend deployments are immediately visible

---

### [2025-12-21 21:40] Created: Kiosk Refresh Script
**Type**: Feature
**Files Created**: `scripts/refresh-kiosk.sh`

**Reason**: Need easy way to refresh Chromium kiosk browser after deployments via SSH
**Usage**: `sudo ./scripts/refresh-kiosk.sh`

---

### [2025-12-21] Phase 0: Code Quality Remediation - Complete
**Plan**: phase0_code_quality.ready.md
**Status**: COMPLETED

**Issues Resolved**:
1. **Hardcoded localhost URLs** (AuthContext.tsx:27,61) - Changed to relative URLs for production compatibility
2. **Missing Error Boundary** (App.tsx) - Created ErrorBoundary component with fallback UI
3. **Magic numbers** - Created constants modules for both backend and frontend
4. **Duplicate utilities** - Created shared formatters.ts with formatDate, formatDuration, etc.
5. **Direct fetch() bypassing auth** - Updated FilesPage.tsx and FileBrowser.tsx to use apiClient

**Files Created**:
- `frontend/src/components/ErrorBoundary.tsx`
- `frontend/src/components/ErrorBoundary.css`
- `frontend/src/constants.ts`
- `frontend/src/utils/formatters.ts`
- `backend/app/core/constants.py`

**Files Modified**:
- `frontend/src/App.tsx` - Added ErrorBoundary wrapper
- `frontend/src/contexts/AuthContext.tsx` - Fixed hardcoded URLs
- `frontend/src/pages/FilesPage.tsx` - Use apiClient
- `frontend/src/components/storage/FileBrowser.tsx` - Use apiClient and formatters
- `frontend/src/components/jobs/JobCard.tsx` - Use shared formatters
- `backend/app/services/stats_broadcaster.py` - Use constants

**Deferred**:
- Refactoring cameras.py router (1287 lines) - Works correctly, refactoring deferred to avoid regressions

**Verification**:
- Frontend builds successfully (npm run build)
- Backend Python compiles without errors

**Next Steps**: Proceed to hardware testing

---

### [2025-12-21 00:00] Project Onboarded with Master Plan
**Command**: /new-project
**Project State**: Existing codebase (production-ready)
**Actions Taken**:
- Assessed project state: 7178 files, Python/React stack, production-ready
- Updated project-config.yaml with TimeMachine-specific settings
- Created Master Plan with 7 phases
- Created phase plan files for all phases

**Master Plan**: [plans/masterplan.md](plans/masterplan.md)

**Phases Created**:
| Phase | Plan File | Status |
|-------|-----------|--------|
| Phase 0: Code Quality | [phase0_code_quality.ready.md](plans/phase0_code_quality.ready.md) | Ready |
| Phase 1: Temp Monitoring | [phase1_temperature_monitoring.ready.md](plans/phase1_temperature_monitoring.ready.md) | Ready |
| Phase 2: Temp Control | [phase2_temperature_control.ready.md](plans/phase2_temperature_control.ready.md) | Ready |
| Phase 3: Retention | [phase3_retention_policies.ready.md](plans/phase3_retention_policies.ready.md) | Ready |
| Phase 4: Scheduling | [phase4_scheduling.ready.md](plans/phase4_scheduling.ready.md) | Ready |
| Phase 5: Notifications | [phase5_notifications.ready.md](plans/phase5_notifications.ready.md) | Ready |
| Phase 6: Hardware Test | [phase6_hardware_validation.ready.md](plans/phase6_hardware_validation.ready.md) | Ready |

**User Goals**:
- Add new features: Temperature control, retention policies, notifications, scheduling
- Fix existing HIGH priority code issues before new development
- Temperature hardware: DHT22/AM2302

**Recommended Next Steps**:
1. Start with Phase 0 to resolve code quality issues
2. Then proceed to Phase 1 (Temperature Monitoring)
3. Run `/start-work` to begin implementation

---

### [2025-12-25 17:00] Critical Security and Reliability Fixes
**Type**: Bug Fix / Security
**Status**: COMPLETED
**Triggered By**: AI Code Evaluation results

**Issues Fixed**:

1. **CRITICAL: Shell Command Injection (preview.py)**
   - Converted `create_subprocess_shell()` with f-strings to `create_subprocess_exec()` with argument lists
   - Prevents shell metacharacter exploitation in ffmpeg commands
   - Files: `backend/app/services/observation/preview.py`

2. **CRITICAL: Race Conditions (polling.py)**
   - Added `threading.Lock` for thread-safe singleton pattern with double-checked locking
   - Added `asyncio.Lock` for reader cache operations
   - Made `_get_reader()` and `invalidate_reader()` async with proper locking
   - Fixed race condition in `stop()` method - now holds lock during reader cleanup
   - Files: `backend/app/services/environment/polling.py`

3. **CRITICAL: Deprecated asyncio API (sensors.py)**
   - Replaced `asyncio.get_event_loop()` with `asyncio.get_running_loop()` in 3 locations
   - Files: `backend/app/services/environment/sensors.py`

4. **No Test Infrastructure**
   - Created pytest test infrastructure with conftest.py fixtures
   - Added tests for environment services and polling service
   - 18 tests passing
   - Files: `backend/tests/conftest.py`, `backend/tests/test_environment_services.py`, `backend/tests/test_polling_service.py`

**Quality Evaluation**:
- Ran quality evaluator agent after fixes
- Fixed 1 HIGH issue (global state pollution in tests)
- Fixed 2 MEDIUM issues (race condition in stop(), unused imports)
- All syntax verified, 18 tests passing

**Files Created**:
- `backend/tests/__init__.py`
- `backend/tests/conftest.py`
- `backend/tests/test_environment_services.py`
- `backend/tests/test_polling_service.py`
- `backend/requirements-test.txt`

**Files Modified**:
- `backend/app/services/observation/preview.py`
- `backend/app/services/environment/polling.py`
- `backend/app/services/environment/sensors.py`

---

### [Initial Setup] Project Initialized
**Type**: Setup
**Description**: Claude orchestration boilerplate created
**Components**:
- Core agents: feature-architect, root-cause-analyzer
- Embedded agents: embedded-developer, embedded-quality-evaluator
- Python agents: python-developer, python-quality-evaluator
- Web agents: web-developer, web-quality-evaluator
- Commands: start-work, pause-work, document, new-feature, fix-bug
- Configuration: project-config.yaml, CLAUDE.md

**Status**: Ready for customization

---

*This file is automatically updated by Claude. Manual edits are allowed for corrections.*

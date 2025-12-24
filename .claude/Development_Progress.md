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

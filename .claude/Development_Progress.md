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

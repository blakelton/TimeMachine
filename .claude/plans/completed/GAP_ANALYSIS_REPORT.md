# TimeMachine Development Plan - Gap Analysis Report

**Generated**: 2025-12-06
**Plans Analyzed**: 11 (00-master-plan through 10-temperature-stub)

---

## Executive Summary

The TimeMachine Observation Chamber development plan is comprehensive and well-structured. However, this analysis identifies **23 gaps** across 7 categories that should be addressed before or during implementation to ensure a robust, production-ready system.

| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| Security | 2 | 2 | 1 | - |
| Error Handling | 1 | 2 | 2 | - |
| Resource Constraints | 2 | 3 | 1 | - |
| Testing | - | 2 | 2 | 1 |
| Integration | 1 | 2 | 1 | - |
| Documentation | - | - | 2 | 1 |
| Missing Features | - | 1 | 2 | - |
| **Total** | **6** | **12** | **11** | **2** |

---

## 1. Security Gaps

### CRITICAL

#### 1.1 No Authentication/Authorization System
**Location**: All API endpoints (01-backend-foundation, all route files)
**Issue**: The entire API is unauthenticated. Any device on the network can:
- View camera feeds
- Start/stop recordings
- Modify system configuration
- Delete stored files

**Impact**: On a home network this may be acceptable, but if exposed or on a shared network, this is a serious vulnerability.

**Recommendation**:
- Add optional authentication (disabled by default for simplicity)
- Consider HTTP Basic Auth as minimum
- JWT tokens for API access if multi-user needed
- Add `TIMEMACHINE_AUTH_ENABLED` and `TIMEMACHINE_AUTH_PASSWORD` environment variables

#### 1.2 CORS Not Configured
**Location**: 01-backend-foundation
**Issue**: No CORS middleware configuration. The FastAPI app may reject requests from the frontend if served from a different origin during development.

**Recommendation**:
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.env == "development" else [settings.allowed_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### HIGH

#### 1.3 File Serving Path Traversal Risk
**Location**: 04-storage-output (storage service)
**Issue**: While `_validate_path()` exists, the file download endpoint in 08-camera-tabs uses URL-encoded paths:
```typescript
src={`/api/v1/storage/files/${encodeURIComponent(lastCapture.path)}`}
```
The corresponding API endpoint is not defined in any plan. If it passes the path directly to file read without validation, path traversal is possible.

**Recommendation**:
- Define explicit `/api/v1/storage/files/{file_id}` endpoint in 04-storage-output
- Use database IDs instead of file paths
- Or implement strict path validation on the endpoint

#### 1.4 Missing Rate Limiting
**Location**: 01-backend-foundation
**Issue**: No rate limiting on API endpoints. A client could flood:
- Capture endpoint (fill disk rapidly)
- Stats endpoint (CPU overhead)
- File listing endpoint (I/O stress)

**Recommendation**:
- Add `slowapi` or custom rate limiter
- Limit capture to 1/second
- Limit expensive endpoints appropriately

### MEDIUM

#### 1.5 Environment File Permissions
**Location**: 09-deployment-service
**Issue**: `timemachine.env` contains configuration but no secrets currently. If auth is added, secrets would be in this file with `640` permissions (readable by group).

**Recommendation**: Document that if secrets are added, permissions should be `600`.

---

## 2. Error Handling Gaps

### CRITICAL

#### 2.1 GStreamer Pipeline Crash Recovery
**Location**: 03-camera-system
**Issue**: GStreamer pipelines can crash due to:
- Camera disconnect
- Encoder overload
- Memory pressure
- I/O errors

The plan shows pipeline setup but no crash handling or recovery mechanism.

**Impact**: A crashed pipeline leaves the camera in an unusable state until service restart.

**Recommendation**:
- Add GStreamer bus message handler for ERROR/EOS
- Implement automatic pipeline restart with backoff
- Add health check that verifies pipeline state
- Emit WebSocket event on camera failure

### HIGH

#### 2.2 Concurrent Recording Limit Enforcement
**Location**: 03-camera-system
**Issue**: `MAX_CONCURRENT_RECORDINGS = 1` is defined, but the enforcement mechanism isn't detailed. What happens when:
- User tries to start second recording?
- Recording crashes but state isn't updated?

**Recommendation**:
- Return 409 Conflict with clear message when limit exceeded
- Add periodic state reconciliation (check if recording process actually running)
- Clean up orphaned recording state on startup

#### 2.3 Database Connection Pool Exhaustion
**Location**: 02-database-config
**Issue**: SQLite with async SQLAlchemy has connection pooling, but max pool size isn't specified. Under load (multiple WebSocket clients + API requests), pool could exhaust.

**Recommendation**:
```python
engine = create_async_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
)
```

### MEDIUM

#### 2.4 WebSocket Disconnect Handling
**Location**: 05-frontend-foundation, 06-home-dashboard
**Issue**: Frontend WebSocket has reconnection logic, but backend WebSocket handling isn't detailed. What happens to:
- Stats broadcast if no clients?
- Event queue if client disconnects mid-send?

**Recommendation**: Add backend WebSocket manager with:
- Client tracking
- Graceful disconnect handling
- Broadcast failure tolerance

#### 2.5 Timelapse Interruption Recovery
**Location**: 03-camera-system, 08-camera-tabs
**Issue**: If timelapse is interrupted (power loss, service restart), there's no mention of:
- Resuming timelapse
- Cleaning up partial timelapse
- Notifying user of interruption

**Recommendation**:
- Store timelapse state in database (not just memory)
- Add startup check for incomplete timelapses
- Option to resume or cleanup

---

## 3. Raspberry Pi Resource Constraint Gaps

### CRITICAL

#### 3.1 Memory Pressure Handling
**Location**: 03-camera-system, 06-home-dashboard
**Issue**: Pi 3 has only 1GB RAM. The plan doesn't address:
- Memory limits for GStreamer pipelines
- Chart.js with 60-point history (multiple charts)
- Multiple MJPEG streams buffering
- SQLAlchemy connection pool overhead

**Impact**: Under memory pressure, OOM killer may terminate the service.

**Recommendation**:
- Add memory monitoring in health endpoint
- Implement backpressure on MJPEG streams
- Reduce MAX_POINTS to 30 for charts
- Add systemd `MemoryMax=` limit with graceful degradation

#### 3.2 SD Card Write Amplification
**Location**: 02-database-config, 04-storage-output
**Issue**: SQLite with frequent writes (events table, job updates) on SD card causes:
- Write amplification from SQLite journaling
- SD card wear
- Potential database corruption on power loss

**Impact**: SD card failure is the #1 cause of Pi system death.

**Recommendation**:
- Configure SQLite with `PRAGMA journal_mode=WAL`
- Add `PRAGMA synchronous=NORMAL` (balance durability/performance)
- Consider moving database to RAM with periodic sync
- Or recommend USB storage for media + database

### HIGH

#### 3.3 H.264 Encoder Contention
**Location**: 03-camera-system
**Issue**: Pi 3 has single H.264 hardware encoder. Plan limits to 1 recording, but:
- What about preview streams using H.264?
- Timelapse output encoding?

**Recommendation**:
- Clarify: MJPEG for preview, H.264 only for recording
- Add encoder lock/semaphore
- Document clearly in troubleshooting

#### 3.4 CPU Throttling Detection
**Location**: 01-backend-foundation (stats endpoint)
**Issue**: Pi throttles CPU under thermal/voltage stress. The stats endpoint shows temperature but doesn't detect:
- `vcgencmd get_throttled` throttle flags
- Under-voltage conditions

**Recommendation**:
- Add throttle status to stats endpoint
- Warn user if under-voltage detected
- Consider reducing operations when throttled

#### 3.5 USB Bandwidth Limits
**Location**: 03-camera-system
**Issue**: Pi 3 shares USB 2.0 bus between:
- USB cameras
- USB storage (if used)
- Ethernet (Pi 3B is USB-based)

Multiple USB cameras + network traffic can exceed bus bandwidth.

**Recommendation**:
- Document max 1-2 USB cameras
- Recommend reducing resolution for USB cameras
- Warn if multiple USB cameras detected

### MEDIUM

#### 3.6 Disk Space Pre-flight Check
**Location**: 03-camera-system, 04-storage-output
**Issue**: Recording starts without checking if there's sufficient disk space. User could start 4K recording with 100MB free.

**Recommendation**:
- Check minimum 500MB free before recording
- Estimate recording duration based on bitrate and space
- Warn user if space low

---

## 4. Testing Gaps

### HIGH

#### 4.1 No End-to-End Test Plan
**Location**: All plans
**Issue**: Each plan has unit/integration tests, but no E2E test plan for:
- Full user workflow (add camera → preview → record → download)
- Multi-camera scenarios
- Failure recovery scenarios

**Recommendation**: Add E2E test plan using Playwright or Cypress for frontend + real API.

#### 4.2 No Load/Stress Testing
**Location**: All plans
**Issue**: Pi 3 resource limits require testing:
- Multiple concurrent stream viewers
- Long-running recording stability
- Memory leak detection

**Recommendation**: Add load test script using `locust` or similar.

### MEDIUM

#### 4.3 No Hardware-in-Loop Tests
**Location**: 03-camera-system
**Issue**: Camera tests mock camera access. No plan for testing on actual Pi with cameras.

**Recommendation**: Add CI step on physical Pi or document manual test procedure.

#### 4.4 Missing Frontend Tests
**Location**: 05-frontend-foundation, 06-home-dashboard, 08-camera-tabs
**Issue**: Test tables show unit tests but no actual test file examples. React Testing Library setup not shown.

**Recommendation**: Add example test files and testing setup to frontend foundation plan.

### LOW

#### 4.5 No Performance Benchmarks
**Location**: Master plan
**Issue**: No baseline performance metrics defined. How do we know if implementation meets targets?

**Recommendation**: Define benchmarks:
- API response time < 100ms
- Stream latency < 500ms
- Recording start time < 2s

---

## 5. Integration Gaps

### CRITICAL

#### 5.1 Frontend/Backend API Contract Missing
**Location**: 05-frontend-foundation, all backend routes
**Issue**: Frontend hooks assume API response shapes, but no shared contract (OpenAPI spec, TypeScript types from backend).

**Impact**: Frontend/backend mismatch is common cause of bugs.

**Recommendation**:
- Generate OpenAPI spec from FastAPI
- Generate TypeScript types from OpenAPI
- Or define shared API types document

### HIGH

#### 5.2 WebSocket Message Format Undefined
**Location**: 05-frontend-foundation, 06-home-dashboard
**Issue**: WebSocket is used for stats updates, but message format isn't defined:
- Message types?
- Payload structure?
- Error messages?

**Recommendation**: Define WebSocket protocol:
```typescript
type WSMessage =
  | { type: 'stats_update', data: StatsPayload }
  | { type: 'camera_event', data: CameraEventPayload }
  | { type: 'job_update', data: JobPayload }
  | { type: 'error', message: string }
```

#### 5.3 Camera Status Synchronization
**Location**: 03-camera-system, 06-home-dashboard, 08-camera-tabs
**Issue**: Camera status (online/offline/recording) shown in multiple places:
- Dashboard cards
- Navigation tabs
- Camera view

No clear mechanism for keeping these synchronized when status changes.

**Recommendation**:
- Use WebSocket events for status changes
- React Query invalidation on events
- Or polling with short interval

### MEDIUM

#### 5.4 Job System Integration
**Location**: 02-database-config, 03-camera-system
**Issue**: Jobs table exists but no clear integration with:
- Recording service
- Timelapse service
- Observation summary component

**Recommendation**: Add job lifecycle management:
- Create job when recording/timelapse starts
- Update job status on progress
- Mark complete/failed on finish

---

## 6. Documentation Gaps

### MEDIUM

#### 6.1 User Documentation Missing
**Location**: Master plan
**Issue**: Technical plans are detailed, but no user-facing documentation:
- How to add a camera
- How to configure storage
- Troubleshooting common issues

**Recommendation**: Add plan for user documentation or include in frontend.

#### 6.2 API Documentation
**Location**: 01-backend-foundation
**Issue**: FastAPI auto-generates docs, but:
- No mention of `/docs` or `/redoc` endpoints
- No customization for better descriptions

**Recommendation**: Enable and customize OpenAPI docs.

### LOW

#### 6.3 Architecture Decision Records
**Location**: Master plan
**Issue**: Technology choices are stated but not justified:
- Why SQLite over PostgreSQL?
- Why TanStack Query over SWR?
- Why GStreamer over picamera2 native?

**Recommendation**: Add ADR section to master plan.

---

## 7. Missing Features

### HIGH

#### 7.1 No Notification System
**Location**: All plans
**Issue**: No way to notify user of:
- Recording complete
- Disk space low
- Camera offline
- Timelapse complete

**Recommendation**: Add notification system:
- Browser notifications (Push API)
- Or email notifications
- Or webhook for home automation

### MEDIUM

#### 7.2 No File Download/Management UI
**Location**: 06-home-dashboard, 08-camera-tabs
**Issue**: Files can be captured/recorded, but no comprehensive file browser:
- View all recordings
- Delete old files
- Download multiple files
- Preview recordings

Observation summary shows recent files but limited functionality.

**Recommendation**: Add dedicated "Library" or "Files" tab with full file management.

#### 7.3 No Camera Settings Persistence
**Location**: 03-camera-system, 08-camera-tabs
**Issue**: Camera settings (bitrate, quality) are set per-session. No persistence of:
- Preferred recording bitrate per camera
- Default capture quality
- Stream settings

**Recommendation**: Add camera_settings JSON column or separate table for per-camera preferences.

---

## Recommendations Summary

### Before Implementation Starts
1. **Define API contract** - Create OpenAPI spec or shared types
2. **Add authentication option** - Even if disabled by default
3. **Configure CORS** - Required for dev workflow
4. **Define WebSocket protocol** - Message types and payloads

### During Implementation (High Priority)
5. **Add GStreamer crash recovery** - Pipeline restart logic
6. **Add memory monitoring** - Prevent OOM on Pi 3
7. **Configure SQLite for SD card** - WAL mode, proper sync
8. **Add disk space checks** - Before starting recordings
9. **Add rate limiting** - Protect against abuse
10. **Create file download endpoint** - Secure file serving

### Before Production
11. **Add E2E tests** - Full workflow testing
12. **Load test on Pi 3** - Verify resource limits
13. **Create user documentation** - Setup and usage guide
14. **Add notification system** - User feedback for long operations

### Future Enhancements
15. **File browser UI** - Full media management
16. **Camera settings persistence** - Per-camera preferences
17. **Architecture decision records** - Document technical choices

---

## Conclusion

The TimeMachine development plan provides a solid foundation with well-organized phases and clear acceptance criteria. The identified gaps are typical for an initial plan and addressing them will result in a robust, production-ready system.

**Key Strengths**:
- Clear separation of concerns
- Async-first backend design
- Proper abstraction layers (camera abstraction, repository pattern)
- Security considerations in storage service
- Good error states in frontend components

**Areas Needing Most Attention**:
- Pi 3 resource constraints (memory, SD card wear, encoder limits)
- Security (authentication, CORS, rate limiting)
- Integration (API contract, WebSocket protocol, status sync)
- Error recovery (GStreamer crashes, interrupted operations)

Addressing the 6 CRITICAL and 12 HIGH priority gaps before or during implementation will significantly reduce risk of production issues.

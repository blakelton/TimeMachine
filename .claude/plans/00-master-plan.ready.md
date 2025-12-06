# TimeMachine Observation Chamber - Master Plan

## Executive Summary

This master plan governs the development of a temperature-controlled observation chamber management system hosted on Raspberry Pi 3+. The system provides web-based control for camera management (CSI and USB), recording, timelapse creation, and future temperature control capabilities.

**Target Platform**: Raspberry Pi 3+ running Pi OS with Python 3.11
**Architecture**: FastAPI backend + React/TypeScript frontend
**Key Constraint**: Resource efficiency on limited Pi 3 hardware (1GB RAM, quad-core ARM)

---

## High-Level Architecture

```
+------------------------------------------------------------------+
|                         CLIENT LAYER                              |
|  +------------------------------------------------------------+  |
|  |              React + Vite + TypeScript Frontend             |  |
|  |  +--------+  +--------+  +--------+  +------------------+  |  |
|  |  |  Home  |  | System |  | Cam 1  |  | Cam N (dynamic)  |  |  |
|  |  |  Tab   |  |  Tab   |  |  Tab   |  |      Tabs        |  |  |
|  |  +--------+  +--------+  +--------+  +------------------+  |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
                              |
                              | HTTP/REST + WebSocket
                              v
+------------------------------------------------------------------+
|                        API GATEWAY                                |
|  +------------------------------------------------------------+  |
|  |                    nginx (reverse proxy)                    |  |
|  |              HTTPS termination, static files               |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
                              |
                              | HTTP (localhost:8000)
                              v
+------------------------------------------------------------------+
|                      APPLICATION LAYER                            |
|  +------------------------------------------------------------+  |
|  |              FastAPI + Uvicorn (async)                      |  |
|  |                                                              |  |
|  |  +------------------+  +------------------+                 |  |
|  |  |   REST Routers   |  | WebSocket Hub    |                 |  |
|  |  |  /health /stats  |  | /ws/stats        |                 |  |
|  |  |  /cameras        |  | /ws/events       |                 |  |
|  |  |  /outputs        |  |                  |                 |  |
|  |  |  /temperature    |  |                  |                 |  |
|  |  +------------------+  +------------------+                 |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|  +------------------------------------------------------------+  |
|  |                    SERVICE LAYER                            |  |
|  |                                                              |  |
|  |  +----------------+  +----------------+  +----------------+ |  |
|  |  | Camera Service |  | Storage Service|  | Config Service | |  |
|  |  | - Discovery    |  | - File Mgmt    |  | - Settings     | |  |
|  |  | - Pipelines    |  | - Retention    |  | - Validation   | |  |
|  |  | - Capture      |  | - NAS Support  |  | - Persistence  | |  |
|  |  +----------------+  +----------------+  +----------------+ |  |
|  |                                                              |  |
|  |  +----------------+  +----------------+                     |  |
|  |  | Stats Service  |  | Temp Service   |                     |  |
|  |  | - CPU/RAM/Disk |  | - (Stub)       |                     |  |
|  |  | - Monitoring   |  | - GPIO Ready   |                     |  |
|  |  +----------------+  +----------------+                     |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                       DATA LAYER                                  |
|  +--------------------+  +------------------------------------+  |
|  |      SQLite        |  |           Filesystem               |  |
|  |  - Cameras config  |  |  - /recordings/*.mp4               |  |
|  |  - Output settings |  |  - /stills/*.jpg                   |  |
|  |  - Job metadata    |  |  - /timelapse/*.mp4                |  |
|  |  - Event log       |  |  - /logs/*.log                     |  |
|  +--------------------+  +------------------------------------+  |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                     HARDWARE LAYER                                |
|  +--------------------+  +--------------------+                   |
|  |   CSI Camera(s)    |  |   USB UVC Cameras  |                   |
|  |   via libcamera    |  |   via V4L2         |                   |
|  |   picamera2        |  |   /dev/video*      |                   |
|  +--------------------+  +--------------------+                   |
|                                                                   |
|  +--------------------+  +--------------------+                   |
|  |   H.264 Encoder    |  |   GPIO (Future)    |                   |
|  |   v4l2h264enc      |  |   Temperature Ctrl |                   |
|  +--------------------+  +--------------------+                   |
+------------------------------------------------------------------+
```

---

## Technology Stack

### Backend Stack

| Component | Technology | Version | Rationale |
|-----------|------------|---------|-----------|
| Runtime | Python | 3.11 | Pi OS default, good async support, type hints |
| Web Framework | FastAPI | 0.104+ | Async-first, auto OpenAPI docs, Pydantic integration |
| ASGI Server | Uvicorn | 0.24+ | Production-ready, good performance on Pi |
| Camera (CSI) | picamera2 | 0.3+ | Official libcamera Python bindings |
| Camera (USB) | v4l2/GStreamer | System | Direct V4L2 access for UVC cameras |
| Video Pipeline | GStreamer | 1.22+ | Hardware encoder access, pipeline flexibility |
| H.264 Encoder | v4l2h264enc | System | Pi hardware encoder, essential for performance |
| Database | SQLite | 3.40+ | Zero-config, sufficient for config/metadata |
| ORM | SQLAlchemy | 2.0+ | Async support, migrations via Alembic |
| Validation | Pydantic | 2.0+ | Settings management, request/response models |
| Task Scheduling | APScheduler | 3.10+ | Timelapse scheduling, retention jobs |
| Rate Limiting | slowapi | 0.1+ | API abuse protection |

### Frontend Stack

| Component | Technology | Version | Rationale |
|-----------|------------|---------|-----------|
| Framework | React | 18+ | Component model, hooks, concurrent features |
| Build Tool | Vite | 5+ | Fast HMR, optimized builds, TypeScript support |
| Language | TypeScript | 5+ | Type safety, better IDE support |
| Styling | CSS Modules or Tailwind | Latest | Scoped styles / utility-first (team choice) |
| State | TanStack Query | 5+ | Server state management, caching, sync |
| HTTP Client | fetch + custom wrapper | Native | Minimal dependencies |
| Charts | Chart.js or Recharts | Latest | Lightweight, lazy-loaded |
| Video | HLS.js (optional) | Latest | HLS playback fallback |
| E2E Testing | Playwright | Latest | Cross-browser E2E tests |

### Infrastructure

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Process Manager | systemd | Pi OS standard, restart policies, journald |
| Reverse Proxy | nginx | HTTPS termination, static serving, optional HLS |
| Logging | structlog + journald | Structured logs, system integration |
| Load Testing | locust | Performance validation on Pi |

---

## Sub-Plan Registry

The following sub-plans will be created to implement this system. Each sub-plan is a self-contained implementation unit with clear inputs, outputs, and acceptance criteria.

### Plan Dependency Graph (Updated with Gap Remediation)

```
                         00-master-plan
                               |
                               v
                    +---------------------+
                    | GAP REMEDIATION     |
                    | (Integrated Below)  |
                    +---------------------+
                               |
            +------------------+------------------+
            |                  |                  |
            v                  v                  v
     01-backend          02-database        05-frontend
     foundation          config             foundation
     + CORS              + SQLite WAL       + API Types
     + Rate Limiting     + Schema fixes     + WS Protocol
     + Auth (optional)                      + Auth UI
            |                  |                  |
            +--------+---------+                  |
                     |                            |
                     v                            v
               03-camera                   06-home-dashboard
               system                      + Status Sync
               + Pipeline Recovery         + Notifications
               + Encoder Management
               + Memory Checks
                     |                            |
                     v                            v
               04-storage                  07-system-settings
               output
               + Disk Checks
               + Secure File Serving
                     |                            |
                     +--------+---------+---------+
                              |
                              v
                       08-camera-tabs
                       + Job Integration
                              |
                              v
                       09-deployment
                       service
                       + Load Testing
                       + Documentation
                              |
                              v
                       10-temperature
                       stub
```

### Sub-Plan Descriptions

| Plan File | Title | Description | Dependencies | Gap Integrations |
|-----------|-------|-------------|--------------|------------------|
| `01-backend-foundation.ready.md` | Backend Foundation | FastAPI app scaffold, project structure, health/stats endpoints, logging setup | None | CORS, Rate Limiting, Optional Auth, Throttle Detection |
| `02-database-config.ready.md` | Database & Config | SQLite schema design, async SQLAlchemy, Pydantic settings, camera/output CRUD models | 01 | SQLite WAL mode, Connection pool config |
| `03-camera-system.ready.md` | Camera System | Device discovery (CSI/USB), GStreamer pipelines, preview/capture/record/stream services | 01, 02 | Pipeline crash recovery, Encoder semaphore, Memory checks |
| `04-storage-output.ready.md` | Storage & Output | File management, path configuration, retention policies, NAS path support | 01, 02 | Disk space pre-checks, Secure file serving endpoint |
| `05-frontend-foundation.ready.md` | Frontend Foundation | Vite/React/TS scaffold, routing, responsive shell, API client, WebSocket helper | None | API type generation, WebSocket protocol types, Auth UI |
| `06-home-dashboard.ready.md` | Home Dashboard | Home tab with observation list, camera status cards, system stats graphs | 05, 01 | Camera status sync via WebSocket, Notification system |
| `07-system-settings.ready.md` | System Settings | System tab with left panel menu, Cameras/Output/Temperature config panels | 05, 02, 03, 04 | Notification settings panel |
| `08-camera-tabs.ready.md` | Camera Tabs | Dynamic per-camera tabs, live preview, capture/record/timelapse controls | 05, 03 | Job system integration, Timelapse interruption recovery |
| `09-deployment-service.ready.md` | Deployment & Service | systemd unit files, environment config, nginx config | 01-04 | Memory limits, Load testing, User documentation |
| `10-temperature-stub.ready.md` | Temperature Stub | Placeholder backend endpoint and UI panel | 02, 05 | None (stub only) |

---

## Implementation Order (With Gap Remediation Integrated)

### Phase 1: Foundation (Days 1-3)

**Backend Track** (Plans 01, 02):

| Step | Task | Source | Priority |
|------|------|--------|----------|
| 1.1 | FastAPI app scaffold with project structure | 01-backend | Core |
| 1.2 | **CORS middleware configuration** | Gap 1.2 | CRITICAL |
| 1.3 | Health and stats endpoints | 01-backend | Core |
| 1.4 | **Throttle detection (vcgencmd)** | Gap 3.4 | HIGH |
| 1.5 | **Rate limiting with slowapi** | Gap 2.2 | HIGH |
| 1.6 | **Optional HTTP Basic Auth** | Gap 2.1 | CRITICAL |
| 1.7 | Structured logging setup | 01-backend | Core |
| 1.8 | SQLite database setup | 02-database | Core |
| 1.9 | **SQLite WAL mode + optimized pragmas** | Gap 1.3 | CRITICAL |
| 1.10 | SQLAlchemy async models | 02-database | Core |
| 1.11 | **Connection pool configuration** | Gap 2.3 | HIGH |
| 1.12 | Pydantic settings management | 02-database | Core |
| 1.13 | Camera/Output CRUD repositories | 02-database | Core |

**Frontend Track** (Plan 05):

| Step | Task | Source | Priority |
|------|------|--------|----------|
| 1.14 | Vite + React + TypeScript scaffold | 05-frontend | Core |
| 1.15 | **OpenAPI TypeScript type generation** | Gap 5.1 | CRITICAL |
| 1.16 | API client with typed responses | 05-frontend | Core |
| 1.17 | **WebSocket protocol types** | Gap 1.4 | HIGH |
| 1.18 | WebSocket client with typed handlers | 05-frontend | Core |
| 1.19 | **Auth UI (login modal)** | Gap 2.1 | CRITICAL |
| 1.20 | Responsive navigation shell | 05-frontend | Core |
| 1.21 | TanStack Query setup | 05-frontend | Core |

**Gate Criteria**:
- Backend serves `/health` and `/stats` with throttle info
- CORS allows frontend requests
- Rate limiting active on endpoints
- SQLite using WAL mode
- Frontend renders navigation shell
- TypeScript types generated from OpenAPI
- WebSocket client uses typed messages
- Optional auth works when enabled

---

### Phase 2: Core Systems (Days 4-7)

**Camera System** (Plan 03):

| Step | Task | Source | Priority |
|------|------|--------|----------|
| 2.1 | Camera device discovery (CSI/USB) | 03-camera | Core |
| 2.2 | Camera capability detection | 03-camera | Core |
| 2.3 | GStreamer pipeline abstraction | 03-camera | Core |
| 2.4 | **ManagedPipeline with crash recovery** | Gap 4.1 | CRITICAL |
| 2.5 | **Encoder semaphore (single H.264)** | Gap 3.3 | HIGH |
| 2.6 | **Memory check before operations** | Gap 3.1 | CRITICAL |
| 2.7 | Preview service (MJPEG) | 03-camera | Core |
| 2.8 | Capture service (stills) | 03-camera | Core |
| 2.9 | **Recording state manager with PID tracking** | Gap 4.2 | HIGH |
| 2.10 | Recording service (H.264) | 03-camera | Core |
| 2.11 | **Timelapse state persistence in DB** | Gap 4.3 | HIGH |
| 2.12 | Timelapse service | 03-camera | Core |
| 2.13 | **Camera status event emission** | Gap 5.1 | HIGH |
| 2.14 | Camera REST API endpoints | 03-camera | Core |

**Storage System** (Plan 04):

| Step | Task | Source | Priority |
|------|------|--------|----------|
| 2.15 | Storage path configuration | 04-storage | Core |
| 2.16 | **Disk space pre-flight checks** | Gap 3.2 | HIGH |
| 2.17 | File organizer (naming conventions) | 04-storage | Core |
| 2.18 | **Secure file serving endpoint** | Gap 2.3 | HIGH |
| 2.19 | Retention manager (age/size policies) | 04-storage | Core |
| 2.20 | Storage REST API endpoints | 04-storage | Core |

**Gate Criteria**:
- Camera discovery finds CSI and USB devices
- GStreamer pipelines auto-recover from crashes
- Encoder contention prevented (only one H.264 at a time)
- Memory checked before starting preview/recording
- Recording state tracked with PIDs, orphans cleaned on startup
- Can capture stills, record video, start timelapse
- Disk space checked before recording
- Files served securely without path traversal
- Camera status changes emit WebSocket events

---

### Phase 3: UI Integration (Days 8-11)

**WebSocket Manager** (Gap 4.4 - Required for status sync):

| Step | Task | Source | Priority |
|------|------|--------|----------|
| 3.1 | **Backend WebSocket connection manager** | Gap 4.4 | MEDIUM |
| 3.2 | **Stats broadcast loop** | Gap 4.4 | MEDIUM |

**Home Dashboard** (Plan 06):

| Step | Task | Source | Priority |
|------|------|--------|----------|
| 3.3 | Dashboard responsive layout | 06-dashboard | Core |
| 3.4 | Camera status cards | 06-dashboard | Core |
| 3.5 | **Camera status sync via WebSocket** | Gap 5.1 | HIGH |
| 3.6 | System stats graphs (CPU/RAM/Disk) | 06-dashboard | Core |
| 3.7 | **Throttle warning banner** | Gap 3.4 | HIGH |
| 3.8 | **Memory warning banner** | Gap 3.1 | HIGH |
| 3.9 | Observation summary (active jobs) | 06-dashboard | Core |
| 3.10 | **Browser notification service** | Gap 5.3 | HIGH |
| 3.11 | **Notification event handlers** | Gap 5.3 | HIGH |

**System Settings** (Plan 07):

| Step | Task | Source | Priority |
|------|------|--------|----------|
| 3.12 | Settings layout with sidebar | 07-settings | Core |
| 3.13 | Cameras CRUD panel | 07-settings | Core |
| 3.14 | Output configuration panel | 07-settings | Core |
| 3.15 | **Notification settings panel** | Gap 5.3 | MEDIUM |
| 3.16 | Temperature stub panel | 07-settings | Core |

**Camera Tabs** (Plan 08):

| Step | Task | Source | Priority |
|------|------|--------|----------|
| 3.17 | Dynamic camera navigation | 08-camera-tabs | Core |
| 3.18 | Camera view layout | 08-camera-tabs | Core |
| 3.19 | Live preview component | 08-camera-tabs | Core |
| 3.20 | Capture tab with quality settings | 08-camera-tabs | Core |
| 3.21 | Record tab with bitrate settings | 08-camera-tabs | Core |
| 3.22 | **Disk space warning in record UI** | Gap 3.2 | HIGH |
| 3.23 | Timelapse tab | 08-camera-tabs | Core |
| 3.24 | **Timelapse resume/cleanup UI** | Gap 4.3 | HIGH |
| 3.25 | **Job integration (create/update jobs)** | Gap 5.2 | HIGH |
| 3.26 | Toast notifications | 08-camera-tabs | Core |

**Gate Criteria**:
- Dashboard shows real-time camera status via WebSocket
- System warnings (throttle, memory, disk) displayed prominently
- Browser notifications for recording/timelapse complete
- Camera settings CRUD fully functional
- Notification preferences configurable
- Recording shows disk space warnings
- Interrupted timelapses can be resumed or cleaned up
- Jobs tracked in database and shown in UI

---

### Phase 4: Production Readiness (Days 12-15)

**Deployment** (Plan 09):

| Step | Task | Source | Priority |
|------|------|--------|----------|
| 4.1 | systemd service file | 09-deployment | Core |
| 4.2 | **Memory limits in systemd (MemoryMax)** | Gap 3.1 | CRITICAL |
| 4.3 | Environment configuration | 09-deployment | Core |
| 4.4 | **Secure env file permissions** | Gap 2.4 | MEDIUM |
| 4.5 | Installation script | 09-deployment | Core |
| 4.6 | nginx reverse proxy config | 09-deployment | Core |
| 4.7 | Operational scripts (start/stop/logs) | 09-deployment | Core |
| 4.8 | udev rules for cameras | 09-deployment | Core |
| 4.9 | Health check with watchdog | 09-deployment | Core |

**Testing** (Gaps 4.1, 4.2):

| Step | Task | Source | Priority |
|------|------|--------|----------|
| 4.10 | **Playwright E2E test setup** | Gap 6.1 | HIGH |
| 4.11 | **E2E tests for critical flows** | Gap 6.1 | HIGH |
| 4.12 | **Locust load test setup** | Gap 6.2 | HIGH |
| 4.13 | **Load test on Pi hardware** | Gap 6.2 | HIGH |

**Documentation** (Gaps 6.1, 6.2):

| Step | Task | Source | Priority |
|------|------|--------|----------|
| 4.14 | **User getting started guide** | Gap 6.3 | MEDIUM |
| 4.15 | **Configuration documentation** | Gap 6.3 | MEDIUM |
| 4.16 | **Troubleshooting guide** | Gap 6.3 | MEDIUM |
| 4.17 | **API documentation enhancement** | Gap 6.4 | MEDIUM |

**Temperature Stub** (Plan 10):

| Step | Task | Source | Priority |
|------|------|--------|----------|
| 4.18 | Temperature API stub endpoints | 10-temperature | Core |
| 4.19 | Temperature schemas | 10-temperature | Core |
| 4.20 | Temperature service interface | 10-temperature | Core |

**Gate Criteria**:
- Service runs on Pi via systemd with memory limits
- systemd restarts on failure
- nginx proxies API and WebSocket correctly
- E2E tests pass for critical flows
- Load tests validate Pi can handle expected load
- User documentation complete
- Temperature stub visible in UI

---

## Total Estimated Duration: 13-17 days

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Phase 1: Foundation | 3 days | Backend + Frontend scaffolds with security |
| Phase 2: Core Systems | 4 days | Camera + Storage with reliability features |
| Phase 3: UI Integration | 4 days | Full UI with notifications + job tracking |
| Phase 4: Production | 4 days | Deployment + Testing + Documentation |

---

## Gap Remediation Summary

All 23 gaps from the Gap Analysis Report are now integrated into the implementation plan:

### Critical Gaps (6) - Integration Points

| Gap | Description | Integrated Into |
|-----|-------------|-----------------|
| 1.1 | No Authentication | Phase 1 (01-backend) |
| 1.2 | CORS Not Configured | Phase 1 (01-backend) |
| 2.1 | GStreamer Crash Recovery | Phase 2 (03-camera) |
| 3.1 | Memory Pressure Handling | Phase 2 (03-camera), Phase 4 (09-deploy) |
| 3.2 | SD Card Write Amplification | Phase 1 (02-database) |
| 5.1 | API Contract Missing | Phase 1 (05-frontend) |

### High Priority Gaps (12) - Integration Points

| Gap | Description | Integrated Into |
|-----|-------------|-----------------|
| 1.3 | File Serving Path Traversal | Phase 2 (04-storage) |
| 1.4 | Rate Limiting Missing | Phase 1 (01-backend) |
| 2.2 | Concurrent Recording Enforcement | Phase 2 (03-camera) |
| 2.3 | Connection Pool Config | Phase 1 (02-database) |
| 3.3 | H.264 Encoder Contention | Phase 2 (03-camera) |
| 3.4 | Throttle Detection | Phase 1 (01-backend) |
| 3.6 | Disk Space Pre-flight | Phase 2 (04-storage) |
| 4.1 | E2E Test Framework | Phase 4 (09-deploy) |
| 4.2 | Load Testing | Phase 4 (09-deploy) |
| 5.2 | WebSocket Protocol | Phase 1 (05-frontend) |
| 5.3 | Camera Status Sync | Phase 3 (06-dashboard) |
| 5.4 | Job System Integration | Phase 3 (08-camera-tabs) |
| 7.1 | Notification System | Phase 3 (06-dashboard) |

### Medium Priority Gaps (5) - Integration Points

| Gap | Description | Integrated Into |
|-----|-------------|-----------------|
| 1.5 | Environment Security | Phase 4 (09-deploy) |
| 2.4 | WebSocket Error Handling | Phase 3 (pre-dashboard) |
| 2.5 | Timelapse Recovery | Phase 2 (03-camera), Phase 3 (08-tabs) |
| 6.1 | User Documentation | Phase 4 (09-deploy) |
| 6.2 | API Documentation | Phase 4 (09-deploy) |

---

## Shared Conventions

### Project Structure

```
TimeMachine/
+-- backend/
|   +-- app/
|   |   +-- __init__.py
|   |   +-- main.py              # FastAPI app factory
|   |   +-- config.py            # Pydantic settings
|   |   +-- api/
|   |   |   +-- __init__.py
|   |   |   +-- routes/
|   |   |   |   +-- health.py
|   |   |   |   +-- stats.py
|   |   |   |   +-- cameras.py
|   |   |   |   +-- outputs.py
|   |   |   |   +-- temperature.py
|   |   |   |   +-- jobs.py         # NEW: Job management
|   |   |   +-- websocket/
|   |   |       +-- hub.py
|   |   |       +-- manager.py      # NEW: Connection manager
|   |   +-- core/
|   |   |   +-- logging.py
|   |   |   +-- exceptions.py
|   |   |   +-- dependencies.py
|   |   |   +-- security.py         # NEW: Auth module
|   |   |   +-- rate_limit.py       # NEW: Rate limiting
|   |   +-- models/
|   |   |   +-- database.py      # SQLAlchemy models
|   |   |   +-- schemas.py       # Pydantic schemas
|   |   +-- services/
|   |   |   +-- camera/
|   |   |   |   +-- discovery.py
|   |   |   |   +-- pipeline.py     # NEW: ManagedPipeline
|   |   |   |   +-- encoder.py      # NEW: Encoder semaphore
|   |   |   |   +-- capture.py
|   |   |   |   +-- recording.py
|   |   |   |   +-- recording_state.py  # NEW: State manager
|   |   |   |   +-- timelapse.py
|   |   |   |   +-- timelapse_recovery.py  # NEW: Recovery
|   |   |   +-- storage/
|   |   |   |   +-- manager.py
|   |   |   |   +-- retention.py
|   |   |   |   +-- checks.py       # NEW: Disk space checks
|   |   |   +-- jobs/
|   |   |   |   +-- service.py      # NEW: Job lifecycle
|   |   |   +-- system/
|   |   |   |   +-- throttle.py     # NEW: Throttle detection
|   |   |   +-- stats.py
|   |   +-- db/
|   |       +-- session.py
|   |       +-- migrations/
|   +-- tests/
|   |   +-- unit/
|   |   +-- integration/
|   |   +-- load/                   # NEW: Locust tests
|   |       +-- locustfile.py
|   +-- alembic.ini
|   +-- requirements.txt
|   +-- requirements-dev.txt
|   +-- Makefile
|   +-- .env.example
+-- frontend/
|   +-- src/
|   |   +-- main.tsx
|   |   +-- App.tsx
|   |   +-- api/
|   |   |   +-- client.ts
|   |   |   +-- websocket.ts
|   |   |   +-- websocket.types.ts  # NEW: WS protocol types
|   |   |   +-- types.generated.ts  # NEW: Generated from OpenAPI
|   |   +-- components/
|   |   |   +-- layout/
|   |   |   +-- common/
|   |   |   +-- auth/               # NEW: Login modal
|   |   +-- pages/
|   |   |   +-- Home/
|   |   |   +-- System/
|   |   |   +-- Camera/
|   |   +-- hooks/
|   |   |   +-- useCameraStatus.ts  # NEW: Status sync
|   |   |   +-- useNotifications.ts # NEW: Browser notifications
|   |   +-- services/
|   |   |   +-- notifications.ts    # NEW: Notification service
|   |   +-- types/
|   |   +-- utils/
|   +-- e2e/                        # NEW: Playwright tests
|   |   +-- home.spec.ts
|   |   +-- camera.spec.ts
|   +-- public/
|   +-- index.html
|   +-- vite.config.ts
|   +-- playwright.config.ts        # NEW: E2E config
|   +-- tsconfig.json
|   +-- package.json
+-- deploy/
|   +-- timemachine.service
|   +-- timemachine.env
|   +-- nginx.conf
+-- scripts/
|   +-- smoke-test.sh
|   +-- install.sh
|   +-- load-test.sh               # NEW: Load testing
|   +-- export_openapi.py          # NEW: Type generation
+-- docs/                          # NEW: User documentation
|   +-- getting-started.md
|   +-- configuration.md
|   +-- troubleshooting.md
+-- .claude/
```

### Naming Conventions

#### Python (Backend)

- **Files**: `snake_case.py` (e.g., `camera_service.py`)
- **Classes**: `PascalCase` (e.g., `CameraService`, `CameraConfig`)
- **Functions/Methods**: `snake_case` (e.g., `get_camera_status`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_FPS`)
- **Type Aliases**: `PascalCase` (e.g., `CameraId = str`)

#### TypeScript (Frontend)

- **Files**: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- **Components**: `PascalCase` (e.g., `CameraCard`, `SystemSettings`)
- **Functions/Hooks**: `camelCase` (e.g., `useCameraStatus`, `fetchStats`)
- **Types/Interfaces**: `PascalCase` (e.g., `CameraConfig`, `StatsResponse`)
- **Constants**: `UPPER_SNAKE_CASE` or `camelCase` for module-scope

#### API Endpoints

- **REST**: Plural nouns, lowercase with hyphens (e.g., `/api/v1/cameras`, `/api/v1/camera-status`)
- **WebSocket**: Namespaced paths (e.g., `/ws/stats`, `/ws/events`)
- **Versioning**: `/api/v1/` prefix for REST endpoints

#### Database

- **Tables**: `snake_case`, plural (e.g., `cameras`, `output_configs`)
- **Columns**: `snake_case` (e.g., `device_path`, `created_at`)
- **Foreign Keys**: `<table>_id` (e.g., `camera_id`)

### API Patterns

#### REST Response Structure

```python
# Success response
{
    "data": { ... },
    "meta": {
        "timestamp": "2024-01-15T10:30:00Z",
        "request_id": "uuid"
    }
}

# Error response
{
    "error": {
        "code": "CAMERA_NOT_FOUND",
        "message": "Camera with ID 'cam-1' not found",
        "details": { ... }
    },
    "meta": {
        "timestamp": "2024-01-15T10:30:00Z",
        "request_id": "uuid"
    }
}

# List response
{
    "data": [ ... ],
    "meta": {
        "total": 10,
        "page": 1,
        "per_page": 20,
        "timestamp": "2024-01-15T10:30:00Z"
    }
}
```

#### WebSocket Message Structure (Updated)

```typescript
// Server -> Client (typed)
type WSMessage =
  | { type: 'stats_update', cpu_percent: number, memory_percent: number, ... }
  | { type: 'camera_event', camera_id: number, event: string, ... }
  | { type: 'job_update', job_id: number, status: string, progress?: number, ... }
  | { type: 'error', code: string, message: string }

// Client -> Server
{
    "action": "subscribe" | "unsubscribe",
    "channel": "stats" | "camera:<id>",
    "params": { ... }
}
```

### Error Handling

#### Backend Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Authentication required |
| `CAMERA_NOT_FOUND` | 404 | Camera ID does not exist |
| `CAMERA_BUSY` | 409 | Camera is in use by another operation |
| `RECORDING_LIMIT` | 409 | Max concurrent recordings reached |
| `ENCODER_BUSY` | 409 | H.264 encoder in use |
| `RATE_LIMIT` | 429 | Too many requests |
| `CAMERA_DISCONNECTED` | 503 | Camera hardware not available |
| `STORAGE_FULL` | 507 | Insufficient storage space |
| `PIPELINE_ERROR` | 500 | GStreamer pipeline failed |
| `CONFIG_ERROR` | 500 | Configuration loading failed |

#### Frontend Error Display

- **Toast notifications** for transient errors (network, validation)
- **Inline errors** for form validation
- **Error boundaries** for component crashes
- **Retry buttons** for recoverable errors
- **Login modal** for 401 responses (when auth enabled)

### Logging Standards

```python
# Structured logging format
{
    "timestamp": "2024-01-15T10:30:00.123Z",
    "level": "INFO",
    "logger": "app.services.camera",
    "message": "Camera capture started",
    "context": {
        "camera_id": "cam-1",
        "resolution": "1920x1080",
        "fps": 30,
        "request_id": "uuid"
    }
}
```

#### Log Levels

- **DEBUG**: Detailed diagnostic info (disabled in production)
- **INFO**: Normal operations (startup, capture started, etc.)
- **WARNING**: Recoverable issues (camera reconnect, low disk space, throttling)
- **ERROR**: Failures requiring attention (pipeline crash, DB error)
- **CRITICAL**: System-level failures (cannot start service)

---

## Quality Gates

### Code Quality Requirements

| Metric | Threshold | Tool |
|--------|-----------|------|
| Cyclomatic Complexity | < 10 per function | ruff/radon |
| Cognitive Complexity | < 15 per function | ruff |
| Function Length | < 50 lines | manual review |
| Test Coverage | > 70% for services | pytest-cov |
| Type Coverage | > 80% | mypy |
| Lint Errors | 0 | ruff |
| Format Compliance | 100% | black |

### Testing Requirements

#### Backend

| Test Type | Coverage Target | Framework |
|-----------|-----------------|-----------|
| Unit Tests | 80% of services | pytest |
| Integration Tests | API endpoints | pytest + httpx |
| Mock Camera Tests | Pipeline logic | pytest + mocks |
| Load Tests | Pi resource limits | locust |

#### Frontend

| Test Type | Coverage Target | Framework |
|-----------|-----------------|-----------|
| Component Tests | 60% of components | Vitest + Testing Library |
| Hook Tests | 80% of custom hooks | Vitest |
| Integration Tests | Critical flows | Vitest |
| E2E Tests | Critical user journeys | Playwright |

### Performance Budgets

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Response Time (p95) | < 200ms | No camera ops |
| Preview Latency | < 500ms | End-to-end |
| Memory Usage (idle) | < 150MB | Backend process |
| Memory Usage (streaming) | < 300MB | 1 camera active |
| CPU Usage (idle) | < 5% | Backend process |
| CPU Usage (recording) | < 60% | 1 camera H.264 |
| Frontend Bundle Size | < 500KB | gzipped |
| First Paint | < 2s | LAN connection |

### Security Checklist

- [x] Input validation on all API endpoints
- [x] Path traversal prevention for file operations
- [x] No secrets in code or logs
- [x] CORS configured for UI origin only
- [x] Rate limiting on resource-intensive endpoints
- [x] Sanitized filenames for user-provided names
- [x] No execution of user-provided data
- [x] Optional authentication available
- [x] Secure environment file permissions documented

---

## Resource Constraints (Pi 3)

### Hardware Limits

| Resource | Total | Reserved (OS) | Available |
|----------|-------|---------------|-----------|
| RAM | 1GB | ~300MB | ~700MB |
| CPU Cores | 4 | 1 (OS/system) | 3 (app) |
| H.264 Encoder | 1 | - | 1 stream |
| USB Bandwidth | 480Mbps | - | Shared |

### Operational Limits

| Operation | Limit | Rationale |
|-----------|-------|-----------|
| Max Cameras | 2-3 | USB bandwidth, CPU |
| Preview Streams | 2 at a time | MJPEG (software) |
| Recording Streams | 1 at a time | H.264 encoder single |
| Timelapse Active | 1 per camera | CPU for capture |
| Still Capture | Concurrent OK | Low resource |

### Resource Monitoring (Integrated)

| Check | Threshold | Action |
|-------|-----------|--------|
| Memory Available | < 100MB | Block new operations |
| Disk Free | < 500MB | Block recordings |
| CPU Throttled | Any flag | Show warning |
| Temperature | > 70°C | Show warning |
| Under-voltage | Detected | Show warning |

### Scaling Notes

- **Raspberry Pi 4/5**: Can support more concurrent operations
- **External Encoder**: USB capture cards could add capacity
- **NAS Storage**: Offloads disk I/O from SD card

---

## Integration Points

### Backend <-> Frontend

| Endpoint | Protocol | Purpose |
|----------|----------|---------|
| `/api/v1/*` | REST | CRUD operations |
| `/ws` | WebSocket | Real-time stats + events |
| `/api/v1/cameras/{id}/stream` | MJPEG | Live video preview |

### Backend <-> Hardware

| Component | Interface | Library |
|-----------|-----------|---------|
| CSI Camera | libcamera | picamera2 |
| USB Camera | V4L2 | GStreamer |
| H.264 Encoder | V4L2 | v4l2h264enc |
| System Stats | sysfs | psutil |
| Throttle Status | vcgencmd | subprocess |
| GPIO (future) | sysfs/gpiod | RPi.GPIO/gpiozero |

### Backend <-> Storage

| Storage Type | Interface | Config |
|--------------|-----------|--------|
| Local | Filesystem | `/var/lib/timemachine/` |
| NAS | NFS/SMB mount | User-provided path |
| Database | SQLite (WAL mode) | `/var/lib/timemachine/timemachine.db` |

---

## Risk Registry (Updated)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| H.264 encoder contention | High | High | Encoder semaphore, one-at-a-time |
| Camera disconnect during record | Medium | High | State manager, file finalization |
| GStreamer pipeline crash | Medium | High | ManagedPipeline with auto-recovery |
| SD card wear | Medium | Medium | WAL mode, NAS recommendation |
| Pi 3 memory exhaustion | Medium | High | Memory checks, systemd MemoryMax |
| USB bandwidth saturation | Medium | Medium | Resolution/fps caps |
| Service hangs | Low | High | Watchdog, health check |
| Authentication bypass | Low | Medium | Optional auth, network isolation |
| API abuse | Low | Medium | Rate limiting |
| picamera2 version issues | Low | Medium | Pin versions, test matrix |

---

## Success Criteria (Master Plan)

### Minimum Viable Product (MVP)

- [ ] Backend serves health/stats endpoints with throttle info
- [ ] Camera discovery finds CSI and USB devices
- [ ] Can capture still images from any camera
- [ ] Can record video with H.264 encoding
- [ ] Frontend displays camera status
- [ ] Can configure camera settings via UI
- [ ] Runs as systemd service
- [ ] Optional authentication works

### Full Feature Set

- [ ] All MVP items complete
- [ ] Timelapse scheduling and generation
- [ ] Timelapse interruption recovery
- [ ] Storage retention policies active
- [ ] Real-time stats via WebSocket
- [ ] Camera status sync via WebSocket
- [ ] Browser notifications for events
- [ ] Responsive UI (mobile hamburger menu)
- [ ] NAS path configuration
- [ ] Temperature control UI stub
- [ ] User documentation complete

### Quality Criteria

- [ ] All quality gates pass
- [ ] No CRITICAL issues from code-quality-evaluator
- [ ] E2E tests pass for critical flows
- [ ] Load tests pass on Pi hardware
- [ ] Memory usage within budget during all operations
- [ ] H.264 encoding maintains target fps
- [ ] Pipeline crashes auto-recover
- [ ] No path traversal vulnerabilities

---

## Appendix: Environment Variables

```bash
# Backend - Core
TIMEMACHINE_ENV=production          # development | production
TIMEMACHINE_LOG_LEVEL=INFO          # DEBUG | INFO | WARNING | ERROR
TIMEMACHINE_DB_PATH=/var/lib/timemachine/timemachine.db
TIMEMACHINE_MEDIA_PATH=/var/lib/timemachine/media
TIMEMACHINE_HOST=127.0.0.1          # Bind address
TIMEMACHINE_PORT=8000               # API port

# Backend - Security (NEW)
TIMEMACHINE_AUTH_ENABLED=false      # Enable HTTP Basic Auth
TIMEMACHINE_AUTH_USERNAME=admin     # Auth username
TIMEMACHINE_AUTH_PASSWORD=          # Auth password (required if auth enabled)
TIMEMACHINE_CORS_ORIGINS=http://localhost:5173  # Allowed CORS origins

# Encoder defaults
TIMEMACHINE_DEFAULT_RESOLUTION=1920x1080
TIMEMACHINE_DEFAULT_FPS=30
TIMEMACHINE_DEFAULT_BITRATE=4000000 # 4 Mbps
TIMEMACHINE_H264_PROFILE=main       # baseline | main | high

# Retention
TIMEMACHINE_RETENTION_DAYS=30
TIMEMACHINE_RETENTION_MAX_GB=50

# Resource limits (NEW)
TIMEMACHINE_MIN_MEMORY_MB=100       # Min memory for operations
TIMEMACHINE_MIN_DISK_MB=500         # Min disk for recordings

# Frontend build
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-01-15 | feature-planner | Initial master plan |
| 2.0 | 2024-12-06 | Claude | Integrated gap remediation tasks |

---

**Status**: `.ready.md` - Plan complete with gap remediation integrated

**Next Steps**:
1. Begin Phase 1 implementation following the integrated task order
2. Rename to `.in_progress.md` when implementation begins
3. Track sub-plan completion status in this document
4. Move to `.completed.md` when all sub-plans are implemented and verified

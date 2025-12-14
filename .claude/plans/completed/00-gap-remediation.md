# Gap Remediation Plan

## Overview

This plan addresses all gaps identified in the Gap Analysis Report. These tasks should be completed **before** or **in parallel with** the main implementation plans (01-10) to ensure a robust, production-ready system.

**Priority**: Execute before main implementation
**Estimated Duration**: 3-4 days

---

## Execution Order

```
Phase 1: Foundation Fixes (Day 1)
├── 1.1 API Contract Definition
├── 1.2 CORS Configuration
├── 1.3 SQLite Optimization
└── 1.4 WebSocket Protocol

Phase 2: Security Layer (Day 1-2)
├── 2.1 Optional Authentication
├── 2.2 Rate Limiting
├── 2.3 Secure File Serving
└── 2.4 Environment Security

Phase 3: Resource Management (Day 2)
├── 3.1 Memory Monitoring
├── 3.2 Disk Space Checks
├── 3.3 Encoder Contention
└── 3.4 Throttle Detection

Phase 4: Error Recovery (Day 2-3)
├── 4.1 GStreamer Crash Recovery
├── 4.2 Recording State Management
├── 4.3 Timelapse Interruption
└── 4.4 WebSocket Error Handling

Phase 5: Integration Fixes (Day 3)
├── 5.1 Camera Status Sync
├── 5.2 Job System Integration
└── 5.3 Notification System

Phase 6: Testing & Documentation (Day 3-4)
├── 6.1 E2E Test Framework
├── 6.2 Load Testing Setup
├── 6.3 User Documentation
└── 6.4 API Documentation
```

---

## Phase 1: Foundation Fixes

### 1.1 API Contract Definition
**Priority**: CRITICAL
**Addresses**: Gap 5.1

#### Goal
Create shared API contract between frontend and backend to prevent drift.

#### Tasks

1. **Enable OpenAPI generation in FastAPI**
   ```python
   # app/main.py
   from fastapi import FastAPI

   def create_app() -> FastAPI:
       app = FastAPI(
           title="TimeMachine API",
           description="Observation Chamber Control System",
           version="1.0.0",
           docs_url="/api/docs",
           redoc_url="/api/redoc",
           openapi_url="/api/openapi.json",
       )
       return app
   ```

2. **Create OpenAPI export script**
   ```python
   # scripts/export_openapi.py
   import json
   from app.main import create_app

   app = create_app()

   with open("openapi.json", "w") as f:
       json.dump(app.openapi(), f, indent=2)
   ```

3. **Add TypeScript type generation**
   ```bash
   # frontend/package.json - add script
   "generate:types": "openapi-typescript ../openapi.json -o src/api/types.generated.ts"
   ```

4. **Create shared types file for manual types**
   ```typescript
   // frontend/src/api/types.ts
   // Re-export generated types
   export * from './types.generated';

   // Add any manual overrides or extensions here
   ```

#### Acceptance Criteria
- [ ] OpenAPI spec accessible at `/api/openapi.json`
- [ ] TypeScript types auto-generated from spec
- [ ] Type generation runs in CI/build process

---

### 1.2 CORS Configuration
**Priority**: CRITICAL
**Addresses**: Gap 1.2

#### Goal
Configure CORS to allow frontend development and production scenarios.

#### Tasks

1. **Add CORS settings to configuration**
   ```python
   # app/core/config.py
   class Settings(BaseSettings):
       # ... existing settings ...

       # CORS
       cors_origins: list[str] = ["http://localhost:5173"]  # Vite dev server
       cors_allow_credentials: bool = True

       @property
       def cors_origins_list(self) -> list[str]:
           if self.env == "development":
               return ["*"]
           return self.cors_origins
   ```

2. **Add CORS middleware to app**
   ```python
   # app/main.py
   from fastapi.middleware.cors import CORSMiddleware

   def create_app() -> FastAPI:
       app = FastAPI(...)

       app.add_middleware(
           CORSMiddleware,
           allow_origins=settings.cors_origins_list,
           allow_credentials=settings.cors_allow_credentials,
           allow_methods=["*"],
           allow_headers=["*"],
       )

       return app
   ```

#### Acceptance Criteria
- [ ] Frontend can call API from localhost:5173
- [ ] Production restricts to configured origins
- [ ] Credentials (cookies) work if needed

---

### 1.3 SQLite Optimization for SD Card
**Priority**: CRITICAL
**Addresses**: Gap 3.2

#### Goal
Configure SQLite to minimize SD card wear and prevent corruption.

#### Tasks

1. **Create database initialization with optimized pragmas**
   ```python
   # app/db/session.py
   from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
   from sqlalchemy.orm import sessionmaker
   from sqlalchemy import event

   def create_engine(database_url: str):
       engine = create_async_engine(
           database_url,
           pool_size=5,
           max_overflow=10,
           pool_timeout=30,
           pool_pre_ping=True,
       )
       return engine

   def set_sqlite_pragmas(dbapi_connection, connection_record):
       """Configure SQLite for SD card longevity."""
       cursor = dbapi_connection.cursor()
       # WAL mode - reduces write amplification
       cursor.execute("PRAGMA journal_mode=WAL")
       # Normal sync - balance of safety and performance
       cursor.execute("PRAGMA synchronous=NORMAL")
       # Memory-mapped I/O - reduces syscalls
       cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
       # Increase cache size
       cursor.execute("PRAGMA cache_size=-64000")  # 64MB
       # Enable foreign keys
       cursor.execute("PRAGMA foreign_keys=ON")
       cursor.close()

   # Register the event listener
   from sqlalchemy import event
   event.listen(engine.sync_engine, "connect", set_sqlite_pragmas)
   ```

2. **Add periodic WAL checkpoint**
   ```python
   # app/services/maintenance.py
   import asyncio
   from sqlalchemy import text

   async def checkpoint_wal(session):
       """Checkpoint WAL file to prevent unbounded growth."""
       await session.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))

   async def maintenance_loop(session_factory):
       """Run periodic maintenance tasks."""
       while True:
           await asyncio.sleep(3600)  # Every hour
           async with session_factory() as session:
               await checkpoint_wal(session)
   ```

3. **Document storage recommendations**
   ```markdown
   # In deployment docs
   ## Storage Recommendations

   For longevity, we recommend:
   1. Use USB SSD/HDD for media storage instead of SD card
   2. Keep database on SD card (small writes) or move to USB
   3. Set TIMEMACHINE_MEDIA_PATH to USB-mounted storage
   ```

#### Acceptance Criteria
- [ ] WAL mode enabled by default
- [ ] Periodic WAL checkpointing runs
- [ ] Documentation recommends USB for media

---

### 1.4 WebSocket Protocol Definition
**Priority**: HIGH
**Addresses**: Gap 5.2

#### Goal
Define clear WebSocket message protocol for frontend/backend communication.

#### Tasks

1. **Create WebSocket protocol types (Backend)**
   ```python
   # app/models/schemas/websocket.py
   from pydantic import BaseModel
   from typing import Literal, Union, Optional
   from datetime import datetime

   class WSStatsUpdate(BaseModel):
       type: Literal["stats_update"] = "stats_update"
       cpu_percent: float
       memory_percent: float
       disk_free_gb: float
       temperature_celsius: Optional[float]
       timestamp: datetime

   class WSCameraEvent(BaseModel):
       type: Literal["camera_event"] = "camera_event"
       camera_id: int
       event: Literal["online", "offline", "recording_started", "recording_stopped", "error"]
       message: Optional[str] = None
       timestamp: datetime

   class WSJobUpdate(BaseModel):
       type: Literal["job_update"] = "job_update"
       job_id: int
       camera_id: int
       job_type: str
       status: Literal["pending", "running", "completed", "failed"]
       progress: Optional[float] = None  # 0-100
       timestamp: datetime

   class WSError(BaseModel):
       type: Literal["error"] = "error"
       code: str
       message: str
       timestamp: datetime

   WSMessage = Union[WSStatsUpdate, WSCameraEvent, WSJobUpdate, WSError]
   ```

2. **Create WebSocket protocol types (Frontend)**
   ```typescript
   // frontend/src/api/websocket.types.ts
   export type WSStatsUpdate = {
     type: 'stats_update';
     cpu_percent: number;
     memory_percent: number;
     disk_free_gb: number;
     temperature_celsius: number | null;
     timestamp: string;
   };

   export type WSCameraEvent = {
     type: 'camera_event';
     camera_id: number;
     event: 'online' | 'offline' | 'recording_started' | 'recording_stopped' | 'error';
     message?: string;
     timestamp: string;
   };

   export type WSJobUpdate = {
     type: 'job_update';
     job_id: number;
     camera_id: number;
     job_type: string;
     status: 'pending' | 'running' | 'completed' | 'failed';
     progress?: number;
     timestamp: string;
   };

   export type WSError = {
     type: 'error';
     code: string;
     message: string;
     timestamp: string;
   };

   export type WSMessage = WSStatsUpdate | WSCameraEvent | WSJobUpdate | WSError;

   export function isStatsUpdate(msg: WSMessage): msg is WSStatsUpdate {
     return msg.type === 'stats_update';
   }

   export function isCameraEvent(msg: WSMessage): msg is WSCameraEvent {
     return msg.type === 'camera_event';
   }

   export function isJobUpdate(msg: WSMessage): msg is WSJobUpdate {
     return msg.type === 'job_update';
   }
   ```

3. **Update WebSocket client to use typed messages**
   ```typescript
   // frontend/src/api/websocket.ts
   import { WSMessage, isStatsUpdate, isCameraEvent, isJobUpdate } from './websocket.types';

   type MessageHandler<T extends WSMessage> = (msg: T) => void;

   class WebSocketClient {
     private handlers: Map<string, Set<MessageHandler<any>>> = new Map();

     subscribe<T extends WSMessage['type']>(
       type: T,
       handler: MessageHandler<Extract<WSMessage, { type: T }>>
     ): () => void {
       if (!this.handlers.has(type)) {
         this.handlers.set(type, new Set());
       }
       this.handlers.get(type)!.add(handler);

       return () => this.handlers.get(type)?.delete(handler);
     }

     private handleMessage(data: string) {
       try {
         const msg: WSMessage = JSON.parse(data);
         const handlers = this.handlers.get(msg.type);
         handlers?.forEach(handler => handler(msg));
       } catch (e) {
         console.error('Invalid WebSocket message', e);
       }
     }
   }
   ```

#### Acceptance Criteria
- [ ] Protocol types defined in both backend and frontend
- [ ] Type guards for message discrimination
- [ ] WebSocket client uses typed handlers

---

## Phase 2: Security Layer

### 2.1 Optional Authentication System
**Priority**: CRITICAL
**Addresses**: Gap 1.1

#### Goal
Add optional HTTP Basic authentication that can be enabled via configuration.

#### Tasks

1. **Add auth settings**
   ```python
   # app/core/config.py
   class Settings(BaseSettings):
       # ... existing ...

       # Authentication (optional)
       auth_enabled: bool = False
       auth_username: str = "admin"
       auth_password: Optional[str] = None  # Must be set if auth_enabled

       def validate_auth(self):
           if self.auth_enabled and not self.auth_password:
               raise ValueError("TIMEMACHINE_AUTH_PASSWORD required when auth enabled")
   ```

2. **Create auth dependency**
   ```python
   # app/core/security.py
   import secrets
   from fastapi import Depends, HTTPException, status
   from fastapi.security import HTTPBasic, HTTPBasicCredentials
   from app.core.config import settings

   security = HTTPBasic(auto_error=False)

   async def verify_auth(
       credentials: HTTPBasicCredentials = Depends(security)
   ) -> bool:
       """Verify authentication if enabled."""
       if not settings.auth_enabled:
           return True

       if credentials is None:
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail="Authentication required",
               headers={"WWW-Authenticate": "Basic"},
           )

       correct_username = secrets.compare_digest(
           credentials.username.encode("utf8"),
           settings.auth_username.encode("utf8")
       )
       correct_password = secrets.compare_digest(
           credentials.password.encode("utf8"),
           settings.auth_password.encode("utf8")
       )

       if not (correct_username and correct_password):
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail="Invalid credentials",
               headers={"WWW-Authenticate": "Basic"},
           )

       return True

   # Dependency for protected routes
   def require_auth():
       return Depends(verify_auth)
   ```

3. **Apply auth to routes**
   ```python
   # app/api/routes/cameras.py
   from app.core.security import require_auth

   router = APIRouter(
       prefix="/cameras",
       dependencies=[require_auth()]  # All routes in this router protected
   )
   ```

4. **Exclude health endpoint from auth**
   ```python
   # app/api/routes/health.py
   # No auth dependency - health check should always be accessible
   router = APIRouter(prefix="/health")

   @router.get("")
   async def health_check():
       # ...
   ```

5. **Add frontend auth handling**
   ```typescript
   // frontend/src/api/client.ts
   class ApiClient {
     private credentials: string | null = null;

     setCredentials(username: string, password: string) {
       this.credentials = btoa(`${username}:${password}`);
     }

     clearCredentials() {
       this.credentials = null;
     }

     private async fetch<T>(url: string, options: RequestInit = {}): Promise<T> {
       const headers: HeadersInit = {
         'Content-Type': 'application/json',
         ...options.headers,
       };

       if (this.credentials) {
         headers['Authorization'] = `Basic ${this.credentials}`;
       }

       const response = await fetch(url, { ...options, headers });

       if (response.status === 401) {
         // Emit event for login prompt
         window.dispatchEvent(new CustomEvent('auth-required'));
         throw new AuthError('Authentication required');
       }

       // ... rest of error handling
     }
   }
   ```

6. **Create login modal component**
   ```typescript
   // frontend/src/components/auth/LoginModal.tsx
   import { useState, useEffect } from 'react';
   import { api } from '@/api/client';
   import { Modal } from '@/components/common/Modal';
   import { Input } from '@/components/common/Input';
   import { Button } from '@/components/common/Button';

   export function LoginModal() {
     const [show, setShow] = useState(false);
     const [username, setUsername] = useState('');
     const [password, setPassword] = useState('');
     const [error, setError] = useState('');

     useEffect(() => {
       const handler = () => setShow(true);
       window.addEventListener('auth-required', handler);
       return () => window.removeEventListener('auth-required', handler);
     }, []);

     const handleLogin = async () => {
       api.setCredentials(username, password);
       try {
         await api.get('/api/v1/health'); // Test credentials
         setShow(false);
         setError('');
         window.location.reload(); // Reload to retry failed requests
       } catch (e) {
         setError('Invalid credentials');
         api.clearCredentials();
       }
     };

     if (!show) return null;

     return (
       <Modal onClose={() => {}}>
         <h2>Login Required</h2>
         {error && <p className="error">{error}</p>}
         <Input
           label="Username"
           value={username}
           onChange={(e) => setUsername(e.target.value)}
         />
         <Input
           label="Password"
           type="password"
           value={password}
           onChange={(e) => setPassword(e.target.value)}
         />
         <Button onClick={handleLogin}>Login</Button>
       </Modal>
     );
   }
   ```

#### Acceptance Criteria
- [ ] Auth disabled by default
- [ ] Setting TIMEMACHINE_AUTH_ENABLED=true requires password
- [ ] 401 returned when auth fails
- [ ] Health endpoint always accessible
- [ ] Frontend prompts for login on 401

---

### 2.2 Rate Limiting
**Priority**: HIGH
**Addresses**: Gap 1.4

#### Goal
Protect API from abuse with rate limiting on sensitive endpoints.

#### Tasks

1. **Install slowapi**
   ```bash
   pip install slowapi
   ```

2. **Configure rate limiter**
   ```python
   # app/core/rate_limit.py
   from slowapi import Limiter
   from slowapi.util import get_remote_address
   from slowapi.errors import RateLimitExceeded
   from fastapi import Request
   from fastapi.responses import JSONResponse

   limiter = Limiter(key_func=get_remote_address)

   async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
       return JSONResponse(
           status_code=429,
           content={
               "error": "rate_limit_exceeded",
               "message": f"Rate limit exceeded: {exc.detail}",
               "retry_after": exc.retry_after,
           }
       )
   ```

3. **Add limiter to app**
   ```python
   # app/main.py
   from slowapi import _rate_limit_exceeded_handler
   from slowapi.errors import RateLimitExceeded
   from app.core.rate_limit import limiter, rate_limit_handler

   def create_app() -> FastAPI:
       app = FastAPI(...)

       app.state.limiter = limiter
       app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

       return app
   ```

4. **Apply limits to endpoints**
   ```python
   # app/api/routes/cameras.py
   from app.core.rate_limit import limiter

   @router.post("/{camera_id}/capture")
   @limiter.limit("1/second")  # Max 1 capture per second
   async def capture_still(
       request: Request,  # Required for rate limiting
       camera_id: int,
       session: AsyncSession = Depends(get_session),
   ):
       # ...

   @router.post("/{camera_id}/record/start")
   @limiter.limit("5/minute")  # Max 5 recording starts per minute
   async def start_recording(request: Request, camera_id: int):
       # ...

   # app/api/routes/storage.py
   @router.get("/files")
   @limiter.limit("30/minute")  # Limit file listing
   async def list_files(request: Request):
       # ...

   @router.post("/cleanup")
   @limiter.limit("1/hour")  # Limit cleanup triggers
   async def trigger_cleanup(request: Request):
       # ...
   ```

#### Acceptance Criteria
- [ ] Capture limited to 1/second
- [ ] Recording starts limited to 5/minute
- [ ] File listing limited to 30/minute
- [ ] 429 response with retry-after header

---

### 2.3 Secure File Serving Endpoint
**Priority**: HIGH
**Addresses**: Gap 1.3

#### Goal
Create secure file serving endpoint that prevents path traversal.

#### Tasks

1. **Create file serving endpoint**
   ```python
   # app/api/routes/storage.py
   from fastapi import APIRouter, HTTPException, Path
   from fastapi.responses import FileResponse
   from pathlib import Path as FilePath
   import hashlib
   import base64

   router = APIRouter(prefix="/storage")

   def encode_file_id(path: str) -> str:
       """Create URL-safe file ID from path."""
       return base64.urlsafe_b64encode(path.encode()).decode()

   def decode_file_id(file_id: str) -> str:
       """Decode file ID back to path."""
       try:
           return base64.urlsafe_b64decode(file_id.encode()).decode()
       except Exception:
           raise HTTPException(status_code=400, detail="Invalid file ID")

   @router.get("/files/{file_id}")
   async def download_file(
       file_id: str = Path(..., description="Base64-encoded file path"),
       session: AsyncSession = Depends(get_session),
   ):
       """Download a stored file securely."""
       # Decode the file ID
       file_path_str = decode_file_id(file_id)
       file_path = FilePath(file_path_str)

       # Get storage service and validate path
       storage = get_storage_service(session)

       # Validate path is within allowed directories
       valid = False
       for base in storage.base_paths.values():
           try:
               file_path.resolve().relative_to(base.resolve())
               valid = True
               break
           except ValueError:
               continue

       if not valid:
           raise HTTPException(status_code=403, detail="Access denied")

       if not file_path.exists():
           raise HTTPException(status_code=404, detail="File not found")

       # Determine content type
       content_type = "application/octet-stream"
       if file_path.suffix.lower() in [".jpg", ".jpeg"]:
           content_type = "image/jpeg"
       elif file_path.suffix.lower() == ".png":
           content_type = "image/png"
       elif file_path.suffix.lower() == ".mp4":
           content_type = "video/mp4"

       return FileResponse(
           path=file_path,
           media_type=content_type,
           filename=file_path.name,
       )
   ```

2. **Update frontend to use file IDs**
   ```typescript
   // frontend/src/api/storage.ts
   export function encodeFileId(path: string): string {
     return btoa(path).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
   }

   export function getFileUrl(path: string): string {
     return `/api/v1/storage/files/${encodeFileId(path)}`;
   }
   ```

3. **Update CaptureTab to use secure URLs**
   ```typescript
   // frontend/src/pages/Camera/CaptureTab.tsx
   import { getFileUrl } from '@/api/storage';

   // Change from:
   // src={`/api/v1/storage/files/${encodeURIComponent(lastCapture.path)}`}
   // To:
   src={getFileUrl(lastCapture.path)}
   ```

#### Acceptance Criteria
- [ ] Files served via opaque file IDs
- [ ] Path traversal attempts return 403
- [ ] Correct content types set
- [ ] Frontend uses secure URL generation

---

### 2.4 Environment Security Documentation
**Priority**: MEDIUM
**Addresses**: Gap 1.5

#### Tasks

1. **Update environment file template**
   ```bash
   # deploy/timemachine.env.example

   # ============================================
   # SECURITY WARNING
   # ============================================
   # If authentication is enabled, this file contains secrets.
   # Ensure file permissions are set to 600 (owner read/write only):
   #   chmod 600 /etc/timemachine/timemachine.env
   # ============================================

   # Authentication (disabled by default)
   TIMEMACHINE_AUTH_ENABLED=false
   # TIMEMACHINE_AUTH_USERNAME=admin
   # TIMEMACHINE_AUTH_PASSWORD=changeme

   # ... rest of config ...
   ```

2. **Update install script**
   ```bash
   # scripts/install.sh

   # Copy configuration
   if [ ! -f /etc/timemachine/timemachine.env ]; then
     cp deploy/timemachine.env.example /etc/timemachine/timemachine.env
     # Secure permissions - only owner can read/write
     chmod 600 /etc/timemachine/timemachine.env
     chown root:root /etc/timemachine/timemachine.env
   fi
   ```

#### Acceptance Criteria
- [ ] Security warning in env template
- [ ] Install script sets 600 permissions
- [ ] Documentation mentions secret handling

---

## Phase 3: Resource Management

### 3.1 Memory Monitoring and Limits
**Priority**: CRITICAL
**Addresses**: Gap 3.1

#### Goal
Monitor memory usage and implement graceful degradation under pressure.

#### Tasks

1. **Add memory monitoring to stats**
   ```python
   # app/api/routes/health.py
   import psutil

   @router.get("/stats")
   async def get_stats():
       memory = psutil.virtual_memory()

       # Memory pressure levels
       if memory.percent > 90:
           memory_status = "critical"
       elif memory.percent > 75:
           memory_status = "warning"
       else:
           memory_status = "ok"

       return {
           "cpu_percent": psutil.cpu_percent(interval=0.1),
           "memory": {
               "percent": memory.percent,
               "available_mb": memory.available / (1024 * 1024),
               "status": memory_status,
           },
           "disk": {
               # ... existing disk stats
           },
       }
   ```

2. **Add memory check before expensive operations**
   ```python
   # app/services/camera/manager.py
   import psutil

   class MemoryPressureError(Exception):
       pass

   def check_memory_available(min_mb: int = 100):
       """Raise error if available memory is below threshold."""
       available = psutil.virtual_memory().available / (1024 * 1024)
       if available < min_mb:
           raise MemoryPressureError(
               f"Insufficient memory: {available:.0f}MB available, {min_mb}MB required"
           )

   class CameraManager:
       async def start_preview(self, camera_id: int):
           check_memory_available(min_mb=100)
           # ... start preview

       async def start_recording(self, camera_id: int, settings: dict):
           check_memory_available(min_mb=200)
           # ... start recording
   ```

3. **Add memory limit to systemd service**
   ```ini
   # deploy/timemachine.service
   [Service]
   # ... existing config ...

   # Memory limit - prevent OOM killer from affecting system
   MemoryMax=800M
   MemoryHigh=700M

   # When memory high, systemd will throttle
   ```

4. **Reduce frontend chart history**
   ```typescript
   // frontend/src/pages/Home/SystemGraphs.tsx
   // Change from 60 points to 30 to reduce memory
   const MAX_POINTS = 30;
   ```

#### Acceptance Criteria
- [ ] Memory status in stats endpoint
- [ ] Memory check before recording/preview
- [ ] Systemd memory limits configured
- [ ] Chart history reduced

---

### 3.2 Disk Space Pre-flight Checks
**Priority**: HIGH
**Addresses**: Gap 3.6

#### Goal
Verify sufficient disk space before starting recordings.

#### Tasks

1. **Create disk space checker**
   ```python
   # app/services/storage/checks.py
   import shutil
   from pathlib import Path

   class InsufficientSpaceError(Exception):
       def __init__(self, path: str, required_mb: int, available_mb: int):
           self.path = path
           self.required_mb = required_mb
           self.available_mb = available_mb
           super().__init__(
               f"Insufficient space at {path}: "
               f"{available_mb}MB available, {required_mb}MB required"
           )

   def check_disk_space(path: Path, required_mb: int = 500):
       """Verify minimum disk space available."""
       try:
           usage = shutil.disk_usage(path)
           available_mb = usage.free / (1024 * 1024)

           if available_mb < required_mb:
               raise InsufficientSpaceError(str(path), required_mb, int(available_mb))

           return available_mb
       except OSError as e:
           raise InsufficientSpaceError(str(path), required_mb, 0)

   def estimate_recording_duration(available_mb: float, bitrate_bps: int) -> int:
       """Estimate max recording duration in seconds."""
       bytes_per_second = bitrate_bps / 8
       mb_per_second = bytes_per_second / (1024 * 1024)

       # Leave 100MB buffer
       usable_mb = max(0, available_mb - 100)

       return int(usable_mb / mb_per_second)
   ```

2. **Integrate into recording service**
   ```python
   # app/services/camera/recording.py
   from app.services.storage.checks import check_disk_space, estimate_recording_duration

   class RecordingService:
       async def start_recording(
           self,
           camera_id: int,
           bitrate: int = 4_000_000,
       ) -> dict:
           # Check disk space
           available = check_disk_space(self.recording_path, required_mb=500)
           max_duration = estimate_recording_duration(available, bitrate)

           # Warn if limited duration
           if max_duration < 300:  # Less than 5 minutes
               logger.warning(
                   "low_disk_space",
                   available_mb=available,
                   max_duration_seconds=max_duration,
               )

           # ... start recording

           return {
               "status": "recording",
               "max_duration_seconds": max_duration,
               "warning": "Low disk space" if max_duration < 300 else None,
           }
   ```

3. **Add disk space to recording API response**
   ```python
   # app/api/routes/cameras.py

   @router.post("/{camera_id}/record/start")
   async def start_recording(camera_id: int, data: RecordingStartRequest):
       try:
           result = await recording_service.start_recording(
               camera_id,
               bitrate=data.bitrate,
           )
           return ResponseWrapper(
               data=result,
               meta=Meta(timestamp=datetime.utcnow()),
           )
       except InsufficientSpaceError as e:
           raise HTTPException(
               status_code=507,  # Insufficient Storage
               detail={
                   "error": "insufficient_storage",
                   "message": str(e),
                   "available_mb": e.available_mb,
                   "required_mb": e.required_mb,
               }
           )
   ```

4. **Update frontend to show warnings**
   ```typescript
   // frontend/src/pages/Camera/RecordTab.tsx

   const startRecording = useMutation({
     mutationFn: () =>
       api.post(`/api/v1/cameras/${cameraId}/record/start`, { bitrate }),
     onSuccess: (data) => {
       setIsRecording(true);
       if (data.warning) {
         toast.warning(`${data.warning} - Max ${Math.floor(data.max_duration_seconds / 60)} minutes`);
       }
     },
     onError: (error) => {
       if (error.status === 507) {
         toast.error(`Not enough disk space: ${error.data.available_mb}MB available`);
       }
     },
   });
   ```

#### Acceptance Criteria
- [ ] 507 error when disk space insufficient
- [ ] Max recording duration calculated
- [ ] Warning shown when space low
- [ ] Frontend displays disk space errors

---

### 3.3 Hardware Encoder Contention Management
**Priority**: HIGH
**Addresses**: Gap 3.3

#### Goal
Manage single H.264 hardware encoder to prevent conflicts.

#### Tasks

1. **Create encoder semaphore**
   ```python
   # app/services/camera/encoder.py
   import asyncio
   from contextlib import asynccontextmanager
   from typing import Optional

   class EncoderManager:
       """Manage access to the single H.264 hardware encoder."""

       def __init__(self):
           self._lock = asyncio.Lock()
           self._current_user: Optional[str] = None

       @property
       def is_available(self) -> bool:
           return not self._lock.locked()

       @property
       def current_user(self) -> Optional[str]:
           return self._current_user

       @asynccontextmanager
       async def acquire(self, user_id: str, timeout: float = 0):
           """Acquire the encoder for exclusive use."""
           try:
               acquired = await asyncio.wait_for(
                   self._lock.acquire(),
                   timeout=timeout if timeout > 0 else None,
               )
               if acquired:
                   self._current_user = user_id
                   yield True
               else:
                   yield False
           except asyncio.TimeoutError:
               yield False
           finally:
               if self._lock.locked():
                   self._current_user = None
                   self._lock.release()

       def try_acquire(self, user_id: str) -> bool:
           """Try to acquire without waiting."""
           if self._lock.locked():
               return False
           # Note: This has a race condition, use acquire() for safety
           return True

   # Global encoder manager
   encoder_manager = EncoderManager()
   ```

2. **Use encoder lock in recording service**
   ```python
   # app/services/camera/recording.py
   from app.services.camera.encoder import encoder_manager

   class EncoderBusyError(Exception):
       def __init__(self, current_user: str):
           self.current_user = current_user
           super().__init__(f"Encoder busy: {current_user}")

   class RecordingService:
       async def start_recording(self, camera_id: int, bitrate: int):
           user_id = f"recording_camera_{camera_id}"

           async with encoder_manager.acquire(user_id, timeout=0) as acquired:
               if not acquired:
                   raise EncoderBusyError(encoder_manager.current_user)

               # Now we have exclusive encoder access
               # ... start recording pipeline
   ```

3. **Document preview uses MJPEG**
   ```python
   # app/services/camera/preview.py
   """
   Preview Service

   Uses MJPEG encoding (software) for preview streams.
   This allows preview to work even while recording uses the H.264 encoder.

   Pipeline: camera -> jpegenc -> multipart/x-mixed-replace
   """
   ```

#### Acceptance Criteria
- [ ] Only one H.264 encoding operation at a time
- [ ] Clear error when encoder busy
- [ ] Preview uses MJPEG (not H.264)
- [ ] Documentation clarifies encoder usage

---

### 3.4 Throttle Detection
**Priority**: HIGH
**Addresses**: Gap 3.4

#### Goal
Detect Pi throttling due to thermal/voltage issues.

#### Tasks

1. **Create throttle detection utility**
   ```python
   # app/services/system/throttle.py
   import subprocess
   import structlog

   logger = structlog.get_logger(__name__)

   # Throttle flag bits from vcgencmd
   THROTTLE_FLAGS = {
       0: "under_voltage_detected",
       1: "arm_frequency_capped",
       2: "currently_throttled",
       3: "soft_temp_limit_active",
       16: "under_voltage_occurred",
       17: "arm_frequency_capped_occurred",
       18: "throttling_occurred",
       19: "soft_temp_limit_occurred",
   }

   def get_throttle_status() -> dict:
       """Get Pi throttle status from vcgencmd."""
       try:
           result = subprocess.run(
               ["vcgencmd", "get_throttled"],
               capture_output=True,
               text=True,
               timeout=5,
           )

           if result.returncode != 0:
               return {"available": False, "error": "vcgencmd failed"}

           # Parse "throttled=0x50005"
           output = result.stdout.strip()
           hex_value = output.split("=")[1]
           flags = int(hex_value, 16)

           active_flags = []
           historical_flags = []

           for bit, name in THROTTLE_FLAGS.items():
               if flags & (1 << bit):
                   if bit < 16:
                       active_flags.append(name)
                   else:
                       historical_flags.append(name)

           return {
               "available": True,
               "raw_value": hex_value,
               "is_throttled": len(active_flags) > 0,
               "active": active_flags,
               "historical": historical_flags,
           }

       except FileNotFoundError:
           return {"available": False, "error": "vcgencmd not found"}
       except Exception as e:
           logger.warning("throttle_check_failed", error=str(e))
           return {"available": False, "error": str(e)}
   ```

2. **Add to stats endpoint**
   ```python
   # app/api/routes/health.py
   from app.services.system.throttle import get_throttle_status

   @router.get("/stats")
   async def get_stats():
       throttle = get_throttle_status()

       return {
           "cpu_percent": psutil.cpu_percent(),
           "memory": { ... },
           "disk": { ... },
           "temperature_celsius": get_temperature(),
           "throttle": throttle,
       }
   ```

3. **Add frontend warning**
   ```typescript
   // frontend/src/pages/Home/WarningBanner.tsx

   function ThrottleWarning({ throttle }) {
     if (!throttle?.is_throttled) return null;

     const warnings = [];
     if (throttle.active.includes('under_voltage_detected')) {
       warnings.push('Low voltage - use official power supply');
     }
     if (throttle.active.includes('currently_throttled')) {
       warnings.push('CPU throttled due to temperature');
     }

     return (
       <div className={styles.warning}>
         <span>⚠️ System Warning</span>
         <ul>
           {warnings.map((w, i) => <li key={i}>{w}</li>)}
         </ul>
       </div>
     );
   }
   ```

#### Acceptance Criteria
- [ ] Throttle status in stats response
- [ ] Under-voltage detection works
- [ ] Thermal throttling detection works
- [ ] Frontend shows throttle warnings

---

## Phase 4: Error Recovery

### 4.1 GStreamer Pipeline Crash Recovery
**Priority**: CRITICAL
**Addresses**: Gap 2.1

#### Goal
Automatically recover from GStreamer pipeline failures.

#### Tasks

1. **Create pipeline wrapper with error handling**
   ```python
   # app/services/camera/pipeline.py
   import gi
   gi.require_version('Gst', '1.0')
   from gi.repository import Gst, GLib
   import asyncio
   import structlog
   from typing import Callable, Optional
   from enum import Enum

   logger = structlog.get_logger(__name__)

   class PipelineState(Enum):
       STOPPED = "stopped"
       STARTING = "starting"
       RUNNING = "running"
       ERROR = "error"
       RECOVERING = "recovering"

   class ManagedPipeline:
       """GStreamer pipeline with automatic crash recovery."""

       def __init__(
           self,
           name: str,
           pipeline_string: str,
           on_error: Optional[Callable[[str], None]] = None,
           max_retries: int = 3,
           retry_delay: float = 2.0,
       ):
           self.name = name
           self.pipeline_string = pipeline_string
           self.on_error = on_error
           self.max_retries = max_retries
           self.retry_delay = retry_delay

           self._pipeline: Optional[Gst.Pipeline] = None
           self._state = PipelineState.STOPPED
           self._retry_count = 0
           self._bus_watch_id: Optional[int] = None

       @property
       def state(self) -> PipelineState:
           return self._state

       async def start(self) -> bool:
           """Start the pipeline."""
           if self._state == PipelineState.RUNNING:
               return True

           self._state = PipelineState.STARTING
           self._retry_count = 0

           return await self._start_pipeline()

       async def _start_pipeline(self) -> bool:
           """Internal start with retry logic."""
           try:
               # Create pipeline
               self._pipeline = Gst.parse_launch(self.pipeline_string)

               # Set up bus message handling
               bus = self._pipeline.get_bus()
               bus.add_signal_watch()
               bus.connect("message::error", self._on_error)
               bus.connect("message::eos", self._on_eos)
               bus.connect("message::state-changed", self._on_state_changed)

               # Start pipeline
               ret = self._pipeline.set_state(Gst.State.PLAYING)

               if ret == Gst.StateChangeReturn.FAILURE:
                   raise RuntimeError("Failed to start pipeline")

               self._state = PipelineState.RUNNING
               logger.info("pipeline_started", name=self.name)
               return True

           except Exception as e:
               logger.error("pipeline_start_failed", name=self.name, error=str(e))
               self._state = PipelineState.ERROR
               await self._attempt_recovery()
               return self._state == PipelineState.RUNNING

       def _on_error(self, bus, message):
           """Handle GStreamer error messages."""
           err, debug = message.parse_error()
           logger.error(
               "pipeline_error",
               name=self.name,
               error=err.message,
               debug=debug,
           )
           self._state = PipelineState.ERROR

           # Schedule recovery
           asyncio.create_task(self._attempt_recovery())

       def _on_eos(self, bus, message):
           """Handle end-of-stream."""
           logger.info("pipeline_eos", name=self.name)
           self._state = PipelineState.STOPPED

       def _on_state_changed(self, bus, message):
           """Handle state changes."""
           if message.src == self._pipeline:
               old, new, pending = message.parse_state_changed()
               logger.debug(
                   "pipeline_state_changed",
                   name=self.name,
                   old=old.value_nick,
                   new=new.value_nick,
               )

       async def _attempt_recovery(self):
           """Attempt to recover from error."""
           if self._retry_count >= self.max_retries:
               logger.error(
                   "pipeline_recovery_failed",
                   name=self.name,
                   retries=self._retry_count,
               )
               if self.on_error:
                   self.on_error(f"Pipeline {self.name} failed after {self._retry_count} retries")
               return

           self._state = PipelineState.RECOVERING
           self._retry_count += 1

           logger.info(
               "pipeline_recovering",
               name=self.name,
               attempt=self._retry_count,
           )

           # Stop current pipeline
           await self.stop()

           # Wait before retry
           await asyncio.sleep(self.retry_delay * self._retry_count)

           # Retry
           await self._start_pipeline()

       async def stop(self):
           """Stop the pipeline."""
           if self._pipeline:
               self._pipeline.set_state(Gst.State.NULL)
               self._pipeline = None
           self._state = PipelineState.STOPPED
           logger.info("pipeline_stopped", name=self.name)
   ```

2. **Use managed pipeline in camera service**
   ```python
   # app/services/camera/preview.py
   from app.services.camera.pipeline import ManagedPipeline

   class PreviewService:
       def __init__(self):
           self._pipelines: dict[int, ManagedPipeline] = {}
           self._ws_manager = get_ws_manager()

       async def start_preview(self, camera_id: int, source: CameraSource):
           pipeline_string = source.get_preview_pipeline()

           def on_error(message: str):
               # Notify clients via WebSocket
               self._ws_manager.broadcast({
                   "type": "camera_event",
                   "camera_id": camera_id,
                   "event": "error",
                   "message": message,
               })

           pipeline = ManagedPipeline(
               name=f"preview_{camera_id}",
               pipeline_string=pipeline_string,
               on_error=on_error,
               max_retries=3,
           )

           self._pipelines[camera_id] = pipeline
           return await pipeline.start()
   ```

3. **Add health check for pipelines**
   ```python
   # app/services/camera/manager.py

   class CameraManager:
       async def check_pipeline_health(self) -> dict:
           """Check health of all active pipelines."""
           status = {}
           for camera_id, pipeline in self._preview_service._pipelines.items():
               status[camera_id] = {
                   "state": pipeline.state.value,
                   "healthy": pipeline.state == PipelineState.RUNNING,
               }
           return status
   ```

#### Acceptance Criteria
- [ ] Pipeline errors caught and logged
- [ ] Automatic retry with backoff
- [ ] Max retry limit enforced
- [ ] WebSocket notification on failure
- [ ] Health check shows pipeline status

---

### 4.2 Recording State Management
**Priority**: HIGH
**Addresses**: Gap 2.2

#### Goal
Robust recording state management with orphan cleanup.

#### Tasks

1. **Create recording state manager**
   ```python
   # app/services/camera/recording_state.py
   from dataclasses import dataclass
   from datetime import datetime
   from typing import Optional
   import asyncio
   import psutil
   import structlog

   logger = structlog.get_logger(__name__)

   @dataclass
   class RecordingInfo:
       camera_id: int
       job_id: int
       started_at: datetime
       pid: int
       output_path: str

   class RecordingStateManager:
       """Track recording state and clean up orphans."""

       def __init__(self):
           self._recordings: dict[int, RecordingInfo] = {}
           self._lock = asyncio.Lock()

       async def register(
           self,
           camera_id: int,
           job_id: int,
           pid: int,
           output_path: str,
       ):
           """Register a new recording."""
           async with self._lock:
               self._recordings[camera_id] = RecordingInfo(
                   camera_id=camera_id,
                   job_id=job_id,
                   started_at=datetime.utcnow(),
                   pid=pid,
                   output_path=output_path,
               )

       async def unregister(self, camera_id: int) -> Optional[RecordingInfo]:
           """Unregister a recording."""
           async with self._lock:
               return self._recordings.pop(camera_id, None)

       def is_recording(self, camera_id: int) -> bool:
           """Check if camera is currently recording."""
           return camera_id in self._recordings

       @property
       def active_count(self) -> int:
           """Number of active recordings."""
           return len(self._recordings)

       async def verify_recording(self, camera_id: int) -> bool:
           """Verify recording process is actually running."""
           info = self._recordings.get(camera_id)
           if not info:
               return False

           try:
               process = psutil.Process(info.pid)
               return process.is_running()
           except psutil.NoSuchProcess:
               # Process died - clean up
               logger.warning(
                   "recording_process_died",
                   camera_id=camera_id,
                   pid=info.pid,
               )
               await self.unregister(camera_id)
               return False

       async def cleanup_orphans(self):
           """Clean up any orphaned recording states."""
           orphans = []

           async with self._lock:
               for camera_id, info in list(self._recordings.items()):
                   try:
                       process = psutil.Process(info.pid)
                       if not process.is_running():
                           orphans.append(camera_id)
                   except psutil.NoSuchProcess:
                       orphans.append(camera_id)

           for camera_id in orphans:
               logger.warning("cleaning_orphan_recording", camera_id=camera_id)
               await self.unregister(camera_id)

           return len(orphans)

   # Global instance
   recording_state = RecordingStateManager()
   ```

2. **Run cleanup on startup**
   ```python
   # app/main.py
   from app.services.camera.recording_state import recording_state

   @app.on_event("startup")
   async def startup():
       # Clean up any orphaned recording states
       orphans = await recording_state.cleanup_orphans()
       if orphans:
           logger.info("cleaned_orphan_recordings", count=orphans)
   ```

3. **Integrate with recording service**
   ```python
   # app/services/camera/recording.py
   from app.services.camera.recording_state import recording_state

   class RecordingService:
       async def start_recording(self, camera_id: int, ...):
           # Check recording limit
           if recording_state.active_count >= MAX_CONCURRENT_RECORDINGS:
               raise HTTPException(
                   status_code=409,
                   detail={
                       "error": "recording_limit_reached",
                       "message": f"Maximum {MAX_CONCURRENT_RECORDINGS} concurrent recording(s) allowed",
                       "active_cameras": list(recording_state._recordings.keys()),
                   }
               )

           # Check if this camera is already recording
           if recording_state.is_recording(camera_id):
               # Verify it's actually running
               if await recording_state.verify_recording(camera_id):
                   raise HTTPException(
                       status_code=409,
                       detail={"error": "already_recording", "camera_id": camera_id}
                   )

           # ... start recording, get pid ...

           await recording_state.register(camera_id, job_id, pid, output_path)
   ```

#### Acceptance Criteria
- [ ] Recording state tracked with PIDs
- [ ] 409 when recording limit reached
- [ ] Orphan cleanup on startup
- [ ] Dead process detection

---

### 4.3 Timelapse Interruption Recovery
**Priority**: HIGH
**Addresses**: Gap 2.5

#### Goal
Handle timelapse interruption with resume/cleanup options.

#### Tasks

1. **Store timelapse state in database**
   ```python
   # app/db/models.py (update Jobs table)

   class Job(Base):
       __tablename__ = "jobs"

       id = Column(Integer, primary_key=True)
       camera_id = Column(Integer, ForeignKey("cameras.id"))
       job_type = Column(String)  # "recording", "timelapse", "capture"
       status = Column(String)  # "pending", "running", "completed", "failed", "interrupted"

       # Timelapse-specific fields
       timelapse_config = Column(JSON, nullable=True)  # {interval, total_frames, quality}
       timelapse_progress = Column(Integer, default=0)  # Current frame count
       timelapse_dir = Column(String, nullable=True)  # Directory for frames

       started_at = Column(DateTime)
       completed_at = Column(DateTime, nullable=True)
       error_message = Column(String, nullable=True)
   ```

2. **Create timelapse recovery service**
   ```python
   # app/services/camera/timelapse_recovery.py
   from pathlib import Path
   import structlog

   logger = structlog.get_logger(__name__)

   class TimelapseRecovery:
       def __init__(self, session_factory):
           self.session_factory = session_factory

       async def find_interrupted(self) -> list[dict]:
           """Find timelapses that were interrupted."""
           async with self.session_factory() as session:
               result = await session.execute(
                   select(Job).where(
                       Job.job_type == "timelapse",
                       Job.status == "running",
                   )
               )
               interrupted = []
               for job in result.scalars():
                   dir_path = Path(job.timelapse_dir)
                   frame_count = len(list(dir_path.glob("frame_*.jpg"))) if dir_path.exists() else 0

                   interrupted.append({
                       "job_id": job.id,
                       "camera_id": job.camera_id,
                       "config": job.timelapse_config,
                       "progress": frame_count,
                       "directory": str(dir_path),
                   })

               return interrupted

       async def resume_timelapse(self, job_id: int) -> bool:
           """Resume an interrupted timelapse."""
           async with self.session_factory() as session:
               job = await session.get(Job, job_id)
               if not job or job.status != "running":
                   return False

               # Count existing frames
               dir_path = Path(job.timelapse_dir)
               existing_frames = len(list(dir_path.glob("frame_*.jpg")))

               # Update progress and restart
               job.timelapse_progress = existing_frames
               await session.commit()

               # Start timelapse service from where we left off
               config = job.timelapse_config
               remaining_frames = config["total_frames"] - existing_frames

               if remaining_frames <= 0:
                   job.status = "completed"
                   await session.commit()
                   return True

               # ... restart timelapse capture
               return True

       async def cleanup_timelapse(self, job_id: int, delete_frames: bool = False):
           """Clean up an interrupted timelapse."""
           async with self.session_factory() as session:
               job = await session.get(Job, job_id)
               if not job:
                   return

               if delete_frames and job.timelapse_dir:
                   dir_path = Path(job.timelapse_dir)
                   if dir_path.exists():
                       import shutil
                       shutil.rmtree(dir_path)
                       logger.info("timelapse_frames_deleted", path=str(dir_path))

               job.status = "failed"
               job.error_message = "Interrupted and cleaned up"
               await session.commit()
   ```

3. **Add API endpoints for recovery**
   ```python
   # app/api/routes/jobs.py

   @router.get("/interrupted")
   async def get_interrupted_jobs(session: AsyncSession = Depends(get_session)):
       """Get list of interrupted jobs that can be resumed."""
       recovery = TimelapseRecovery(session)
       interrupted = await recovery.find_interrupted()
       return ResponseWrapper(data=interrupted)

   @router.post("/{job_id}/resume")
   async def resume_job(job_id: int, session: AsyncSession = Depends(get_session)):
       """Resume an interrupted timelapse."""
       recovery = TimelapseRecovery(session)
       success = await recovery.resume_timelapse(job_id)
       if not success:
           raise HTTPException(status_code=400, detail="Cannot resume job")
       return {"status": "resumed"}

   @router.post("/{job_id}/cleanup")
   async def cleanup_job(
       job_id: int,
       delete_frames: bool = False,
       session: AsyncSession = Depends(get_session),
   ):
       """Clean up an interrupted timelapse."""
       recovery = TimelapseRecovery(session)
       await recovery.cleanup_timelapse(job_id, delete_frames)
       return {"status": "cleaned"}
   ```

4. **Check for interrupted jobs on startup**
   ```python
   # app/main.py

   @app.on_event("startup")
   async def startup():
       # ... existing startup ...

       # Check for interrupted timelapses
       recovery = TimelapseRecovery(session_factory)
       interrupted = await recovery.find_interrupted()
       if interrupted:
           logger.warning(
               "interrupted_timelapses_found",
               count=len(interrupted),
               job_ids=[j["job_id"] for j in interrupted],
           )
   ```

#### Acceptance Criteria
- [ ] Timelapse state persisted to database
- [ ] Interrupted timelapses detected on startup
- [ ] Resume continues from last frame
- [ ] Cleanup removes frames and updates status

---

### 4.4 WebSocket Error Handling
**Priority**: MEDIUM
**Addresses**: Gap 2.4

#### Goal
Robust WebSocket connection management on backend.

#### Tasks

1. **Create WebSocket manager**
   ```python
   # app/services/websocket/manager.py
   from fastapi import WebSocket
   from typing import Set
   import asyncio
   import structlog
   import json

   logger = structlog.get_logger(__name__)

   class WebSocketManager:
       def __init__(self):
           self._clients: Set[WebSocket] = set()
           self._lock = asyncio.Lock()

       async def connect(self, websocket: WebSocket):
           """Accept and register a new WebSocket connection."""
           await websocket.accept()
           async with self._lock:
               self._clients.add(websocket)
           logger.info("ws_client_connected", total=len(self._clients))

       async def disconnect(self, websocket: WebSocket):
           """Remove a WebSocket connection."""
           async with self._lock:
               self._clients.discard(websocket)
           logger.info("ws_client_disconnected", total=len(self._clients))

       async def broadcast(self, message: dict):
           """Broadcast message to all connected clients."""
           if not self._clients:
               return

           data = json.dumps(message)
           disconnected = []

           async with self._lock:
               for client in self._clients:
                   try:
                       await asyncio.wait_for(
                           client.send_text(data),
                           timeout=5.0,
                       )
                   except asyncio.TimeoutError:
                       logger.warning("ws_send_timeout")
                       disconnected.append(client)
                   except Exception as e:
                       logger.warning("ws_send_failed", error=str(e))
                       disconnected.append(client)

           # Clean up failed connections
           for client in disconnected:
               await self.disconnect(client)

       async def send_to(self, websocket: WebSocket, message: dict):
           """Send message to specific client."""
           try:
               await websocket.send_json(message)
           except Exception as e:
               logger.warning("ws_send_to_failed", error=str(e))
               await self.disconnect(websocket)

       @property
       def client_count(self) -> int:
           return len(self._clients)

   # Global instance
   ws_manager = WebSocketManager()
   ```

2. **Create WebSocket endpoint**
   ```python
   # app/api/routes/websocket.py
   from fastapi import APIRouter, WebSocket, WebSocketDisconnect
   from app.services.websocket.manager import ws_manager

   router = APIRouter()

   @router.websocket("/ws")
   async def websocket_endpoint(websocket: WebSocket):
       await ws_manager.connect(websocket)
       try:
           while True:
               # Keep connection alive, handle any client messages
               data = await websocket.receive_text()
               # Could handle client-initiated messages here
       except WebSocketDisconnect:
           pass
       finally:
           await ws_manager.disconnect(websocket)
   ```

3. **Broadcast stats periodically**
   ```python
   # app/services/stats_broadcaster.py
   import asyncio
   from app.services.websocket.manager import ws_manager
   from app.services.system.stats import get_system_stats

   async def stats_broadcast_loop():
       """Periodically broadcast system stats."""
       while True:
           if ws_manager.client_count > 0:
               stats = await get_system_stats()
               await ws_manager.broadcast({
                   "type": "stats_update",
                   **stats,
               })
           await asyncio.sleep(2)  # Every 2 seconds
   ```

#### Acceptance Criteria
- [ ] Client connections tracked
- [ ] Failed sends don't crash server
- [ ] Disconnected clients cleaned up
- [ ] Broadcast only when clients connected

---

## Phase 5: Integration Fixes

### 5.1 Camera Status Synchronization
**Priority**: HIGH
**Addresses**: Gap 5.3

#### Goal
Keep camera status synchronized across all UI components.

#### Tasks

1. **Emit status events from camera service**
   ```python
   # app/services/camera/events.py
   from app.services.websocket.manager import ws_manager
   from datetime import datetime

   async def emit_camera_status(
       camera_id: int,
       status: str,  # "online", "offline", "recording", "error"
       message: str = None,
   ):
       await ws_manager.broadcast({
           "type": "camera_event",
           "camera_id": camera_id,
           "event": status,
           "message": message,
           "timestamp": datetime.utcnow().isoformat(),
       })
   ```

2. **Create camera status hook in frontend**
   ```typescript
   // frontend/src/api/hooks/useCameraStatus.ts
   import { useEffect } from 'react';
   import { useQueryClient } from '@tanstack/react-query';
   import { wsClient } from '@/api/websocket';
   import { isCameraEvent } from '@/api/websocket.types';

   export function useCameraStatusSync() {
     const queryClient = useQueryClient();

     useEffect(() => {
       const unsubscribe = wsClient.subscribe('camera_event', (event) => {
         // Invalidate camera queries to trigger refetch
         queryClient.invalidateQueries({ queryKey: ['cameras'] });
         queryClient.invalidateQueries({
           queryKey: ['camera', event.camera_id]
         });
       });

       return unsubscribe;
     }, [queryClient]);
   }
   ```

3. **Use in App component**
   ```typescript
   // frontend/src/App.tsx
   import { useCameraStatusSync } from '@/api/hooks/useCameraStatus';

   function App() {
     useCameraStatusSync();

     return (
       // ... rest of app
     );
   }
   ```

#### Acceptance Criteria
- [ ] Status changes emitted via WebSocket
- [ ] Frontend invalidates queries on status change
- [ ] All components show consistent status

---

### 5.2 Job System Integration
**Priority**: HIGH
**Addresses**: Gap 5.4

#### Goal
Integrate job lifecycle with recording and timelapse services.

#### Tasks

1. **Create job service**
   ```python
   # app/services/jobs/service.py
   from datetime import datetime
   from typing import Optional
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select

   from app.db.models import Job
   from app.services.websocket.manager import ws_manager

   class JobService:
       def __init__(self, session: AsyncSession):
           self.session = session

       async def create_job(
           self,
           camera_id: int,
           job_type: str,
           config: dict = None,
       ) -> Job:
           """Create a new job."""
           job = Job(
               camera_id=camera_id,
               job_type=job_type,
               status="pending",
               timelapse_config=config if job_type == "timelapse" else None,
               started_at=datetime.utcnow(),
           )
           self.session.add(job)
           await self.session.commit()
           await self.session.refresh(job)

           await self._emit_update(job)
           return job

       async def update_status(
           self,
           job_id: int,
           status: str,
           progress: float = None,
           error: str = None,
       ):
           """Update job status."""
           job = await self.session.get(Job, job_id)
           if not job:
               return

           job.status = status
           if progress is not None:
               job.timelapse_progress = int(progress)
           if error:
               job.error_message = error
           if status in ["completed", "failed"]:
               job.completed_at = datetime.utcnow()

           await self.session.commit()
           await self._emit_update(job)

       async def _emit_update(self, job: Job):
           """Emit WebSocket update for job."""
           total_frames = None
           if job.timelapse_config:
               total_frames = job.timelapse_config.get("total_frames")

           progress = None
           if total_frames and job.timelapse_progress:
               progress = (job.timelapse_progress / total_frames) * 100

           await ws_manager.broadcast({
               "type": "job_update",
               "job_id": job.id,
               "camera_id": job.camera_id,
               "job_type": job.job_type,
               "status": job.status,
               "progress": progress,
               "timestamp": datetime.utcnow().isoformat(),
           })

       async def get_active_jobs(self, camera_id: int = None) -> list[Job]:
           """Get active jobs, optionally filtered by camera."""
           query = select(Job).where(Job.status.in_(["pending", "running"]))
           if camera_id:
               query = query.where(Job.camera_id == camera_id)
           result = await self.session.execute(query)
           return list(result.scalars())
   ```

2. **Integrate with recording service**
   ```python
   # app/services/camera/recording.py
   from app.services.jobs.service import JobService

   class RecordingService:
       async def start_recording(self, camera_id: int, session: AsyncSession, ...):
           job_service = JobService(session)

           # Create job
           job = await job_service.create_job(camera_id, "recording")
           await job_service.update_status(job.id, "running")

           try:
               # ... start recording ...
               return {"job_id": job.id, "status": "recording"}
           except Exception as e:
               await job_service.update_status(job.id, "failed", error=str(e))
               raise

       async def stop_recording(self, camera_id: int, session: AsyncSession):
           # ... stop recording ...

           # Find and complete job
           job_service = JobService(session)
           jobs = await job_service.get_active_jobs(camera_id)
           for job in jobs:
               if job.job_type == "recording":
                   await job_service.update_status(job.id, "completed")
   ```

3. **Add active jobs to ObservationSummary**
   ```typescript
   // frontend/src/pages/Home/ObservationSummary.tsx
   import { useQuery } from '@tanstack/react-query';
   import { api } from '@/api/client';

   export function ObservationSummary() {
     const { data: jobs } = useQuery({
       queryKey: ['jobs', 'active'],
       queryFn: () => api.get('/api/v1/jobs?status=running'),
       refetchInterval: 5000,
     });

     return (
       <div className={styles.summary}>
         <Card>
           <h3>Active Jobs</h3>
           {jobs?.length ? (
             <ul className={styles.jobs}>
               {jobs.map((job) => (
                 <li key={job.id}>
                   Camera {job.camera_id}: {job.job_type}
                   {job.progress && ` (${job.progress.toFixed(0)}%)`}
                 </li>
               ))}
             </ul>
           ) : (
             <p className={styles.empty}>No active jobs</p>
           )}
         </Card>
       </div>
     );
   }
   ```

#### Acceptance Criteria
- [ ] Jobs created when recording/timelapse starts
- [ ] Job status updated on progress/completion
- [ ] WebSocket events emitted for job updates
- [ ] Active jobs shown in dashboard

---

### 5.3 Basic Notification System
**Priority**: HIGH
**Addresses**: Gap 7.1

#### Goal
Browser notifications for important events.

#### Tasks

1. **Create notification service in frontend**
   ```typescript
   // frontend/src/services/notifications.ts

   class NotificationService {
     private permission: NotificationPermission = 'default';

     async requestPermission(): Promise<boolean> {
       if (!('Notification' in window)) {
         console.warn('Notifications not supported');
         return false;
       }

       this.permission = await Notification.requestPermission();
       return this.permission === 'granted';
     }

     notify(title: string, options?: NotificationOptions) {
       if (this.permission !== 'granted') return;

       new Notification(title, {
         icon: '/favicon.ico',
         ...options,
       });
     }

     notifyRecordingComplete(cameraName: string, duration: string) {
       this.notify('Recording Complete', {
         body: `${cameraName} - ${duration}`,
         tag: 'recording-complete',
       });
     }

     notifyTimelapseComplete(cameraName: string, frames: number) {
       this.notify('Timelapse Complete', {
         body: `${cameraName} - ${frames} frames captured`,
         tag: 'timelapse-complete',
       });
     }

     notifyLowDiskSpace(freeGB: number) {
       this.notify('Low Disk Space Warning', {
         body: `Only ${freeGB.toFixed(1)} GB remaining`,
         tag: 'disk-warning',
       });
     }

     notifyCameraOffline(cameraName: string) {
       this.notify('Camera Offline', {
         body: `${cameraName} is no longer responding`,
         tag: `camera-offline`,
       });
     }
   }

   export const notifications = new NotificationService();
   ```

2. **Request permission on app load**
   ```typescript
   // frontend/src/App.tsx
   import { useEffect } from 'react';
   import { notifications } from '@/services/notifications';

   function App() {
     useEffect(() => {
       // Request notification permission
       notifications.requestPermission();
     }, []);

     // ...
   }
   ```

3. **Hook into WebSocket events**
   ```typescript
   // frontend/src/hooks/useNotifications.ts
   import { useEffect } from 'react';
   import { wsClient } from '@/api/websocket';
   import { notifications } from '@/services/notifications';
   import { useCameras } from '@/api/hooks/useCameras';

   export function useNotificationHandler() {
     const { data: cameras } = useCameras();

     useEffect(() => {
       const unsubJob = wsClient.subscribe('job_update', (event) => {
         if (event.status === 'completed') {
           const camera = cameras?.find(c => c.id === event.camera_id);
           const cameraName = camera?.name || `Camera ${event.camera_id}`;

           if (event.job_type === 'recording') {
             notifications.notifyRecordingComplete(cameraName, 'Recording saved');
           } else if (event.job_type === 'timelapse') {
             notifications.notifyTimelapseComplete(cameraName, event.progress || 0);
           }
         }
       });

       const unsubCamera = wsClient.subscribe('camera_event', (event) => {
         if (event.event === 'offline') {
           const camera = cameras?.find(c => c.id === event.camera_id);
           notifications.notifyCameraOffline(camera?.name || `Camera ${event.camera_id}`);
         }
       });

       const unsubStats = wsClient.subscribe('stats_update', (event) => {
         if (event.disk_free_gb < 1) {
           notifications.notifyLowDiskSpace(event.disk_free_gb);
         }
       });

       return () => {
         unsubJob();
         unsubCamera();
         unsubStats();
       };
     }, [cameras]);
   }
   ```

4. **Add notification settings to UI**
   ```typescript
   // frontend/src/pages/System/NotificationSettings.tsx
   import { useState, useEffect } from 'react';
   import { notifications } from '@/services/notifications';
   import { Button } from '@/components/common/Button';
   import { Card } from '@/components/common/Card';

   export function NotificationSettings() {
     const [permission, setPermission] = useState(Notification.permission);

     const handleEnable = async () => {
       const granted = await notifications.requestPermission();
       setPermission(granted ? 'granted' : 'denied');
     };

     return (
       <Card>
         <h3>Browser Notifications</h3>
         {permission === 'granted' ? (
           <p>Notifications enabled</p>
         ) : permission === 'denied' ? (
           <p>Notifications blocked. Enable in browser settings.</p>
         ) : (
           <Button onClick={handleEnable}>Enable Notifications</Button>
         )}
       </Card>
     );
   }
   ```

#### Acceptance Criteria
- [ ] Permission requested on first load
- [ ] Notifications for recording/timelapse complete
- [ ] Notifications for camera offline
- [ ] Notifications for low disk space
- [ ] Settings page to manage notifications

---

## Phase 6: Testing & Documentation

### 6.1 E2E Test Framework Setup
**Priority**: HIGH
**Addresses**: Gap 4.1

#### Goal
Set up end-to-end testing infrastructure.

#### Tasks

1. **Install Playwright**
   ```bash
   cd frontend
   npm install -D @playwright/test
   npx playwright install
   ```

2. **Create Playwright config**
   ```typescript
   // frontend/playwright.config.ts
   import { defineConfig, devices } from '@playwright/test';

   export default defineConfig({
     testDir: './e2e',
     fullyParallel: true,
     forbidOnly: !!process.env.CI,
     retries: process.env.CI ? 2 : 0,
     workers: process.env.CI ? 1 : undefined,
     reporter: 'html',
     use: {
       baseURL: 'http://localhost:5173',
       trace: 'on-first-retry',
     },
     projects: [
       {
         name: 'chromium',
         use: { ...devices['Desktop Chrome'] },
       },
     ],
     webServer: {
       command: 'npm run dev',
       url: 'http://localhost:5173',
       reuseExistingServer: !process.env.CI,
     },
   });
   ```

3. **Create example E2E tests**
   ```typescript
   // frontend/e2e/home.spec.ts
   import { test, expect } from '@playwright/test';

   test.describe('Home Dashboard', () => {
     test('shows camera cards', async ({ page }) => {
       await page.goto('/');

       // Wait for cameras section
       await expect(page.getByRole('heading', { name: 'Cameras' })).toBeVisible();

       // Should show at least empty state or camera cards
       const cameras = page.locator('[data-testid="camera-card"]');
       const emptyState = page.getByText('No cameras configured');

       await expect(cameras.or(emptyState)).toBeVisible();
     });

     test('shows system stats', async ({ page }) => {
       await page.goto('/');

       await expect(page.getByRole('heading', { name: 'System' })).toBeVisible();
       await expect(page.getByText(/CPU Usage/)).toBeVisible();
       await expect(page.getByText(/RAM Usage/)).toBeVisible();
     });
   });

   // frontend/e2e/camera.spec.ts
   import { test, expect } from '@playwright/test';

   test.describe('Camera View', () => {
     test.beforeEach(async ({ page }) => {
       // Assumes camera ID 1 exists - mock in CI
       await page.goto('/camera/1');
     });

     test('shows live preview', async ({ page }) => {
       await expect(page.getByText('LIVE').or(page.getByText('Camera Offline'))).toBeVisible();
     });

     test('capture button works', async ({ page }) => {
       const captureTab = page.getByRole('tab', { name: 'Capture' });
       await captureTab.click();

       const captureBtn = page.getByRole('button', { name: /Take Photo/ });
       await expect(captureBtn).toBeVisible();
     });
   });
   ```

4. **Add npm scripts**
   ```json
   // frontend/package.json
   {
     "scripts": {
       "test:e2e": "playwright test",
       "test:e2e:ui": "playwright test --ui"
     }
   }
   ```

#### Acceptance Criteria
- [ ] Playwright installed and configured
- [ ] Basic E2E tests for dashboard
- [ ] E2E tests for camera view
- [ ] Tests run in CI pipeline

---

### 6.2 Load Testing Setup
**Priority**: HIGH
**Addresses**: Gap 4.2

#### Goal
Create load testing scripts for Pi resource validation.

#### Tasks

1. **Install locust**
   ```bash
   pip install locust
   ```

2. **Create load test file**
   ```python
   # tests/load/locustfile.py
   from locust import HttpUser, task, between

   class TimeMachineUser(HttpUser):
       wait_time = between(1, 3)

       @task(10)
       def get_health(self):
           self.client.get("/api/v1/health")

       @task(5)
       def get_stats(self):
           self.client.get("/api/v1/health/stats")

       @task(3)
       def get_cameras(self):
           self.client.get("/api/v1/cameras")

       @task(1)
       def capture_still(self):
           # Only if camera exists
           self.client.post("/api/v1/cameras/1/capture", json={"quality": 85})

   class StreamViewer(HttpUser):
       """Simulates users watching MJPEG streams."""
       wait_time = between(30, 60)  # Stay connected for 30-60s

       @task
       def watch_stream(self):
           with self.client.get(
               "/api/v1/cameras/1/stream",
               stream=True,
               catch_response=True,
           ) as response:
               # Read for a bit then disconnect
               for chunk in response.iter_content(chunk_size=1024):
                   if len(chunk) > 0:
                       break
               response.success()
   ```

3. **Create load test script**
   ```bash
   # scripts/load-test.sh
   #!/bin/bash

   HOST="${1:-http://localhost:8000}"
   USERS="${2:-10}"
   SPAWN_RATE="${3:-2}"
   DURATION="${4:-60}"

   echo "Running load test against $HOST"
   echo "Users: $USERS, Spawn rate: $SPAWN_RATE/s, Duration: ${DURATION}s"

   locust -f tests/load/locustfile.py \
     --host "$HOST" \
     --users "$USERS" \
     --spawn-rate "$SPAWN_RATE" \
     --run-time "${DURATION}s" \
     --headless \
     --html "load_test_report.html"

   echo "Report saved to load_test_report.html"
   ```

4. **Document Pi-specific test procedure**
   ```markdown
   # tests/load/README.md

   ## Load Testing on Raspberry Pi

   ### Recommended Test Levels

   | Test | Users | Duration | Expected |
   |------|-------|----------|----------|
   | Smoke | 2 | 30s | No errors |
   | Light | 5 | 60s | <200ms avg |
   | Normal | 10 | 120s | <500ms avg |
   | Stress | 20 | 180s | Find limits |

   ### Running Tests

   ```bash
   # From development machine against Pi
   ./scripts/load-test.sh http://raspberrypi.local:8000 10 2 60
   ```

   ### Monitoring During Tests

   SSH into Pi and run:
   ```bash
   watch -n 1 'vcgencmd measure_temp && free -m && uptime'
   ```

   ### Success Criteria

   - CPU stays < 80% average
   - Memory stays < 700MB used
   - Temperature stays < 70°C
   - No 5xx errors
   - 95th percentile < 1s
   ```

#### Acceptance Criteria
- [ ] Locust installed and configured
- [ ] Load test scenarios defined
- [ ] Pi-specific testing documented
- [ ] Success criteria defined

---

### 6.3 User Documentation
**Priority**: MEDIUM
**Addresses**: Gap 6.1

#### Goal
Create user-facing documentation for setup and usage.

#### Tasks

1. **Create docs directory structure**
   ```
   docs/
   ├── getting-started.md
   ├── configuration.md
   ├── cameras.md
   ├── storage.md
   └── troubleshooting.md
   ```

2. **Write getting started guide**
   ```markdown
   # docs/getting-started.md

   # Getting Started with TimeMachine

   ## Requirements

   - Raspberry Pi 3B+ or newer (1GB+ RAM)
   - Raspberry Pi OS (Bullseye or newer)
   - CSI camera (Pi Camera Module) and/or USB webcam
   - Storage: SD card + optional USB drive for recordings

   ## Quick Install

   1. Download the latest release
   2. Run the installer:
      ```bash
      sudo ./scripts/install.sh
      ```
   3. Configure your settings:
      ```bash
      sudo nano /etc/timemachine/timemachine.env
      ```
   4. Start the service:
      ```bash
      sudo systemctl start timemachine
      ```
   5. Open http://raspberrypi.local in your browser

   ## First Steps

   1. **Add a Camera**: Go to System → Cameras → Add Camera
   2. **Test Preview**: Click on your camera tab to see the live feed
   3. **Take a Photo**: Use the Capture tab to take a still image
   4. **Record Video**: Use the Record tab to start recording

   ## Need Help?

   See [Troubleshooting](troubleshooting.md) for common issues.
   ```

3. **Write troubleshooting guide**
   ```markdown
   # docs/troubleshooting.md

   # Troubleshooting

   ## Camera Not Detected

   ### CSI Camera
   1. Check cable connection (blue side facing Ethernet port)
   2. Enable camera interface: `sudo raspi-config` → Interface Options → Camera
   3. Verify detection: `libcamera-hello --list-cameras`

   ### USB Camera
   1. Check connection: `ls /dev/video*`
   2. Check permissions: User must be in `video` group
   3. Try different USB port

   ## Stream Not Loading

   - **Blank screen**: Camera may be in use by another process
   - **Error message**: Check if service is running: `systemctl status timemachine`
   - **Slow/choppy**: Reduce resolution or FPS in camera settings

   ## Recording Fails

   - **507 Error**: Not enough disk space
   - **409 Error**: Already recording (only 1 recording at a time)
   - **Camera busy**: Stop any running preview first

   ## Service Won't Start

   1. Check logs: `journalctl -u timemachine -n 50`
   2. Verify permissions: `ls -la /var/lib/timemachine`
   3. Check config: `cat /etc/timemachine/timemachine.env`

   ## Performance Issues

   - **High CPU**: Reduce camera resolution/FPS
   - **High Memory**: Close unused browser tabs
   - **Throttling**: Check power supply (use official 5V/3A adapter)
     - Run: `vcgencmd get_throttled`
   ```

#### Acceptance Criteria
- [ ] Getting started guide written
- [ ] Configuration documentation written
- [ ] Troubleshooting guide written
- [ ] Docs linked from README

---

### 6.4 API Documentation Enhancement
**Priority**: MEDIUM
**Addresses**: Gap 6.2

#### Goal
Enhance auto-generated API documentation.

#### Tasks

1. **Add detailed descriptions to endpoints**
   ```python
   # app/api/routes/cameras.py

   @router.get(
       "",
       response_model=ResponseWrapper[list[CameraResponse]],
       summary="List all cameras",
       description="""
       Returns a list of all configured cameras with their current status.

       The status field indicates:
       - `online`: Camera is connected and available
       - `offline`: Camera is not responding
       - `recording`: Camera is currently recording
       - `error`: Camera encountered an error
       """,
   )
   async def list_cameras():
       # ...

   @router.post(
       "/{camera_id}/capture",
       response_model=ResponseWrapper[CaptureResponse],
       summary="Capture a still image",
       description="""
       Captures a single still image from the specified camera.

       **Rate limit**: 1 request per second

       **Errors**:
       - 404: Camera not found
       - 409: Camera is busy
       - 507: Insufficient disk space
       """,
       responses={
           429: {"description": "Rate limit exceeded"},
           507: {"description": "Insufficient storage"},
       },
   )
   async def capture_still():
       # ...
   ```

2. **Add example values to schemas**
   ```python
   # app/models/schemas/camera.py
   from pydantic import BaseModel, Field

   class CameraCreate(BaseModel):
       name: str = Field(
           ...,
           description="Human-readable camera name",
           example="Front Yard Camera",
       )
       device_path: str = Field(
           ...,
           description="Device path or CSI camera index",
           example="/dev/video0",
       )
       resolution: str = Field(
           default="1920x1080",
           description="Video resolution",
           example="1920x1080",
       )
       fps: int = Field(
           default=30,
           description="Frames per second",
           ge=1,
           le=60,
           example=30,
       )
   ```

3. **Add tags for organization**
   ```python
   # app/main.py

   app = FastAPI(
       title="TimeMachine API",
       description="""
       ## Observation Chamber Control System

       TimeMachine provides a web interface for managing cameras on a Raspberry Pi.

       ### Features
       - Multiple camera support (CSI and USB)
       - Live preview streaming
       - Video recording with H.264 encoding
       - Timelapse capture
       - Storage management

       ### Authentication
       Authentication is optional and can be enabled in configuration.
       When enabled, use HTTP Basic Auth.
       """,
       version="1.0.0",
       openapi_tags=[
           {"name": "cameras", "description": "Camera management and operations"},
           {"name": "storage", "description": "File storage and management"},
           {"name": "system", "description": "System health and configuration"},
           {"name": "temperature", "description": "Temperature control (stub)"},
       ],
   )
   ```

#### Acceptance Criteria
- [ ] All endpoints have descriptions
- [ ] Error responses documented
- [ ] Example values in schemas
- [ ] Tags organize endpoints logically

---

## Summary

This remediation plan addresses all 23 gaps identified in the Gap Analysis Report:

| Phase | Items | Priority Coverage |
|-------|-------|-------------------|
| 1. Foundation | 4 | 2 CRITICAL, 2 HIGH |
| 2. Security | 4 | 1 CRITICAL, 2 HIGH, 1 MEDIUM |
| 3. Resources | 4 | 2 CRITICAL, 2 HIGH |
| 4. Recovery | 4 | 1 CRITICAL, 2 HIGH, 1 MEDIUM |
| 5. Integration | 3 | 1 CRITICAL, 2 HIGH |
| 6. Testing/Docs | 4 | 2 HIGH, 2 MEDIUM |

**Total Estimated Duration**: 3-4 days

**Recommended Approach**:
1. Complete Phases 1-2 before starting main implementation
2. Integrate Phases 3-4 into respective main plans (03-camera-system, etc.)
3. Complete Phases 5-6 after main implementation

---

## File Lifecycle

- Current: `.ready.md`
- When starting: Rename to `.in_progress.md`
- When complete: Move to `.claude/plans/completed/00-gap-remediation.md`

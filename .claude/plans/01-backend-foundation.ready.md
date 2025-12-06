# Backend Foundation - Plan

## Overview

Establish the FastAPI backend scaffold with health/stats endpoints, structured logging, error handling, and development tooling. This is the foundation upon which all other backend services will be built.

**Dependencies**: None
**Estimated Duration**: 2-3 days

---

## Phase 1: Project Scaffold

### Goal
Create the directory structure and basic FastAPI application factory.

### Tasks

1. **Create directory structure**
   ```
   backend/
   ├── app/
   │   ├── __init__.py
   │   ├── main.py              # FastAPI app factory
   │   ├── config.py            # Pydantic Settings
   │   ├── api/
   │   │   ├── __init__.py
   │   │   ├── deps.py          # Dependency injection
   │   │   └── routes/
   │   │       ├── __init__.py
   │   │       ├── health.py
   │   │       └── stats.py
   │   ├── core/
   │   │   ├── __init__.py
   │   │   ├── logging.py
   │   │   ├── exceptions.py
   │   │   └── middleware.py
   │   ├── models/
   │   │   ├── __init__.py
   │   │   └── schemas/
   │   │       ├── __init__.py
   │   │       ├── common.py    # ResponseWrapper, Meta
   │   │       ├── health.py
   │   │       └── stats.py
   │   ├── services/
   │   │   ├── __init__.py
   │   │   └── stats.py
   │   └── utils/
   │       └── __init__.py
   ├── tests/
   │   ├── __init__.py
   │   ├── conftest.py
   │   ├── unit/
   │   └── integration/
   ├── requirements.txt
   ├── requirements-dev.txt
   ├── pyproject.toml
   ├── Makefile
   └── .env.example
   ```

2. **Create `app/main.py` - Application Factory**
   ```python
   from fastapi import FastAPI
   from contextlib import asynccontextmanager
   from app.config import settings
   from app.core.logging import setup_logging
   from app.core.middleware import setup_middleware
   from app.api.routes import health, stats

   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # Startup
       setup_logging()
       yield
       # Shutdown

   def create_app() -> FastAPI:
       app = FastAPI(
           title="TimeMachine",
           description="Observation Chamber Controller",
           version="0.1.0",
           lifespan=lifespan,
       )
       setup_middleware(app)
       app.include_router(health.router, prefix="/api/v1", tags=["health"])
       app.include_router(stats.router, prefix="/api/v1", tags=["stats"])
       return app

   app = create_app()
   ```

3. **Create `app/config.py` - Pydantic Settings**
   ```python
   from pydantic_settings import BaseSettings
   from functools import lru_cache

   class Settings(BaseSettings):
       env: str = "development"
       log_level: str = "INFO"
       host: str = "127.0.0.1"
       port: int = 8000
       db_path: str = "./data/timemachine.db"
       media_path: str = "./data/media"

       class Config:
           env_prefix = "TIMEMACHINE_"
           env_file = ".env"

   @lru_cache
   def get_settings() -> Settings:
       return Settings()

   settings = get_settings()
   ```

4. **Create `requirements.txt`**
   ```
   fastapi>=0.104.0
   uvicorn[standard]>=0.24.0
   pydantic>=2.5.0
   pydantic-settings>=2.1.0
   psutil>=5.9.0
   python-multipart>=0.0.6
   structlog>=23.2.0
   ```

5. **Create `requirements-dev.txt`**
   ```
   -r requirements.txt
   pytest>=7.4.0
   pytest-asyncio>=0.21.0
   pytest-cov>=4.1.0
   httpx>=0.25.0
   ruff>=0.1.6
   black>=23.11.0
   mypy>=1.7.0
   pre-commit>=3.6.0
   ```

6. **Create `Makefile`**
   ```makefile
   .PHONY: install dev run test lint format type-check clean

   install:
   	pip install -r requirements.txt

   dev:
   	pip install -r requirements-dev.txt
   	pre-commit install

   run:
   	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

   test:
   	pytest tests/ -v --cov=app --cov-report=term-missing

   lint:
   	ruff check app/ tests/

   format:
   	black app/ tests/
   	ruff check --fix app/ tests/

   type-check:
   	mypy app/

   clean:
   	find . -type d -name __pycache__ -exec rm -rf {} +
   	find . -type f -name "*.pyc" -delete
   ```

### Acceptance Criteria
- [ ] Directory structure created
- [ ] `make install` succeeds
- [ ] `make run` starts the server
- [ ] FastAPI Swagger UI accessible at `/docs`

---

## Phase 2: Health & Stats Endpoints

### Goal
Implement health check and system stats endpoints with proper response models.

### Tasks

1. **Create `app/models/schemas/common.py`**
   ```python
   from pydantic import BaseModel
   from datetime import datetime
   from typing import TypeVar, Generic, Optional

   T = TypeVar("T")

   class Meta(BaseModel):
       timestamp: datetime
       request_id: Optional[str] = None

   class ResponseWrapper(BaseModel, Generic[T]):
       data: T
       meta: Meta
   ```

2. **Create `app/models/schemas/health.py`**
   ```python
   from pydantic import BaseModel

   class HealthResponse(BaseModel):
       status: str
       version: str
       uptime_seconds: float
   ```

3. **Create `app/models/schemas/stats.py`**
   ```python
   from pydantic import BaseModel
   from typing import Optional

   class DiskStats(BaseModel):
       total_gb: float
       used_gb: float
       free_gb: float
       percent_used: float

   class StatsResponse(BaseModel):
       cpu_percent: float
       memory_percent: float
       memory_used_mb: float
       memory_total_mb: float
       disk: DiskStats
       temperature_celsius: Optional[float] = None
   ```

4. **Create `app/services/stats.py`**
   ```python
   import psutil
   import asyncio
   from concurrent.futures import ThreadPoolExecutor
   from app.models.schemas.stats import StatsResponse, DiskStats

   _executor = ThreadPoolExecutor(max_workers=2)

   def _get_cpu_temp() -> float | None:
       try:
           temps = psutil.sensors_temperatures()
           if "cpu_thermal" in temps:
               return temps["cpu_thermal"][0].current
       except Exception:
           pass
       return None

   def _collect_stats_sync() -> StatsResponse:
       cpu = psutil.cpu_percent(interval=0.1)
       mem = psutil.virtual_memory()
       disk = psutil.disk_usage("/")
       temp = _get_cpu_temp()

       return StatsResponse(
           cpu_percent=cpu,
           memory_percent=mem.percent,
           memory_used_mb=mem.used / (1024 * 1024),
           memory_total_mb=mem.total / (1024 * 1024),
           disk=DiskStats(
               total_gb=disk.total / (1024**3),
               used_gb=disk.used / (1024**3),
               free_gb=disk.free / (1024**3),
               percent_used=disk.percent,
           ),
           temperature_celsius=temp,
       )

   async def collect_stats() -> StatsResponse:
       loop = asyncio.get_event_loop()
       return await loop.run_in_executor(_executor, _collect_stats_sync)
   ```

5. **Create `app/api/routes/health.py`**
   ```python
   from fastapi import APIRouter
   from datetime import datetime
   from app.models.schemas.health import HealthResponse
   from app.models.schemas.common import ResponseWrapper, Meta

   router = APIRouter()
   _start_time = datetime.utcnow()

   @router.get("/health", response_model=ResponseWrapper[HealthResponse])
   async def health_check():
       uptime = (datetime.utcnow() - _start_time).total_seconds()
       return ResponseWrapper(
           data=HealthResponse(
               status="healthy",
               version="0.1.0",
               uptime_seconds=uptime,
           ),
           meta=Meta(timestamp=datetime.utcnow()),
       )
   ```

6. **Create `app/api/routes/stats.py`**
   ```python
   from fastapi import APIRouter
   from datetime import datetime
   from app.services.stats import collect_stats
   from app.models.schemas.stats import StatsResponse
   from app.models.schemas.common import ResponseWrapper, Meta

   router = APIRouter()

   @router.get("/stats", response_model=ResponseWrapper[StatsResponse])
   async def get_stats():
       stats = await collect_stats()
       return ResponseWrapper(
           data=stats,
           meta=Meta(timestamp=datetime.utcnow()),
       )
   ```

### Acceptance Criteria
- [ ] `GET /api/v1/health` returns status, version, uptime
- [ ] `GET /api/v1/stats` returns CPU, RAM, disk stats
- [ ] Temperature included when available (Pi hardware)
- [ ] Response times < 200ms

---

## Phase 3: Logging & Error Handling

### Goal
Implement structured JSON logging with correlation IDs and global exception handling.

### Tasks

1. **Create `app/core/logging.py`**
   ```python
   import structlog
   import logging
   from app.config import settings

   def setup_logging():
       structlog.configure(
           processors=[
               structlog.contextvars.merge_contextvars,
               structlog.processors.add_log_level,
               structlog.processors.TimeStamper(fmt="iso"),
               structlog.processors.JSONRenderer()
               if settings.env == "production"
               else structlog.dev.ConsoleRenderer(),
           ],
           wrapper_class=structlog.make_filtering_bound_logger(
               logging.getLevelName(settings.log_level)
           ),
           context_class=dict,
           logger_factory=structlog.PrintLoggerFactory(),
           cache_logger_on_first_use=True,
       )

   def get_logger(name: str):
       return structlog.get_logger(name)
   ```

2. **Create `app/core/exceptions.py`**
   ```python
   from enum import Enum
   from pydantic import BaseModel
   from typing import Any, Optional

   class ErrorCode(str, Enum):
       VALIDATION_ERROR = "VALIDATION_ERROR"
       NOT_FOUND = "NOT_FOUND"
       INTERNAL_ERROR = "INTERNAL_ERROR"
       CAMERA_ERROR = "CAMERA_ERROR"
       STORAGE_ERROR = "STORAGE_ERROR"

   class ErrorDetail(BaseModel):
       code: ErrorCode
       message: str
       details: Optional[dict[str, Any]] = None

   class AppException(Exception):
       def __init__(
           self,
           code: ErrorCode,
           message: str,
           status_code: int = 500,
           details: dict | None = None,
       ):
           self.code = code
           self.message = message
           self.status_code = status_code
           self.details = details
           super().__init__(message)
   ```

3. **Create `app/core/middleware.py`**
   ```python
   import uuid
   import structlog
   from fastapi import FastAPI, Request
   from fastapi.responses import JSONResponse
   from starlette.middleware.cors import CORSMiddleware
   from datetime import datetime
   from app.core.exceptions import AppException

   def setup_middleware(app: FastAPI):
       # CORS
       app.add_middleware(
           CORSMiddleware,
           allow_origins=["*"],  # Configure for production
           allow_credentials=True,
           allow_methods=["*"],
           allow_headers=["*"],
       )

       @app.middleware("http")
       async def request_id_middleware(request: Request, call_next):
           request_id = str(uuid.uuid4())[:8]
           structlog.contextvars.bind_contextvars(request_id=request_id)
           response = await call_next(request)
           response.headers["X-Request-ID"] = request_id
           return response

       @app.exception_handler(AppException)
       async def app_exception_handler(request: Request, exc: AppException):
           return JSONResponse(
               status_code=exc.status_code,
               content={
                   "error": {
                       "code": exc.code.value,
                       "message": exc.message,
                       "details": exc.details,
                   },
                   "meta": {"timestamp": datetime.utcnow().isoformat()},
               },
           )

       @app.exception_handler(Exception)
       async def global_exception_handler(request: Request, exc: Exception):
           logger = structlog.get_logger()
           logger.exception("Unhandled exception", error=str(exc))
           return JSONResponse(
               status_code=500,
               content={
                   "error": {
                       "code": "INTERNAL_ERROR",
                       "message": "An unexpected error occurred",
                   },
                   "meta": {"timestamp": datetime.utcnow().isoformat()},
               },
           )
   ```

### Acceptance Criteria
- [ ] Logs include request_id for correlation
- [ ] JSON logs in production, console in development
- [ ] AppException returns structured error response
- [ ] Unhandled exceptions return 500 with safe message

---

## Phase 4: Development Tooling

### Goal
Configure linting, formatting, type checking, and pre-commit hooks.

### Tasks

1. **Create `pyproject.toml`**
   ```toml
   [project]
   name = "timemachine"
   version = "0.1.0"
   requires-python = ">=3.11"

   [tool.ruff]
   line-length = 100
   target-version = "py311"
   select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]
   ignore = ["E501"]

   [tool.ruff.isort]
   known-first-party = ["app"]

   [tool.black]
   line-length = 100
   target-version = ["py311"]

   [tool.mypy]
   python_version = "3.11"
   strict = true
   ignore_missing_imports = true

   [tool.pytest.ini_options]
   asyncio_mode = "auto"
   testpaths = ["tests"]
   ```

2. **Create `.pre-commit-config.yaml`**
   ```yaml
   repos:
     - repo: https://github.com/astral-sh/ruff-pre-commit
       rev: v0.1.6
       hooks:
         - id: ruff
           args: [--fix]
     - repo: https://github.com/psf/black
       rev: 23.11.0
       hooks:
         - id: black
     - repo: https://github.com/pre-commit/mirrors-mypy
       rev: v1.7.0
       hooks:
         - id: mypy
           additional_dependencies: [pydantic>=2.0]
   ```

3. **Create `tests/conftest.py`**
   ```python
   import pytest
   from httpx import AsyncClient
   from app.main import app

   @pytest.fixture
   async def client():
       async with AsyncClient(app=app, base_url="http://test") as ac:
           yield ac
   ```

4. **Create `tests/integration/test_health.py`**
   ```python
   import pytest

   @pytest.mark.asyncio
   async def test_health_endpoint(client):
       response = await client.get("/api/v1/health")
       assert response.status_code == 200
       data = response.json()
       assert data["data"]["status"] == "healthy"
       assert "version" in data["data"]
       assert "uptime_seconds" in data["data"]
   ```

5. **Create `.env.example`**
   ```bash
   TIMEMACHINE_ENV=development
   TIMEMACHINE_LOG_LEVEL=DEBUG
   TIMEMACHINE_HOST=127.0.0.1
   TIMEMACHINE_PORT=8000
   TIMEMACHINE_DB_PATH=./data/timemachine.db
   TIMEMACHINE_MEDIA_PATH=./data/media
   ```

### Acceptance Criteria
- [ ] `make lint` passes with no errors
- [ ] `make format` applies consistent formatting
- [ ] `make type-check` passes
- [ ] `make test` runs and passes
- [ ] Pre-commit hooks installed and working

---

## Phase 5: API Foundation

### Goal
Complete the API foundation with proper documentation and CORS configuration.

### Tasks

1. **Update OpenAPI documentation in `app/main.py`**
   ```python
   app = FastAPI(
       title="TimeMachine API",
       description="Observation Chamber Controller for Raspberry Pi",
       version="0.1.0",
       docs_url="/docs",
       redoc_url="/redoc",
       openapi_tags=[
           {"name": "health", "description": "Health and status endpoints"},
           {"name": "stats", "description": "System statistics"},
           {"name": "cameras", "description": "Camera management"},
           {"name": "outputs", "description": "Output configuration"},
           {"name": "temperature", "description": "Temperature control (stub)"},
       ],
   )
   ```

2. **Add request logging middleware**
   ```python
   @app.middleware("http")
   async def log_requests(request: Request, call_next):
       logger = structlog.get_logger()
       logger.info(
           "request_started",
           method=request.method,
           path=request.url.path,
       )
       response = await call_next(request)
       logger.info(
           "request_completed",
           status_code=response.status_code,
       )
       return response
   ```

### Acceptance Criteria
- [ ] OpenAPI docs show all tags
- [ ] Request/response logging works
- [ ] CORS allows frontend origin
- [ ] All endpoints documented

---

## Testing Requirements

| Test | Type | Coverage |
|------|------|----------|
| Health endpoint | Integration | Response structure, status |
| Stats endpoint | Integration | Response structure, data types |
| Stats service | Unit | CPU/RAM/disk collection |
| Exception handler | Unit | Error response format |
| Middleware | Unit | Request ID generation |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| psutil blocking event loop | Use `run_in_executor` for all psutil calls |
| Temperature unavailable | Return `null`, don't crash |
| Memory growth from logging | Use structlog print logger, no buffering |

---

## File Lifecycle

- Current: `.ready.md`
- When starting: Rename to `.in_progress.md`
- When complete: Move to `.claude/plans/completed/01-backend-foundation.md`

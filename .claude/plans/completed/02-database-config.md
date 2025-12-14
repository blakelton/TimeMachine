# Database & Configuration - Plan

## Overview

Implement SQLite database with async SQLAlchemy, schema design, migrations, and repository pattern for data access.

**Dependencies**: 01-backend-foundation
**Estimated Duration**: 1-2 days

---

## Phase 1: SQLite Foundation

### Goal
Set up async SQLite connection with proper session management.

### Tasks

1. **Add dependencies to `requirements.txt`**
   ```
   sqlalchemy[asyncio]>=2.0.23
   aiosqlite>=0.19.0
   ```

2. **Create `app/db/session.py`**
   ```python
   from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
   from sqlalchemy.orm import DeclarativeBase
   from app.config import settings

   class Base(DeclarativeBase):
       pass

   engine = create_async_engine(
       f"sqlite+aiosqlite:///{settings.db_path}",
       echo=settings.env == "development",
       pool_size=5,
       max_overflow=10,
   )

   async_session = async_sessionmaker(
       engine,
       class_=AsyncSession,
       expire_on_commit=False,
   )

   async def get_session() -> AsyncSession:
       async with async_session() as session:
           yield session

   async def init_db():
       async with engine.begin() as conn:
           await conn.run_sync(Base.metadata.create_all)
   ```

3. **Update `app/main.py` lifespan**
   ```python
   from app.db.session import init_db

   @asynccontextmanager
   async def lifespan(app: FastAPI):
       setup_logging()
       await init_db()
       yield
   ```

### Acceptance Criteria
- [ ] Database file created on startup
- [ ] Async sessions work correctly
- [ ] Connection pooling configured

---

## Phase 2: Schema Design

### Goal
Define SQLAlchemy models for all entities.

### SQL Schema

```sql
-- Cameras table
CREATE TABLE cameras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL CHECK (source_type IN ('CSI', 'USB')),
    device_path TEXT NOT NULL,
    resolution TEXT NOT NULL DEFAULT '1920x1080',
    fps INTEGER NOT NULL DEFAULT 30,
    encoder_settings TEXT,  -- JSON
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Output configuration (single row)
CREATE TABLE output_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    recording_path TEXT NOT NULL DEFAULT './recordings',
    stills_path TEXT NOT NULL DEFAULT './stills',
    timelapse_path TEXT NOT NULL DEFAULT './timelapse',
    video_format TEXT NOT NULL DEFAULT 'mp4',
    image_format TEXT NOT NULL DEFAULT 'jpeg',
    image_quality INTEGER NOT NULL DEFAULT 85,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Temperature configuration (stub, single row)
CREATE TABLE temperature_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    enabled INTEGER NOT NULL DEFAULT 0,
    target_temp REAL,
    sensor_pin INTEGER,
    heater_pin INTEGER,
    cooler_pin INTEGER,
    hysteresis REAL DEFAULT 1.0,
    settings TEXT,  -- JSON for future
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Jobs (recordings, timelapses)
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id INTEGER NOT NULL,
    job_type TEXT NOT NULL CHECK (job_type IN ('recording', 'timelapse', 'capture')),
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    file_path TEXT,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    metadata TEXT,  -- JSON
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE
);

-- Events log
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    camera_id INTEGER,
    message TEXT NOT NULL,
    details TEXT,  -- JSON
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE SET NULL
);

-- Schema version tracking
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Tasks

1. **Create `app/models/database.py`**
   ```python
   from sqlalchemy import String, Integer, Boolean, Float, Text, ForeignKey, JSON
   from sqlalchemy.orm import Mapped, mapped_column, relationship
   from datetime import datetime
   from app.db.session import Base

   class Camera(Base):
       __tablename__ = "cameras"

       id: Mapped[int] = mapped_column(primary_key=True)
       name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
       source_type: Mapped[str] = mapped_column(String(10), nullable=False)  # CSI, USB
       device_path: Mapped[str] = mapped_column(String(255), nullable=False)
       resolution: Mapped[str] = mapped_column(String(20), default="1920x1080")
       fps: Mapped[int] = mapped_column(Integer, default=30)
       encoder_settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
       enabled: Mapped[bool] = mapped_column(Boolean, default=True)
       created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
       updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

       jobs: Mapped[list["Job"]] = relationship(back_populates="camera")

   class OutputConfig(Base):
       __tablename__ = "output_config"

       id: Mapped[int] = mapped_column(primary_key=True, default=1)
       recording_path: Mapped[str] = mapped_column(String(500), default="./recordings")
       stills_path: Mapped[str] = mapped_column(String(500), default="./stills")
       timelapse_path: Mapped[str] = mapped_column(String(500), default="./timelapse")
       video_format: Mapped[str] = mapped_column(String(10), default="mp4")
       image_format: Mapped[str] = mapped_column(String(10), default="jpeg")
       image_quality: Mapped[int] = mapped_column(Integer, default=85)
       created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
       updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

   class TemperatureConfig(Base):
       __tablename__ = "temperature_config"

       id: Mapped[int] = mapped_column(primary_key=True, default=1)
       enabled: Mapped[bool] = mapped_column(Boolean, default=False)
       target_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
       sensor_pin: Mapped[int | None] = mapped_column(Integer, nullable=True)
       heater_pin: Mapped[int | None] = mapped_column(Integer, nullable=True)
       cooler_pin: Mapped[int | None] = mapped_column(Integer, nullable=True)
       hysteresis: Mapped[float] = mapped_column(Float, default=1.0)
       settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
       created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
       updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

   class Job(Base):
       __tablename__ = "jobs"

       id: Mapped[int] = mapped_column(primary_key=True)
       camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"))
       job_type: Mapped[str] = mapped_column(String(20), nullable=False)  # recording, timelapse, capture
       status: Mapped[str] = mapped_column(String(20), default="pending")
       file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
       started_at: Mapped[datetime | None] = mapped_column(nullable=True)
       ended_at: Mapped[datetime | None] = mapped_column(nullable=True)
       metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
       created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

       camera: Mapped["Camera"] = relationship(back_populates="jobs")

   class Event(Base):
       __tablename__ = "events"

       id: Mapped[int] = mapped_column(primary_key=True)
       event_type: Mapped[str] = mapped_column(String(50), nullable=False)
       camera_id: Mapped[int | None] = mapped_column(ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
       message: Mapped[str] = mapped_column(Text, nullable=False)
       details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
       timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow)
   ```

### Acceptance Criteria
- [ ] All tables created on startup
- [ ] Relationships work correctly
- [ ] JSON columns serialize/deserialize

---

## Phase 3: Migration System

### Goal
Simple SQL-based migrations for schema changes.

### Tasks

1. **Create `app/db/migrations/__init__.py`**
   ```python
   from pathlib import Path
   from sqlalchemy import text
   from sqlalchemy.ext.asyncio import AsyncConnection
   import structlog

   logger = structlog.get_logger(__name__)

   MIGRATIONS_DIR = Path(__file__).parent / "versions"

   async def get_current_version(conn: AsyncConnection) -> int:
       try:
           result = await conn.execute(text("SELECT MAX(version) FROM schema_version"))
           row = result.fetchone()
           return row[0] if row and row[0] else 0
       except Exception:
           return 0

   async def run_migrations(conn: AsyncConnection):
       current = await get_current_version(conn)
       logger.info("migration_check", current_version=current)

       if not MIGRATIONS_DIR.exists():
           MIGRATIONS_DIR.mkdir(parents=True)
           return

       for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
           version = int(migration_file.stem.split("_")[0])
           if version > current:
               logger.info("applying_migration", version=version, file=migration_file.name)
               sql = migration_file.read_text()
               await conn.execute(text(sql))
               await conn.execute(
                   text("INSERT INTO schema_version (version) VALUES (:v)"),
                   {"v": version},
               )
               await conn.commit()
   ```

2. **Create initial migration `app/db/migrations/versions/001_initial.sql`**
   ```sql
   -- Initial schema (handled by SQLAlchemy create_all, this is a placeholder)
   -- Future migrations go here
   ```

### Acceptance Criteria
- [ ] Migrations run on startup
- [ ] Version tracked in database
- [ ] New migrations apply automatically

---

## Phase 4: Repository Pattern

### Goal
Implement data access layer with clean async repositories.

### Tasks

1. **Create `app/db/repositories/base.py`**
   ```python
   from typing import TypeVar, Generic, Type
   from sqlalchemy import select, delete
   from sqlalchemy.ext.asyncio import AsyncSession

   T = TypeVar("T")

   class BaseRepository(Generic[T]):
       def __init__(self, session: AsyncSession, model: Type[T]):
           self.session = session
           self.model = model

       async def get(self, id: int) -> T | None:
           return await self.session.get(self.model, id)

       async def get_all(self) -> list[T]:
           result = await self.session.execute(select(self.model))
           return list(result.scalars().all())

       async def create(self, obj: T) -> T:
           self.session.add(obj)
           await self.session.commit()
           await self.session.refresh(obj)
           return obj

       async def update(self, obj: T) -> T:
           await self.session.commit()
           await self.session.refresh(obj)
           return obj

       async def delete(self, id: int) -> bool:
           result = await self.session.execute(
               delete(self.model).where(self.model.id == id)
           )
           await self.session.commit()
           return result.rowcount > 0
   ```

2. **Create `app/db/repositories/camera.py`**
   ```python
   from sqlalchemy import select
   from sqlalchemy.ext.asyncio import AsyncSession
   from app.db.repositories.base import BaseRepository
   from app.models.database import Camera

   class CameraRepository(BaseRepository[Camera]):
       def __init__(self, session: AsyncSession):
           super().__init__(session, Camera)

       async def get_by_name(self, name: str) -> Camera | None:
           result = await self.session.execute(
               select(Camera).where(Camera.name == name)
           )
           return result.scalar_one_or_none()

       async def get_enabled(self) -> list[Camera]:
           result = await self.session.execute(
               select(Camera).where(Camera.enabled == True)
           )
           return list(result.scalars().all())
   ```

3. **Create `app/db/repositories/output.py`**
   ```python
   from sqlalchemy.ext.asyncio import AsyncSession
   from app.models.database import OutputConfig

   class OutputRepository:
       def __init__(self, session: AsyncSession):
           self.session = session

       async def get(self) -> OutputConfig:
           config = await self.session.get(OutputConfig, 1)
           if not config:
               config = OutputConfig(id=1)
               self.session.add(config)
               await self.session.commit()
               await self.session.refresh(config)
           return config

       async def update(self, **kwargs) -> OutputConfig:
           config = await self.get()
           for key, value in kwargs.items():
               if hasattr(config, key):
                   setattr(config, key, value)
           await self.session.commit()
           await self.session.refresh(config)
           return config
   ```

### Acceptance Criteria
- [ ] CRUD operations work for all entities
- [ ] Transactions commit properly
- [ ] Single-row configs auto-create

---

## Phase 5: Pydantic Schemas

### Goal
Define request/response schemas for API validation.

### Tasks

1. **Create `app/models/schemas/camera.py`**
   ```python
   from pydantic import BaseModel, Field
   from datetime import datetime
   from typing import Optional

   class EncoderSettings(BaseModel):
       profile: str = Field(default="main", pattern="^(baseline|main|high)$")
       bitrate: int = Field(default=4000000, ge=500000, le=20000000)
       mjpeg_fallback: bool = False

   class CameraBase(BaseModel):
       name: str = Field(..., min_length=1, max_length=100)
       source_type: str = Field(..., pattern="^(CSI|USB)$")
       device_path: str = Field(..., min_length=1)
       resolution: str = Field(default="1920x1080", pattern=r"^\d+x\d+$")
       fps: int = Field(default=30, ge=1, le=120)
       encoder_settings: Optional[EncoderSettings] = None
       enabled: bool = True

   class CameraCreate(CameraBase):
       pass

   class CameraUpdate(BaseModel):
       name: Optional[str] = Field(None, min_length=1, max_length=100)
       source_type: Optional[str] = Field(None, pattern="^(CSI|USB)$")
       device_path: Optional[str] = None
       resolution: Optional[str] = Field(None, pattern=r"^\d+x\d+$")
       fps: Optional[int] = Field(None, ge=1, le=120)
       encoder_settings: Optional[EncoderSettings] = None
       enabled: Optional[bool] = None

   class CameraResponse(CameraBase):
       id: int
       created_at: datetime
       updated_at: datetime

       class Config:
           from_attributes = True
   ```

2. **Create `app/models/schemas/output.py`**
   ```python
   from pydantic import BaseModel, Field
   from datetime import datetime
   from typing import Optional

   class OutputConfigBase(BaseModel):
       recording_path: str = Field(default="./recordings")
       stills_path: str = Field(default="./stills")
       timelapse_path: str = Field(default="./timelapse")
       video_format: str = Field(default="mp4", pattern="^(mp4|mkv)$")
       image_format: str = Field(default="jpeg", pattern="^(jpeg|png)$")
       image_quality: int = Field(default=85, ge=1, le=100)

   class OutputConfigUpdate(BaseModel):
       recording_path: Optional[str] = None
       stills_path: Optional[str] = None
       timelapse_path: Optional[str] = None
       video_format: Optional[str] = Field(None, pattern="^(mp4|mkv)$")
       image_format: Optional[str] = Field(None, pattern="^(jpeg|png)$")
       image_quality: Optional[int] = Field(None, ge=1, le=100)

   class OutputConfigResponse(OutputConfigBase):
       id: int
       created_at: datetime
       updated_at: datetime

       class Config:
           from_attributes = True
   ```

### Acceptance Criteria
- [ ] All schemas validate correctly
- [ ] Patterns enforce valid values
- [ ] ORM models convert to schemas

---

## Testing Requirements

| Test | Type | Coverage |
|------|------|----------|
| Database init | Integration | Tables created |
| Camera CRUD | Integration | All operations |
| Output config | Integration | Get/update |
| Repository base | Unit | Generic CRUD |
| Pydantic schemas | Unit | Validation rules |

---

## File Lifecycle

- Current: `.ready.md`
- When starting: Rename to `.in_progress.md`
- When complete: Move to `.claude/plans/completed/02-database-config.md`

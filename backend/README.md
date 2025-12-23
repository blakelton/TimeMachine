# TimeMachine Backend

FastAPI-based backend for the TimeMachine Observation Chamber control system.

## Requirements

- Python 3.11+
- Raspberry Pi 3+ (for hardware features)

## Setup

1. Create virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:
```bash
make install-dev
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

4. Run development server:
```bash
make run
```

API will be available at:
- **API**: http://127.0.0.1:8000/api/v1
- **Docs**: http://127.0.0.1:8000/api/docs
- **ReDoc**: http://127.0.0.1:8000/api/redoc

## Development

### Run Tests
```bash
make test
```

### Linting
```bash
make lint
```

### Format Code
```bash
make format
```

### Type Check
```bash
make type-check
```

## Project Structure

```
app/
├── __init__.py           # Package initialization
├── main.py              # FastAPI app factory
├── api/                 # API routes
│   ├── routes/          # Route modules
│   └── websocket/       # WebSocket handlers
├── core/                # Core utilities
│   ├── config.py        # Settings
│   ├── logging.py       # Structured logging
│   ├── exceptions.py    # Custom exceptions
│   ├── security.py      # Authentication
│   └── rate_limit.py    # Rate limiting
├── models/              # Data models
│   ├── database.py      # SQLAlchemy models
│   └── schemas.py       # Pydantic schemas
├── services/            # Business logic
│   ├── camera/          # Camera services (preview, recording, timelapse)
│   │   └── resolver.py  # Hardware ID to device path resolution
│   ├── observation/     # Observation tracking and management
│   ├── storage/         # Storage services
│   ├── camera_device_monitor.py  # Background USB device monitoring
│   ├── stats_broadcaster.py      # WebSocket stats broadcasting
│   ├── startup.py       # Startup cleanup and device reconciliation
│   └── system/          # System monitoring
└── db/                  # Database
    ├── session.py       # DB session management
    └── migrations/      # Alembic migrations
```

## Configuration

All configuration via environment variables with `TIMEMACHINE_` prefix.

See [.env.example](.env.example) for all available options.

## Features Implemented

### Core Infrastructure
- [x] FastAPI application scaffold
- [x] Structured logging with structlog
- [x] Health and stats endpoints
- [x] CORS middleware
- [x] Optional HTTP Basic authentication
- [x] Rate limiting with slowapi
- [x] Custom exception hierarchy
- [x] Pydantic settings management

### Camera Services
- [x] Multi-camera support (CSI via libcamera, USB via GStreamer)
- [x] Persistent camera identification via hardware_id
- [x] Automatic device path resolution using /dev/v4l/by-path/ symlinks
- [x] Background device monitor for USB camera reconnection handling
- [x] Preview streaming with MJPEG
- [x] Still capture with configurable quality
- [x] Video recording with H.264 encoding
- [x] Timelapse with frame capture and video assembly

### Observation System
- [x] Observation tracking for captures, recordings, and timelapses
- [x] Thumbnail generation via ffmpeg
- [x] Batch delete API endpoint
- [x] Media file serving

### System Monitoring
- [x] CPU, RAM, disk, temperature monitoring
- [x] Raspberry Pi throttle detection
- [x] WebSocket stats broadcasting (2s interval)
- [x] Startup cleanup (stale jobs, orphan processes)
- [x] Device path reconciliation on startup

## Next Steps

See [docs/PROJECT_STATUS.md](../docs/PROJECT_STATUS.md) for current development status.

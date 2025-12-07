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
│   ├── camera/          # Camera services
│   ├── storage/         # Storage services
│   ├── jobs/            # Job management
│   └── system/          # System monitoring
└── db/                  # Database
    ├── session.py       # DB session management
    └── migrations/      # Alembic migrations
```

## Configuration

All configuration via environment variables with `TIMEMACHINE_` prefix.

See [.env.example](.env.example) for all available options.

## Features Implemented

- [x] FastAPI application scaffold
- [x] Structured logging with structlog
- [x] Health and stats endpoints
- [x] CORS middleware
- [x] Optional HTTP Basic authentication
- [x] Rate limiting with slowapi
- [x] Raspberry Pi throttle detection
- [x] System monitoring (CPU, RAM, disk, temperature)
- [x] Custom exception hierarchy
- [x] Pydantic settings management

## Next Steps

See [.claude/plans/00-master-plan.ready.md](../.claude/plans/00-master-plan.ready.md) for development roadmap.

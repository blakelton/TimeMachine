# TimeMachine Observation Chamber

Temperature-controlled observation chamber management system for Raspberry Pi 3+. Provides web-based control for camera management (CSI and USB), recording, timelapse creation, and temperature control.

## Development Status

**Current Phase**: Camera Services Implementation Complete

**What's Ready**:
- Complete, production-ready web interface with real-time monitoring
- Full camera configuration management (CRUD operations)
- Camera operations (preview, capture, record, timelapse) with Job tracking
- Timelapse service with resume support and video assembly
- Startup cleanup (stale jobs, orphan process handling)
- Deployment infrastructure (systemd, nginx, installation scripts)
- Comprehensive documentation

**What Needs Testing**:
- Hardware validation on Raspberry Pi 3
- GStreamer pipeline verification with actual cameras
- EOS handling for MP4 file finalization

**See**: [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) for detailed status

---

## Features

### Camera Operations
- **Camera Discovery**: Automatic detection of CSI and USB cameras
- **Live Preview**: MJPEG streaming with auto-reconnect
- **Still Capture**: High-quality JPEG with configurable quality
- **Video Recording**: H.264 hardware-encoded with EOS support for clean MP4 finalization
- **Timelapse Creation**: Configurable interval/duration with progress tracking, resume support, and ffmpeg video assembly
- **Job Tracking**: Database-backed job status with running/completed/failed states

### Web Interface
- **Home Dashboard**: Real-time system stats (CPU, memory, disk, temperature) with live camera status
- **Camera Tabs**: Individual camera control with Preview/Capture/Record/Timelapse tabs
- **System Settings**: Camera CRUD, output configuration, notification preferences
- **Responsive Design**: Mobile-first UI with touch-friendly controls
- **Real-time Updates**: WebSocket integration for live stats and job status

### System Management
- **Live Statistics**: CPU, memory, disk usage, and temperature via WebSocket (2s updates)
- **Disk Space Warnings**: Alerts when storage <10% free, blocks operations at <5%
- **Job Management**: View, filter, and manage recording/timelapse jobs via API
- **Startup Cleanup**: Automatic cleanup of stale jobs and orphan GStreamer processes
- **Graceful Shutdown**: EOS signal for recordings, proper job status updates

### API & Integration
- **RESTful API**: Full FastAPI backend with OpenAPI documentation
- **Jobs API**: Endpoints for job listing, filtering, and management
- **WebSocket Protocol**: Typed messages for stats, camera events, and job updates
- **Type Safety**: End-to-end TypeScript/Python type safety

## Hardware Requirements

- Raspberry Pi 3B+ or newer
- Raspberry Pi Camera Module (CSI) or USB webcam
- MicroSD card (16GB minimum, recommend USB storage for media)
- Power supply (5V 2.5A minimum)

## Quick Start

### Installation

```bash
# Download installation script
curl -O https://raw.githubusercontent.com/yourusername/TimeMachine/main/scripts/install.sh
chmod +x install.sh

# Run installation (requires sudo)
sudo ./install.sh
```

The installation script will:
- Install system dependencies (Python 3.11, GStreamer, libcamera, picamera2)
- Create timemachine user and directories
- Set up Python virtual environment with system site packages
- Initialize database
- Configure systemd service
- Copy nginx configuration

**Post-installation:**

```bash
# Setup nginx reverse proxy (recommended)
sudo ./scripts/setup-nginx.sh

# Install management command
sudo cp scripts/timemachine.sh /usr/local/bin/timemachine
sudo chmod +x /usr/local/bin/timemachine
```

### Configuration

Edit the environment configuration:

```bash
sudo nano /etc/timemachine/timemachine.env
```

**Update production paths:**
```bash
TIMEMACHINE_DB_PATH=/var/lib/timemachine/timemachine.db
TIMEMACHINE_MEDIA_PATH=/var/lib/timemachine/media
```

Key settings:
- `TIMEMACHINE_ENABLE_AUTH`: Enable HTTP Basic Auth (default: false)
- `TIMEMACHINE_API_USERNAME`: API username (if auth enabled)
- `TIMEMACHINE_API_PASSWORD`: API password (if auth enabled)
- `TIMEMACHINE_CORS_ORIGINS`: Allowed CORS origins

### Starting the Service

```bash
# Start services
sudo timemachine start

# Enable on boot
sudo timemachine enable

# Check status
timemachine status
```

### Accessing the Interface

- **Web UI**: http://raspberrypi.local (or your Pi's IP address)
- **API**: http://raspberrypi.local/api/v1/
- **API Docs**: http://raspberrypi.local/api/docs

## API Endpoints

### Camera Operations
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/cameras` | GET | List all cameras |
| `/cameras/{id}` | GET | Get camera details |
| `/cameras/discover` | POST | Discover available cameras |
| `/cameras/{id}/preview/start` | POST | Start MJPEG preview |
| `/cameras/{id}/preview/stop` | POST | Stop preview |
| `/cameras/{id}/capture` | POST | Capture still image |
| `/cameras/{id}/recording/start` | POST | Start recording (returns job_id) |
| `/cameras/{id}/recording/stop` | POST | Stop recording (EOS support) |
| `/cameras/{id}/timelapse/start` | POST | Start timelapse capture |
| `/cameras/{id}/timelapse/stop` | POST | Stop and assemble video |

### Job Management
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/jobs` | GET | List all jobs (filter by camera_id, job_type, status) |
| `/jobs/running` | GET | List currently running jobs |
| `/jobs/{id}` | GET | Get job details |
| `/jobs/{id}` | DELETE | Delete job record |

### System
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with system stats |
| `/ws` | WebSocket | Real-time stats and events |

## Management Commands

The `timemachine` command provides service management:

```bash
timemachine start          # Start services
timemachine stop           # Stop services
timemachine restart        # Restart services
timemachine status         # Show service status
timemachine logs           # Follow logs (Ctrl+C to exit)
timemachine logs-error     # Show error logs
timemachine enable         # Enable on boot
timemachine disable        # Disable from boot
timemachine update         # Update from git
timemachine backup         # Backup database and config
timemachine restore <file> # Restore from backup
timemachine check          # Run health checks
```

## Development

### Local Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/TimeMachine.git
cd TimeMachine

# Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend setup (separate terminal)
cd frontend
npm install
npm run dev
```

### Testing API Endpoints

```bash
# Health check
curl http://localhost:8000/api/v1/health

# List cameras
curl http://localhost:8000/api/v1/cameras

# Discover cameras
curl -X POST http://localhost:8000/api/v1/cameras/discover

# List jobs
curl http://localhost:8000/api/v1/jobs

# Start recording (camera ID 1)
curl -X POST http://localhost:8000/api/v1/cameras/1/recording/start

# Stop recording
curl -X POST http://localhost:8000/api/v1/cameras/1/recording/stop
```

### API Documentation

With the backend running, visit:
- Interactive API docs: http://localhost:8000/api/docs
- OpenAPI schema: http://localhost:8000/api/openapi.json

## Project Structure

```
TimeMachine/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # API endpoints (cameras, jobs, health, etc.)
│   │   ├── core/        # Config, logging, resources, rate limiting
│   │   ├── db/          # Database models and repositories
│   │   ├── schemas/     # Pydantic request/response schemas
│   │   └── services/    # Camera, timelapse, startup services
│   └── requirements.txt
├── frontend/            # React frontend
│   ├── src/
│   │   ├── api/        # API client
│   │   ├── components/ # React components
│   │   ├── contexts/   # React contexts
│   │   └── types/      # TypeScript types
│   └── package.json
├── deploy/             # Deployment configs
│   ├── timemachine.service
│   ├── timemachine.env.example
│   └── nginx.conf
├── scripts/            # Installation and ops scripts
│   ├── install.sh
│   └── timemachine.sh
└── docs/              # Documentation
```

## Technology Stack

**Backend:**
- Python 3.11
- FastAPI 0.104.1
- SQLAlchemy 2.0+ (async)
- GStreamer 1.0
- libcamera

**Frontend:**
- React 19
- TypeScript 5
- Vite 6
- TanStack Query
- React Router

**Deployment:**
- systemd
- nginx
- SQLite (WAL mode)

## Documentation

- **[Project Status](docs/PROJECT_STATUS.md)** - Current development status and roadmap
- [Getting Started Guide](docs/getting-started.md) - Installation and initial setup
- [Configuration Guide](docs/configuration.md) - Environment variables and settings
- [Troubleshooting Guide](docs/troubleshooting.md) - Common issues and solutions
- [Deployment Checklist](docs/deployment-checklist.md) - Production deployment guide
- [API Documentation](http://localhost:8000/api/docs) - Interactive API docs

## System Requirements

**Minimum:**
- Raspberry Pi 3B+ (1GB RAM)
- 16GB SD card
- One camera (CSI or USB)

**Recommended:**
- Raspberry Pi 4 (2GB+ RAM)
- USB storage for media files
- Multiple cameras for monitoring

**Resource Limits:**
- Memory limit: 800MB (systemd MemoryMax)
- Single H.264 encoder (one recording at a time)
- USB bandwidth shared between cameras and network

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat(scope): add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## Support

- GitHub Issues: https://github.com/yourusername/TimeMachine/issues
- Documentation: https://github.com/yourusername/TimeMachine/docs

# TimeMachine Observation Chamber

Temperature-controlled observation chamber management system for Raspberry Pi 3+. Provides web-based control for camera management (CSI and USB), recording, timelapse creation, and temperature control.

## ⚠️ Development Status

**Current Phase**: Post-Phase 4 - Core camera operations in development

**What's Ready**: ✅
- Complete, production-ready web interface with real-time monitoring
- Full camera configuration management (CRUD operations)
- Deployment infrastructure (systemd, nginx, installation scripts)
- Comprehensive documentation (getting started, configuration, troubleshooting, deployment)

**What's Not Ready**: ❌
- **Camera operations** (preview, capture, record, timelapse) - GStreamer services incomplete
- **Retention policies** - Background cleanup not implemented
- **Pipeline crash recovery** - Auto-restart not implemented

**Estimated Time to MVP**: 1-2 weeks
**See**: [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) for detailed status

---

## Features

### Camera Operations
- **Camera Management**: Full CRUD for CSI and USB cameras with enable/disable controls
- **Live Preview**: MJPEG streaming with auto-reconnect
- **Still Capture**: High-quality JPEG with configurable quality (low/medium/high/max)
- **Video Recording**: H.264 hardware-encoded recording with bitrate control and live timer
- **Timelapse Creation**: Configurable interval and duration with progress tracking

### Web Interface
- **Home Dashboard**: Real-time system stats (CPU, memory, disk, temperature) with live camera status
- **Camera Tabs**: Individual camera control with Preview/Capture/Record/Timelapse tabs
- **System Settings**: Camera CRUD, output configuration, notification preferences
- **Responsive Design**: Mobile-first UI with touch-friendly controls
- **Real-time Updates**: WebSocket integration for live stats and job status

### System Monitoring
- **Live Statistics**: CPU, memory, disk usage, and temperature via WebSocket (2s updates)
- **Disk Space Warnings**: Alerts when storage <10% free, blocks operations at <5%
- **Job Tracking**: Real-time recording and timelapse progress with WebSocket updates
- **Toast Notifications**: Success/error feedback for all operations

### API & Integration
- **RESTful API**: Full FastAPI backend with OpenAPI documentation
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
- **API Docs**: http://raspberrypi.local/api/v1/docs

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

# Initialize database
make db-init

# Run development server
make dev

# Frontend setup (separate terminal)
cd frontend
npm install
npm run dev
```

### API Documentation

With the backend running, visit:
- Interactive API docs: http://localhost:8000/api/v1/docs
- OpenAPI schema: http://localhost:8000/api/v1/openapi.json

## Project Structure

```
TimeMachine/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── core/        # Config, logging, resources
│   │   ├── db/          # Database models and repositories
│   │   └── services/    # Camera, system services
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
- [API Documentation](http://localhost:8000/api/v1/docs) - Interactive API docs

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

# TimeMachine Observation Chamber

Temperature-controlled observation chamber management system for Raspberry Pi 3+. Provides web-based control for camera management (CSI and USB), recording, timelapse creation, and temperature control.

## Features

- **Camera Management**: Support for CSI and USB cameras with auto-discovery
- **Live Preview**: MJPEG streaming from multiple cameras
- **Still Capture**: High-quality JPEG image capture
- **Video Recording**: H.264 hardware-encoded video recording
- **Web Interface**: Responsive React-based UI for remote control
- **System Monitoring**: Real-time CPU, memory, and temperature monitoring
- **RESTful API**: Full API for programmatic control
- **WebSocket**: Real-time system stats and event notifications

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
- Install system dependencies (Python 3.11, GStreamer, libcamera)
- Create timemachine user and directories
- Set up Python virtual environment
- Initialize database
- Configure systemd service
- Set up nginx reverse proxy

### Configuration

Edit the environment configuration:

```bash
sudo nano /etc/timemachine/timemachine.env
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

- [Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions
- [Configuration Reference](docs/CONFIGURATION.md) - Environment variables and settings
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md) - Common issues and solutions
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

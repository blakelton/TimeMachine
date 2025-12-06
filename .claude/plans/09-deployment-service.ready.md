# Deployment & Service - Plan

## Overview

Configure systemd service, nginx reverse proxy, and deployment scripts for production on Raspberry Pi.

**Dependencies**: All backend and frontend plans
**Estimated Duration**: 1-2 days

---

## Phase 1: Systemd Service

### Goal
Create robust systemd service configuration.

### Tasks

1. **Create `deploy/timemachine.service`**
   ```ini
   [Unit]
   Description=TimeMachine Observation Chamber
   After=network.target

   [Service]
   Type=exec
   User=timemachine
   Group=timemachine
   WorkingDirectory=/opt/timemachine/backend
   EnvironmentFile=/etc/timemachine/timemachine.env
   ExecStart=/opt/timemachine/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
   ExecReload=/bin/kill -HUP $MAINPID
   Restart=always
   RestartSec=5

   # Security hardening
   NoNewPrivileges=true
   ProtectSystem=strict
   ProtectHome=true
   PrivateTmp=true
   ReadWritePaths=/var/lib/timemachine
   
   # Allow access to camera devices
   SupplementaryGroups=video
   DeviceAllow=/dev/video* rw
   DeviceAllow=/dev/vchiq rw

   # Logging
   StandardOutput=journal
   StandardError=journal
   SyslogIdentifier=timemachine

   [Install]
   WantedBy=multi-user.target
   ```

2. **Create `deploy/timemachine.env.example`**
   ```bash
   # TimeMachine Environment Configuration
   
   # Environment (development|production)
   TIMEMACHINE_ENV=production
   
   # Logging
   TIMEMACHINE_LOG_LEVEL=INFO
   
   # Server
   TIMEMACHINE_HOST=127.0.0.1
   TIMEMACHINE_PORT=8000
   
   # Database
   TIMEMACHINE_DB_PATH=/var/lib/timemachine/timemachine.db
   
   # Storage
   TIMEMACHINE_MEDIA_PATH=/var/lib/timemachine/media
   
   # Encoder defaults
   TIMEMACHINE_DEFAULT_RESOLUTION=1920x1080
   TIMEMACHINE_DEFAULT_FPS=30
   TIMEMACHINE_DEFAULT_BITRATE=4000000
   
   # Retention
   TIMEMACHINE_RETENTION_DAYS=30
   TIMEMACHINE_RETENTION_MAX_GB=50
   ```

### Acceptance Criteria
- [ ] Service starts on boot
- [ ] Restarts on failure
- [ ] Camera access works
- [ ] Logging to journald

---

## Phase 2: Installation Script

### Goal
Automated installation for Pi.

### Tasks

1. **Create `scripts/install.sh`**
   ```bash
   #!/bin/bash
   set -e

   echo "=== TimeMachine Installation ==="

   # Check root
   if [ "$EUID" -ne 0 ]; then
     echo "Please run as root"
     exit 1
   fi

   # Create user
   if ! id -u timemachine &>/dev/null; then
     echo "Creating timemachine user..."
     useradd -r -s /bin/false -d /opt/timemachine timemachine
     usermod -aG video timemachine
   fi

   # Create directories
   echo "Creating directories..."
   mkdir -p /opt/timemachine
   mkdir -p /var/lib/timemachine/media/{recordings,stills,timelapse}
   mkdir -p /etc/timemachine

   # Copy application
   echo "Copying application..."
   cp -r backend /opt/timemachine/
   cp -r frontend/dist /opt/timemachine/static

   # Create virtual environment
   echo "Setting up Python environment..."
   python3 -m venv /opt/timemachine/venv
   /opt/timemachine/venv/bin/pip install -r /opt/timemachine/backend/requirements.txt

   # Copy configuration
   if [ ! -f /etc/timemachine/timemachine.env ]; then
     cp deploy/timemachine.env.example /etc/timemachine/timemachine.env
     chmod 640 /etc/timemachine/timemachine.env
   fi

   # Set permissions
   echo "Setting permissions..."
   chown -R timemachine:timemachine /opt/timemachine
   chown -R timemachine:timemachine /var/lib/timemachine
   chown root:timemachine /etc/timemachine/timemachine.env

   # Install service
   echo "Installing service..."
   cp deploy/timemachine.service /etc/systemd/system/
   systemctl daemon-reload
   systemctl enable timemachine

   echo "=== Installation Complete ==="
   echo "Edit /etc/timemachine/timemachine.env then run:"
   echo "  systemctl start timemachine"
   ```

### Acceptance Criteria
- [ ] Script runs without errors
- [ ] All directories created
- [ ] Permissions correct
- [ ] Service enabled

---

## Phase 3: Frontend Deployment

### Goal
Serve static frontend with FastAPI.

### Tasks

1. **Update `app/main.py` for static files**
   ```python
   from fastapi.staticfiles import StaticFiles
   from pathlib import Path

   def create_app() -> FastAPI:
       app = FastAPI(...)
       
       # Mount static files if directory exists
       static_dir = Path("/opt/timemachine/static")
       if static_dir.exists():
           app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
       
       return app
   ```

2. **Build frontend for production**
   ```bash
   cd frontend
   npm run build
   # Output in frontend/dist/
   ```

### Acceptance Criteria
- [ ] Frontend served from FastAPI
- [ ] SPA routing works
- [ ] Assets cached properly

---

## Phase 4: Nginx Configuration

### Goal
Reverse proxy with HTTPS support.

### Tasks

1. **Create `deploy/nginx/timemachine.conf`**
   ```nginx
   upstream timemachine {
       server 127.0.0.1:8000;
   }

   server {
       listen 80;
       server_name _;

       # Redirect to HTTPS (optional)
       # return 301 https://$server_name$request_uri;

       location / {
           proxy_pass http://timemachine;
           proxy_http_version 1.1;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       # WebSocket support
       location /ws {
           proxy_pass http://timemachine;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_read_timeout 86400;
       }

       # MJPEG stream (long-lived connections)
       location ~ ^/api/v1/cameras/\d+/stream$ {
           proxy_pass http://timemachine;
           proxy_http_version 1.1;
           proxy_set_header Host $host;
           proxy_buffering off;
           proxy_cache off;
           proxy_read_timeout 86400;
       }
   }
   ```

2. **Create `deploy/nginx/timemachine-ssl.conf`** (HTTPS version)
   ```nginx
   server {
       listen 443 ssl http2;
       server_name _;

       ssl_certificate /etc/ssl/certs/timemachine.crt;
       ssl_certificate_key /etc/ssl/private/timemachine.key;

       # ... same location blocks ...
   }
   ```

### Acceptance Criteria
- [ ] HTTP proxy works
- [ ] WebSocket proxied
- [ ] MJPEG streams work
- [ ] HTTPS available

---

## Phase 5: Operational Commands

### Goal
Scripts for common operations.

### Tasks

1. **Create `scripts/timemachine.sh`**
   ```bash
   #!/bin/bash
   
   case "$1" in
     start)
       sudo systemctl start timemachine
       ;;
     stop)
       sudo systemctl stop timemachine
       ;;
     restart)
       sudo systemctl restart timemachine
       ;;
     status)
       sudo systemctl status timemachine
       ;;
     logs)
       sudo journalctl -u timemachine -f
       ;;
     update)
       echo "Stopping service..."
       sudo systemctl stop timemachine
       echo "Updating..."
       git pull
       cd frontend && npm run build && cd ..
       sudo cp -r frontend/dist /opt/timemachine/static
       /opt/timemachine/venv/bin/pip install -r backend/requirements.txt
       echo "Starting service..."
       sudo systemctl start timemachine
       ;;
     backup)
       BACKUP_DIR="/var/backups/timemachine"
       mkdir -p "$BACKUP_DIR"
       cp /var/lib/timemachine/timemachine.db "$BACKUP_DIR/timemachine_$(date +%Y%m%d).db"
       cp /etc/timemachine/timemachine.env "$BACKUP_DIR/timemachine.env_$(date +%Y%m%d)"
       echo "Backup complete"
       ;;
     *)
       echo "Usage: $0 {start|stop|restart|status|logs|update|backup}"
       exit 1
       ;;
   esac
   ```

### Acceptance Criteria
- [ ] All commands work
- [ ] Update process smooth
- [ ] Backup saves config

---

## Phase 6: Camera Permissions

### Goal
Ensure camera access for service.

### Tasks

1. **Create udev rule for camera access**
   ```
   # /etc/udev/rules.d/99-timemachine-cameras.rules
   SUBSYSTEM=="video4linux", GROUP="video", MODE="0660"
   ```

2. **Document permission requirements**
   - User must be in `video` group
   - `/dev/vchiq` access for CSI cameras
   - `/dev/video*` access for USB cameras

### Acceptance Criteria
- [ ] USB cameras accessible
- [ ] CSI cameras accessible
- [ ] Permissions persist on reboot

---

## Phase 7: Development Workflow

### Goal
Streamline development-to-Pi workflow.

### Tasks

1. **Create `scripts/deploy-to-pi.sh`**
   ```bash
   #!/bin/bash
   PI_HOST="${PI_HOST:-pi@raspberrypi.local}"
   
   echo "Building frontend..."
   cd frontend && npm run build && cd ..
   
   echo "Syncing to Pi..."
   rsync -avz --exclude 'node_modules' --exclude '.venv' --exclude '__pycache__' \
     ./ "$PI_HOST:/home/pi/timemachine/"
   
   echo "Restarting service..."
   ssh "$PI_HOST" "cd /home/pi/timemachine && sudo ./scripts/timemachine.sh update"
   
   echo "Done!"
   ```

### Acceptance Criteria
- [ ] One-command deploy
- [ ] Service restarts
- [ ] Changes visible immediately

---

## Phase 8: Monitoring & Health

### Goal
Health monitoring and alerts.

### Tasks

1. **Add systemd watchdog**
   ```ini
   [Service]
   WatchdogSec=30
   ```

2. **Implement health check in app**
   - Return 200 if healthy
   - Touch watchdog periodically

3. **Configure log rotation**
   ```
   # /etc/logrotate.d/timemachine
   /var/log/timemachine/*.log {
       daily
       rotate 7
       compress
       missingok
       notifempty
   }
   ```

### Acceptance Criteria
- [ ] Watchdog restarts hung service
- [ ] Logs rotated
- [ ] Health endpoint works

---

## Troubleshooting Guide

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Service won't start | Permission denied | Check user/group, video group |
| No camera detected | /dev/video missing | Check udev rules, cable |
| MJPEG stream fails | Encoder busy | Only one H.264 stream at a time |
| WebSocket disconnects | Proxy timeout | Check nginx proxy_read_timeout |
| Database locked | Concurrent writes | Check for zombie processes |

---

## File Lifecycle

- Current: `.ready.md`
- When starting: Rename to `.in_progress.md`
- When complete: Move to `.claude/plans/completed/09-deployment-service.md`

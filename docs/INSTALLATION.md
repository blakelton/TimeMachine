# TimeMachine Installation Guide

Complete installation instructions for TimeMachine Observation Chamber on Raspberry Pi.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Automated Installation](#automated-installation)
- [Manual Installation](#manual-installation)
- [Post-Installation](#post-installation)
- [Verification](#verification)
- [Uninstallation](#uninstallation)

## Prerequisites

### Hardware Requirements

- Raspberry Pi 3B+ or newer (1GB RAM minimum, 2GB+ recommended)
- MicroSD card (16GB minimum, Class 10 or better)
- Raspberry Pi Camera Module (CSI) and/or USB webcam
- Power supply: 5V 2.5A minimum (5V 3A recommended for Pi 4)
- Network connection (Ethernet or WiFi)

### Software Requirements

- Raspberry Pi OS (Bullseye or newer)
- Internet connection for package downloads
- Root access (sudo privileges)

### Recommended Setup

- **Use USB storage for media files**: SD cards have limited write endurance
- **Enable SSH**: For remote management
- **Static IP or mDNS**: For consistent access

## Automated Installation

The automated installation script handles all setup steps.

### 1. Download Installation Script

```bash
# Option 1: Direct download
curl -O https://raw.githubusercontent.com/yourusername/TimeMachine/main/scripts/install.sh
chmod +x install.sh

# Option 2: Clone repository
git clone https://github.com/yourusername/TimeMachine.git
cd TimeMachine
chmod +x scripts/install.sh
```

### 2. Run Installation

```bash
sudo ./scripts/install.sh
```

The script will:
1. Update system packages
2. Install Python 3.11 and dependencies
3. Install GStreamer and libcamera packages
4. Create `timemachine` system user
5. Create directory structure in `/opt/timemachine`
6. Set up Python virtual environment
7. Install Python dependencies
8. Initialize SQLite database
9. Install systemd service
10. Install nginx configuration
11. Install management script to `/usr/local/bin/timemachine`

**Installation time:** 10-20 minutes (depending on internet speed)

### 3. Configure Environment

Edit the environment file:

```bash
sudo nano /etc/timemachine/timemachine.env
```

See [CONFIGURATION.md](CONFIGURATION.md) for all available options.

### 4. Start Services

```bash
# Start services
sudo timemachine start

# Enable on boot
sudo timemachine enable

# Check status
timemachine status
```

## Manual Installation

For custom setups or troubleshooting, follow these manual steps.

### 1. System Dependencies

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Install GStreamer
sudo apt install -y \
  gstreamer1.0-tools \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-ugly \
  gstreamer1.0-libav \
  python3-gst-1.0

# Install libcamera
sudo apt install -y \
  libcamera-apps \
  libcamera-dev \
  libcamera-tools

# Install camera support and build dependencies
sudo apt install -y \
  build-essential \
  git \
  nginx \
  v4l-utils \
  python3-picamera2
```

### 2. Create System User

```bash
# Create timemachine user
sudo useradd -r -s /bin/false -d /opt/timemachine -m timemachine

# Add to video group for camera access
sudo usermod -aG video timemachine
```

### 3. Create Directory Structure

```bash
# Application directory
sudo mkdir -p /opt/timemachine
sudo chown timemachine:timemachine /opt/timemachine

# Data directories
sudo mkdir -p /var/lib/timemachine/{media,recordings,stills,timelapse}
sudo chown -R timemachine:timemachine /var/lib/timemachine
sudo chmod 755 /var/lib/timemachine

# Configuration directory
sudo mkdir -p /etc/timemachine
sudo chmod 755 /etc/timemachine
```

### 4. Clone Repository

```bash
# Clone as timemachine user
sudo -u timemachine git clone https://github.com/yourusername/TimeMachine.git /opt/timemachine/.repo

# Copy backend files
sudo -u timemachine cp -r /opt/timemachine/.repo/backend/* /opt/timemachine/

# Copy deployment files
sudo cp /opt/timemachine/.repo/deploy/timemachine.service /etc/systemd/system/
sudo cp /opt/timemachine/.repo/deploy/timemachine.env.example /etc/timemachine/timemachine.env
sudo cp /opt/timemachine/.repo/deploy/nginx.conf /etc/nginx/sites-available/timemachine

# Copy scripts
sudo cp /opt/timemachine/.repo/scripts/timemachine.sh /usr/local/bin/timemachine
sudo chmod +x /usr/local/bin/timemachine
```

### 5. Python Environment

```bash
# Create virtual environment with system site packages (for picamera2)
sudo -u timemachine python3.11 -m venv /opt/timemachine/venv --system-site-packages

# Install dependencies
sudo -u timemachine /opt/timemachine/venv/bin/pip install --upgrade pip
sudo -u timemachine /opt/timemachine/venv/bin/pip install -r /opt/timemachine/requirements.txt
```

### 6. Database Initialization

```bash
# Create database directory
sudo mkdir -p /var/lib/timemachine
sudo chown timemachine:timemachine /var/lib/timemachine

# Initialize database
sudo -u timemachine /opt/timemachine/venv/bin/python -c "
import asyncio
from app.db.session import init_db
asyncio.run(init_db())
"
```

### 7. Environment Configuration

```bash
# Edit configuration
sudo nano /etc/timemachine/timemachine.env

# Set minimal configuration
TIMEMACHINE_DB_PATH=/var/lib/timemachine/timemachine.db
TIMEMACHINE_MEDIA_PATH=/var/lib/timemachine/media
TIMEMACHINE_LOG_LEVEL=INFO
```

### 8. Systemd Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable timemachine

# Start service
sudo systemctl start timemachine

# Check status
sudo systemctl status timemachine
```

### 9. Nginx Configuration

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/timemachine /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

## Post-Installation

### 1. Verify Installation

```bash
# Run health check
timemachine check
```

Expected output:
```
=== TimeMachine Health Check ===

✓ Service is running
✓ API is responding
✓ Database exists (24K)
✓ Disk space available: 25G
✓ Memory available: 500M
✓ Cameras detected: 1
```

### 2. Access Web Interface

Open browser to:
- http://raspberrypi.local (if mDNS enabled)
- http://YOUR_PI_IP_ADDRESS

### 3. Verify API

```bash
# Test health endpoint
curl http://localhost:8000/api/v1/health

# Expected response:
{"status":"healthy","version":"0.1.0"}

# View API documentation
curl http://localhost:8000/api/v1/docs
```

### 4. Test Camera Discovery

```bash
# Discover cameras via API
curl -X POST http://localhost:8000/api/v1/cameras/discover

# Expected response:
{"cameras_found":1,"message":"Camera discovery completed"}
```

### 5. Configure Firewall (Optional)

```bash
# Allow HTTP
sudo ufw allow 80/tcp

# Allow HTTPS (if configured)
sudo ufw allow 443/tcp

# Reload firewall
sudo ufw reload
```

## USB Storage Configuration (Recommended)

Using USB storage for media files extends SD card life.

### 1. Format USB Drive

```bash
# Find USB device
lsblk

# Format (replace sdX with your device)
sudo mkfs.ext4 /dev/sdX1
```

### 2. Mount USB Drive

```bash
# Create mount point
sudo mkdir -p /mnt/timemachine

# Get UUID
sudo blkid /dev/sdX1

# Add to /etc/fstab
UUID=your-uuid-here /mnt/timemachine ext4 defaults,nofail 0 2

# Mount
sudo mount -a
```

### 3. Update Configuration

```bash
# Edit environment
sudo nano /etc/timemachine/timemachine.env

# Update media path
TIMEMACHINE_MEDIA_PATH=/mnt/timemachine/media

# Create directories
sudo mkdir -p /mnt/timemachine/media
sudo chown timemachine:timemachine /mnt/timemachine/media

# Restart service
sudo timemachine restart
```

## Verification

### Check Service Status

```bash
# Service status
sudo systemctl status timemachine

# Should show: Active: active (running)
```

### Check Logs

```bash
# Follow logs
timemachine logs

# Check for errors
timemachine logs-error
```

### Test Endpoints

```bash
# Health check
curl http://localhost:8000/api/v1/health

# System stats
curl http://localhost:8000/api/v1/system/stats

# Camera list
curl http://localhost:8000/api/v1/cameras
```

## Uninstallation

To completely remove TimeMachine:

```bash
# Stop and disable service
sudo systemctl stop timemachine
sudo systemctl disable timemachine

# Remove systemd service
sudo rm /etc/systemd/system/timemachine.service
sudo systemctl daemon-reload

# Remove nginx config
sudo rm /etc/nginx/sites-enabled/timemachine
sudo rm /etc/nginx/sites-available/timemachine
sudo systemctl restart nginx

# Remove application files
sudo rm -rf /opt/timemachine

# Remove data (CAUTION: Deletes all recordings)
sudo rm -rf /var/lib/timemachine

# Remove configuration
sudo rm -rf /etc/timemachine

# Remove management script
sudo rm /usr/local/bin/timemachine

# Remove user (optional)
sudo userdel timemachine
```

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.

## Next Steps

- [Configure environment variables](CONFIGURATION.md)
- [Set up authentication](CONFIGURATION.md#authentication)
- [Configure cameras](CONFIGURATION.md#camera-settings)
- [Set up backups](CONFIGURATION.md#backup-configuration)

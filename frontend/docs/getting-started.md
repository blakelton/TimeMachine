# TimeMachine Observation Chamber - Getting Started Guide

## Overview

TimeMachine is a temperature-controlled observation chamber management system designed for Raspberry Pi 3+. It provides web-based control for camera management, recording, timelapse creation, and system monitoring.

## System Requirements

### Hardware

- **Raspberry Pi 3 or later** (tested on Pi 3B+, Pi 4, Pi 5)
- **Minimum 16GB microSD card** (Class 10 or better recommended)
- **USB or CSI camera(s)** - supports multiple cameras
- **Stable 5V power supply** (2.5A minimum for Pi 3)
- **Network connection** (Ethernet recommended for reliability)

### Software

- **Raspberry Pi OS** (Bullseye or later)
- **Python 3.11+**
- **Node.js 18+** (for frontend build)
- **nginx** (reverse proxy)

## Installation

### 1. Prepare Raspberry Pi

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip \
  nginx git libcamera-dev gstreamer1.0-tools \
  gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad v4l-utils

# Install Node.js 18 (if not already installed)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### 2. Clone Repository

```bash
cd /opt
sudo git clone https://github.com/yourusername/timemachine.git
sudo chown -R $USER:$USER /opt/timemachine
cd /opt/timemachine
```

### 3. Run Installation Script

```bash
chmod +x scripts/install.sh
sudo ./scripts/install.sh
```

The installation script will:
- Create `timemachine` system user and group
- Set up Python virtual environment
- Install backend dependencies
- Build frontend static files
- Create necessary directories
- Copy systemd service file
- Configure nginx
- Set up permissions

### 4. Configure Environment

```bash
# Edit environment configuration
sudo nano /etc/timemachine/timemachine.env
```

Key settings to configure:

```bash
# Authentication (recommended for production)
TIMEMACHINE_AUTH_ENABLED=true
TIMEMACHINE_AUTH_USERNAME=admin
TIMEMACHINE_AUTH_PASSWORD=your_secure_password_here

# CORS (allow your Pi's IP address)
TIMEMACHINE_CORS_ORIGINS=http://192.168.1.100

# Storage (optional: use external USB or NAS)
TIMEMACHINE_MEDIA_PATH=/mnt/usb/timemachine/media
```

### 5. Start Services

```bash
# Enable and start TimeMachine service
sudo systemctl enable timemachine
sudo systemctl start timemachine

# Check status
sudo systemctl status timemachine

# Enable and start nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 6. Access Web Interface

Open your browser and navigate to:
- **Local access**: `http://localhost` or `http://raspberrypi.local`
- **Network access**: `http://<raspberry-pi-ip-address>`

If authentication is enabled, log in with the credentials from your `.env` file.

## Initial Configuration

### Add Your First Camera

1. Navigate to **Settings** > **Cameras**
2. Click **Add Camera**
3. Fill in camera details:
   - **Name**: Descriptive name (e.g., "Top View Camera")
   - **Type**: `csi` or `usb`
   - **Device Path**: 
     - CSI: Usually `/dev/video0`
     - USB: Check with `ls /dev/video*`
   - **Enabled**: Check to activate
4. Click **Save**

### Configure Output Settings

1. Navigate to **Settings** > **Output Config**
2. Set storage paths:
   - **Recording Path**: `/var/lib/timemachine/media/recordings`
   - **Still Path**: `/var/lib/timemachine/media/stills`
   - **Timelapse Path**: `/var/lib/timemachine/media/timelapse`
3. Set retention policies:
   - **Retention Days**: Number of days to keep files
   - **Max Storage GB**: Maximum storage to use
4. Click **Save**

## Basic Operations

### Camera Preview

1. Go to **Home** dashboard
2. Click on a camera card
3. Navigate to **Preview** tab
4. Click **Start Preview**
5. Live MJPEG stream will appear
6. Click **Stop Preview** when done

### Capture Still Image

1. Navigate to camera's **Capture** tab
2. Select image quality (Low/Medium/High)
3. Click **Capture**
4. Image is saved to still path

### Record Video

1. Navigate to camera's **Record** tab
2. Set recording parameters:
   - **Duration** (seconds)
   - **Bitrate** (kbps)
3. Click **Start Recording**
4. Recording progress shows in real-time
5. Video saved to recording path when complete

### Create Timelapse

1. Navigate to camera's **Timelapse** tab
2. Configure timelapse:
   - **Interval** (seconds between captures)
   - **Duration** (total timelapse duration)
3. Click **Start Timelapse**
4. Progress tracked in UI
5. Completed video saved to timelapse path

## Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u timemachine -n 50

# Check for port conflicts
sudo netstat -tlnp | grep 8000

# Verify Python environment
cd /opt/timemachine/backend
source venv/bin/activate
python -c "import app; print('OK')"
```

### Camera not detected

```bash
# List video devices
ls -l /dev/video*

# Test camera with libcamera (CSI)
libcamera-hello --list-cameras

# Test camera with v4l2 (USB)
v4l2-ctl --list-devices
```

### Frontend not loading

```bash
# Check nginx status
sudo systemctl status nginx

# Check nginx error log
sudo tail -f /var/log/nginx/timemachine-error.log

# Verify static files
ls -la /opt/timemachine/static
```

### Low disk space warnings

```bash
# Check disk usage
df -h

# Clean up old recordings
sudo find /var/lib/timemachine/media -type f -mtime +30 -delete

# Consider using external storage
```

## Next Steps

- Read [Configuration Guide](configuration.md) for advanced settings
- Read [Troubleshooting Guide](troubleshooting.md) for common issues
- Review [API Documentation](http://raspberrypi.local/api/docs)
- Set up automated backups to NAS
- Configure temperature control (coming soon)

## Getting Help

- **GitHub Issues**: https://github.com/yourusername/timemachine/issues
- **Documentation**: https://github.com/yourusername/timemachine/wiki
- **Logs**: `sudo journalctl -u timemachine -f`

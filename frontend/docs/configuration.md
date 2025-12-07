# TimeMachine - Configuration Guide

## Environment Variables

All configuration is managed through environment variables in `/etc/timemachine/timemachine.env`.

### Core Settings

```bash
# Environment mode (development|production)
TIMEMACHINE_ENV=production

# Enable debug logging (true|false)
TIMEMACHINE_DEBUG=false

# Log level (DEBUG|INFO|WARNING|ERROR|CRITICAL)
TIMEMACHINE_LOG_LEVEL=INFO
```

### Server Configuration

```bash
# Bind address (127.0.0.1 for localhost only, 0.0.0.0 for all interfaces)
TIMEMACHINE_HOST=127.0.0.1

# Port (default: 8000, must match nginx config)
TIMEMACHINE_PORT=8000
```

### Database

```bash
# SQLite database path
TIMEMACHINE_DB_PATH=/var/lib/timemachine/timemachine.db
```

The database uses **WAL mode** for better concurrency and reduced SD card wear.

### Storage

```bash
# Media storage root path
TIMEMACHINE_MEDIA_PATH=/var/lib/timemachine/media
```

#### Storage Structure

```
/var/lib/timemachine/media/
├── recordings/           # Video recordings
│   └── YYYY-MM-DD/
│       └── camera_name_HHMMSS.mp4
├── stills/              # Still images
│   └── YYYY-MM-DD/
│       └── camera_name_HHMMSS.jpg
└── timelapse/           # Timelapse videos
    └── YYYY-MM-DD/
        └── camera_name_HHMMSS.mp4
```

#### Using External Storage

**USB Drive:**

```bash
# Format drive
sudo mkfs.ext4 /dev/sda1

# Create mount point
sudo mkdir -p /mnt/usb

# Mount drive
sudo mount /dev/sda1 /mnt/usb

# Add to fstab for auto-mount
echo "/dev/sda1 /mnt/usb ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab

# Update environment
TIMEMACHINE_MEDIA_PATH=/mnt/usb/timemachine/media
```

**NAS (NFS):**

```bash
# Install NFS client
sudo apt install -y nfs-common

# Create mount point
sudo mkdir -p /mnt/nas

# Mount NAS
sudo mount -t nfs 192.168.1.10:/volume1/timemachine /mnt/nas

# Add to fstab
echo "192.168.1.10:/volume1/timemachine /mnt/nas nfs defaults,nofail 0 0" | sudo tee -a /etc/fstab

# Update environment
TIMEMACHINE_MEDIA_PATH=/mnt/nas/media
```

### Security

#### CORS Origins

```bash
# Comma-separated list of allowed origins
TIMEMACHINE_CORS_ORIGINS=http://localhost:5173,http://192.168.1.100
```

**Production recommendation**: Only allow your Pi's IP address.

#### Authentication

```bash
# Enable HTTP Basic Auth (recommended for production)
TIMEMACHINE_AUTH_ENABLED=true

# Username for authentication
TIMEMACHINE_AUTH_USERNAME=admin

# Password (REQUIRED if auth is enabled)
TIMEMACHINE_AUTH_PASSWORD=your_secure_password_here
```

**Security best practices:**
- Use a strong password (16+ characters)
- Consider adding HTTPS with Let's Encrypt
- Restrict network access with firewall rules

### Encoder Defaults

```bash
# Default video resolution
TIMEMACHINE_DEFAULT_RESOLUTION=1920x1080

# Default frames per second
TIMEMACHINE_DEFAULT_FPS=30

# Default bitrate in bits/second (4Mbps = 4000000)
TIMEMACHINE_DEFAULT_BITRATE=4000000

# H.264 profile (baseline|main|high)
# Pi 3: use 'main' for best compatibility
# Pi 4/5: can use 'high' for better quality
TIMEMACHINE_H264_PROFILE=main
```

**Pi 3 recommendations:**
- Max resolution: 1920x1080
- Max FPS: 30
- Bitrate: 3000000-5000000 (3-5 Mbps)

**Pi 4/5 capabilities:**
- Max resolution: 1920x1080 (higher possible with encoding limits)
- Max FPS: 60
- Bitrate: up to 10000000 (10 Mbps)

### Retention Policies

```bash
# Days to keep files before auto-deletion
TIMEMACHINE_RETENTION_DAYS=30

# Maximum storage to use in GB
TIMEMACHINE_RETENTION_MAX_GB=50
```

Files are deleted automatically when:
1. Age exceeds `RETENTION_DAYS`
2. Total storage exceeds `RETENTION_MAX_GB` (oldest files deleted first)

### Resource Limits

```bash
# Minimum available memory (MB) before blocking operations
TIMEMACHINE_MIN_MEMORY_MB=100

# Minimum available disk space (MB) before blocking recordings
TIMEMACHINE_MIN_DISK_MB=500
```

These limits prevent system crashes due to resource exhaustion.

## systemd Configuration

Edit `/etc/systemd/system/timemachine.service`:

### Memory Limits

```ini
[Service]
# Maximum memory (800MB for Pi 3, can increase for Pi 4/5)
MemoryMax=800M

# Soft limit (warnings start here)
MemoryHigh=700M
```

### CPU Quota

```ini
[Service]
# CPU quota (300% = 3 cores on Pi 3)
CPUQuota=300%
```

### Restart Policy

```ini
[Service]
# Restart behavior
Restart=always
RestartSec=10

# Timeout for graceful shutdown
TimeoutStopSec=30
```

After editing:

```bash
sudo systemctl daemon-reload
sudo systemctl restart timemachine
```

## nginx Configuration

Edit `/etc/nginx/sites-available/timemachine`:

### Reverse Proxy Timeouts

```nginx
location /api/ {
    # Increase for long-running operations
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}
```

### WebSocket Configuration

```nginx
location /ws/ {
    # Long timeouts for persistent connections
    proxy_connect_timeout 7d;
    proxy_send_timeout 7d;
    proxy_read_timeout 7d;
}
```

### Upload Limits

```nginx
server {
    # Maximum upload size (for future file uploads)
    client_max_body_size 100M;
}
```

After editing:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Camera Configuration

### CSI Camera

```json
{
  "name": "CSI Camera",
  "type": "csi",
  "device_path": "/dev/video0",
  "enabled": true
}
```

### USB Camera

```json
{
  "name": "USB Webcam",
  "type": "usb",
  "device_path": "/dev/video2",
  "enabled": true
}
```

**Finding device paths:**

```bash
# List all video devices
v4l2-ctl --list-devices

# Test camera
libcamera-hello --list-cameras  # CSI
ffmpeg -f v4l2 -list_formats all -i /dev/video2  # USB
```

## Monitoring and Alerts

### System Stats

Stats are broadcast via WebSocket every 2 seconds:
- CPU usage (%)
- Memory usage (%)
- Disk free space (GB)
- CPU temperature (°C)

### Throttle Detection

The system monitors for:
- Under-voltage (low power)
- ARM frequency capping (thermal)
- Currently throttled flag

Warnings displayed in UI when detected.

## Performance Tuning

### For Better Video Quality

```bash
# Increase bitrate
TIMEMACHINE_DEFAULT_BITRATE=6000000

# Use higher profile (Pi 4/5 only)
TIMEMACHINE_H264_PROFILE=high
```

### For Lower Resource Usage

```bash
# Reduce resolution
TIMEMACHINE_DEFAULT_RESOLUTION=1280x720

# Reduce FPS
TIMEMACHINE_DEFAULT_FPS=24

# Lower bitrate
TIMEMACHINE_DEFAULT_BITRATE=2000000
```

### For More Concurrent Operations (Pi 4/5)

```bash
# Increase memory limit in systemd
MemoryMax=2G
MemoryHigh=1800M

# Increase CPU quota
CPUQuota=400%
```

## Backup and Restore

### Backup Configuration

```bash
# Backup database and config
sudo tar czf timemachine-backup-$(date +%Y%m%d).tar.gz \
  /var/lib/timemachine/timemachine.db \
  /etc/timemachine/timemachine.env
```

### Restore Configuration

```bash
# Extract backup
sudo tar xzf timemachine-backup-YYYYMMDD.tar.gz -C /

# Restart service
sudo systemctl restart timemachine
```

### Backup Media Files

```bash
# Use rsync to backup to NAS
rsync -avz --progress /var/lib/timemachine/media/ \
  user@nas:/volume1/backups/timemachine/
```

## Advanced Configuration

### Enable HTTPS with Let's Encrypt

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate (requires domain name)
sudo certbot --nginx -d timemachine.yourdomain.com

# Auto-renewal is configured automatically
```

### Custom Logging

Create `/etc/timemachine/logging.json`:

```json
{
  "version": 1,
  "disable_existing_loggers": false,
  "formatters": {
    "json": {
      "()": "structlog.stdlib.ProcessorFormatter",
      "processor": "structlog.dev.ConsoleRenderer"
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "formatter": "json",
      "stream": "ext://sys.stdout"
    }
  },
  "root": {
    "level": "INFO",
    "handlers": ["console"]
  }
}
```

Update systemd service to use custom logging:

```ini
ExecStart=/opt/timemachine/backend/venv/bin/uvicorn app.main:app \
    --log-config /etc/timemachine/logging.json
```

## See Also

- [Getting Started Guide](getting-started.md)
- [Troubleshooting Guide](troubleshooting.md)
- [API Documentation](http://raspberrypi.local/api/docs)

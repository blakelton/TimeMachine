# TimeMachine Configuration Reference

Complete reference for all TimeMachine configuration options.

## Table of Contents

- [Environment Variables](#environment-variables)
- [Database Configuration](#database-configuration)
- [Authentication](#authentication)
- [CORS Configuration](#cors-configuration)
- [Rate Limiting](#rate-limiting)
- [Logging](#logging)
- [Camera Settings](#camera-settings)
- [Resource Limits](#resource-limits)
- [Systemd Configuration](#systemd-configuration)
- [Nginx Configuration](#nginx-configuration)

## Environment Variables

All environment variables use the `TIMEMACHINE_` prefix and are loaded from `/etc/timemachine/timemachine.env`.

### Core Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `TIMEMACHINE_DB_PATH` | Path | `/var/lib/timemachine/timemachine.db` | SQLite database file path |
| `TIMEMACHINE_MEDIA_PATH` | Path | `/var/lib/timemachine/media` | Base path for media files |
| `TIMEMACHINE_LOG_LEVEL` | String | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `TIMEMACHINE_ENV` | String | `production` | Environment (development, production) |

### API Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `TIMEMACHINE_API_HOST` | String | `0.0.0.0` | API bind address |
| `TIMEMACHINE_API_PORT` | Integer | `8000` | API bind port |
| `TIMEMACHINE_API_RELOAD` | Boolean | `false` | Enable auto-reload (dev only) |

### Authentication

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `TIMEMACHINE_ENABLE_AUTH` | Boolean | `false` | Enable HTTP Basic Auth |
| `TIMEMACHINE_API_USERNAME` | String | None | API username (required if auth enabled) |
| `TIMEMACHINE_API_PASSWORD` | String | None | API password (required if auth enabled) |

### CORS Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `TIMEMACHINE_CORS_ORIGINS` | String | `["http://localhost:5173"]` | Allowed CORS origins (JSON array) |
| `TIMEMACHINE_CORS_CREDENTIALS` | Boolean | `true` | Allow credentials in CORS |

### Rate Limiting

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `TIMEMACHINE_RATE_LIMIT_ENABLED` | Boolean | `true` | Enable rate limiting |
| `TIMEMACHINE_RATE_LIMIT_REQUESTS` | Integer | `100` | Requests per window |
| `TIMEMACHINE_RATE_LIMIT_WINDOW` | Integer | `60` | Window size in seconds |

### Resource Limits

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `TIMEMACHINE_MAX_MEMORY_MB` | Integer | `700` | Maximum memory usage (MB) |
| `TIMEMACHINE_MIN_DISK_MB` | Integer | `500` | Minimum disk space required (MB) |
| `TIMEMACHINE_PREVIEW_PORT_BASE` | Integer | `8080` | Base port for preview streams |

## Database Configuration

TimeMachine uses SQLite with Write-Ahead Logging (WAL) mode for optimal SD card performance.

### Default Settings

```python
# Database location
TIMEMACHINE_DB_PATH=/var/lib/timemachine/timemachine.db

# WAL mode (automatic)
PRAGMA journal_mode=WAL
PRAGMA synchronous=NORMAL

# Memory mapping
PRAGMA mmap_size=268435456  # 256MB

# Cache size
PRAGMA cache_size=-64000  # 64MB
```

### Production Recommendations

```bash
# Use USB storage for database
TIMEMACHINE_DB_PATH=/mnt/usb/timemachine/timemachine.db

# Ensure directory exists and has correct permissions
sudo mkdir -p /mnt/usb/timemachine
sudo chown timemachine:timemachine /mnt/usb/timemachine
```

### Database Backup

Automatic backup configuration:

```bash
# Backup location (via timemachine backup command)
/var/backups/timemachine/timemachine_YYYYMMDD_HHMMSS.tar.gz

# Backup schedule (cron example)
# Daily at 2 AM
0 2 * * * /usr/local/bin/timemachine backup
```

## Authentication

TimeMachine supports optional HTTP Basic Authentication.

### Disable Authentication (Default)

```bash
# /etc/timemachine/timemachine.env
TIMEMACHINE_ENABLE_AUTH=false
```

No authentication required - suitable for trusted networks.

### Enable Authentication

```bash
# /etc/timemachine/timemachine.env
TIMEMACHINE_ENABLE_AUTH=true
TIMEMACHINE_API_USERNAME=admin
TIMEMACHINE_API_PASSWORD=your-secure-password-here
```

**Security Notes:**
- Use strong passwords (16+ characters)
- Change default password immediately
- Consider using HTTPS with Let's Encrypt
- Passwords are compared using constant-time comparison

### Testing Authentication

```bash
# Without auth (should fail)
curl http://localhost:8000/api/v1/health

# With auth
curl -u admin:password http://localhost:8000/api/v1/health
```

## CORS Configuration

Configure Cross-Origin Resource Sharing for frontend access.

### Development

```bash
# Allow localhost development server
TIMEMACHINE_CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

### Production

```bash
# Allow specific domain
TIMEMACHINE_CORS_ORIGINS=["https://timemachine.example.com"]

# Allow multiple domains
TIMEMACHINE_CORS_ORIGINS=["https://timemachine.example.com","https://backup.example.com"]
```

### All Origins (Not Recommended)

```bash
# Allow all origins (use only for testing)
TIMEMACHINE_CORS_ORIGINS=["*"]
```

## Rate Limiting

Protect API from abuse with rate limiting.

### Default Configuration

```bash
# Enable rate limiting
TIMEMACHINE_RATE_LIMIT_ENABLED=true

# 100 requests per 60 seconds
TIMEMACHINE_RATE_LIMIT_REQUESTS=100
TIMEMACHINE_RATE_LIMIT_WINDOW=60
```

### Custom Limits

```bash
# Stricter limits for public deployments
TIMEMACHINE_RATE_LIMIT_REQUESTS=30
TIMEMACHINE_RATE_LIMIT_WINDOW=60

# Relaxed limits for trusted networks
TIMEMACHINE_RATE_LIMIT_REQUESTS=1000
TIMEMACHINE_RATE_LIMIT_WINDOW=60

# Disable rate limiting (not recommended)
TIMEMACHINE_RATE_LIMIT_ENABLED=false
```

## Logging

Configure structured logging with JSON output.

### Log Levels

```bash
# DEBUG - Verbose output for development
TIMEMACHINE_LOG_LEVEL=DEBUG

# INFO - Normal operation (default)
TIMEMACHINE_LOG_LEVEL=INFO

# WARNING - Only warnings and errors
TIMEMACHINE_LOG_LEVEL=WARNING

# ERROR - Only errors
TIMEMACHINE_LOG_LEVEL=ERROR
```

### Log Format

Logs use structured JSON format:

```json
{
  "event": "camera_preview_started",
  "camera_id": 1,
  "device": "/dev/video0",
  "port": 8081,
  "pid": 12345,
  "timestamp": "2025-01-15T10:30:45.123Z",
  "level": "info"
}
```

### Viewing Logs

```bash
# Follow all logs
timemachine logs

# Error logs only
timemachine logs-error

# Systemd journal (last 100 lines)
sudo journalctl -u timemachine -n 100

# JSON log parsing with jq
sudo journalctl -u timemachine -o json | jq -r '.MESSAGE'
```

### Log Rotation

Systemd handles log rotation automatically:

```bash
# Check journal size
sudo journalctl --disk-usage

# Vacuum old logs (keep last 100MB)
sudo journalctl --vacuum-size=100M

# Vacuum by time (keep last 30 days)
sudo journalctl --vacuum-time=30d
```

## Camera Settings

Camera-specific configuration and tuning.

### Preview Settings

```bash
# Base port for preview streams
TIMEMACHINE_PREVIEW_PORT_BASE=8080

# Camera 0 preview: http://raspberrypi:8080
# Camera 1 preview: http://raspberrypi:8081
# Camera 2 preview: http://raspberrypi:8082
```

### CSI Camera Settings

CSI cameras use libcamera with default settings:
- Resolution: 1920x1080
- Preview framerate: 15 fps
- Recording framerate: 30 fps
- JPEG quality: 50 (preview), 95 (still)
- H.264 bitrate: 4 Mbps

### USB Camera Settings

USB cameras use V4L2 with GStreamer:
- Resolution: 1920x1080
- Framerate: 30 fps
- JPEG quality: 50 (preview), 95 (still)
- H.264 bitrate: 4 Mbps

### Custom Camera Settings

Modify [backend/app/services/camera/preview.py](../backend/app/services/camera/preview.py) to customize:
- Resolution
- Framerate
- Quality
- Bitrate
- Color settings

## Resource Limits

### Memory Limits

```bash
# Application memory limit
TIMEMACHINE_MAX_MEMORY_MB=700

# Systemd enforces hard limit
MemoryMax=800M
MemoryHigh=700M
```

**Raspberry Pi 3 Constraints:**
- Total RAM: 1GB
- OS overhead: ~200MB
- TimeMachine limit: 700MB
- Safety buffer: 100MB

### Disk Space Limits

```bash
# Minimum free disk space required
TIMEMACHINE_MIN_DISK_MB=500
```

Operations fail gracefully if disk space falls below minimum.

### CPU Limits

```bash
# Systemd CPU quota (300% = 3 cores)
CPUQuota=300%
```

Prevents TimeMachine from monopolizing CPU on multi-core systems.

### Encoder Limit

**Single H.264 hardware encoder:**
- Only one recording at a time
- EncoderSemaphore manages access
- Recordings queue if encoder busy

## Systemd Configuration

Service configuration in `/etc/systemd/system/timemachine.service`.

### Key Settings

```ini
[Service]
Type=exec
User=timemachine
WorkingDirectory=/opt/timemachine/backend

# Resource limits
MemoryMax=800M
MemoryHigh=700M
CPUQuota=300%

# Camera access
SupplementaryGroups=video
DeviceAllow=/dev/video* rw
DeviceAllow=/dev/vchiq rw

# Restart policy
Restart=on-failure
RestartSec=5s
```

### Modifying Service

```bash
# Edit service file
sudo nano /etc/systemd/system/timemachine.service

# Reload systemd
sudo systemctl daemon-reload

# Restart service
sudo systemctl restart timemachine
```

## Nginx Configuration

Reverse proxy configuration in `/etc/nginx/sites-available/timemachine`.

### Key Settings

```nginx
upstream timemachine_backend {
  server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
}

# API and WebSocket proxy
location /api/ {
  proxy_pass http://timemachine_backend;
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
}

# Media file serving
location /media/ {
  alias /var/lib/timemachine/media/;
  autoindex off;  # Security
}

# Preview stream proxy
location ~ ^/preview/(\d+)$ {
  set $preview_port $1;
  proxy_pass http://127.0.0.1:$preview_port;
}
```

### HTTPS Configuration (Optional)

```nginx
server {
  listen 443 ssl http2;
  server_name timemachine.example.com;

  ssl_certificate /etc/letsencrypt/live/timemachine.example.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/timemachine.example.com/privkey.pem;

  # Mozilla modern configuration
  ssl_protocols TLSv1.3;
  ssl_prefer_server_ciphers off;
}
```

### Client Limits

```nginx
# Request size limits
client_max_body_size 100M;

# Timeout settings
proxy_connect_timeout 60s;
proxy_send_timeout 60s;
proxy_read_timeout 60s;
```

## Example Configurations

### Development

```bash
# /etc/timemachine/timemachine.env
TIMEMACHINE_ENV=development
TIMEMACHINE_LOG_LEVEL=DEBUG
TIMEMACHINE_API_RELOAD=true
TIMEMACHINE_ENABLE_AUTH=false
TIMEMACHINE_CORS_ORIGINS=["http://localhost:5173"]
TIMEMACHINE_RATE_LIMIT_ENABLED=false
```

### Production (Local Network)

```bash
# /etc/timemachine/timemachine.env
TIMEMACHINE_ENV=production
TIMEMACHINE_LOG_LEVEL=INFO
TIMEMACHINE_ENABLE_AUTH=false
TIMEMACHINE_CORS_ORIGINS=["http://raspberrypi.local"]
TIMEMACHINE_RATE_LIMIT_ENABLED=true
TIMEMACHINE_RATE_LIMIT_REQUESTS=100
```

### Production (Public Internet)

```bash
# /etc/timemachine/timemachine.env
TIMEMACHINE_ENV=production
TIMEMACHINE_LOG_LEVEL=WARNING
TIMEMACHINE_ENABLE_AUTH=true
TIMEMACHINE_API_USERNAME=admin
TIMEMACHINE_API_PASSWORD=your-strong-password-here
TIMEMACHINE_CORS_ORIGINS=["https://timemachine.example.com"]
TIMEMACHINE_RATE_LIMIT_ENABLED=true
TIMEMACHINE_RATE_LIMIT_REQUESTS=30
```

## Validation

### Check Configuration

```bash
# Test configuration syntax
sudo -u timemachine /opt/timemachine/venv/bin/python -c "
from app.core.config import settings
print(f'DB Path: {settings.db_path}')
print(f'Media Path: {settings.media_path}')
print(f'Auth Enabled: {settings.enable_auth}')
"

# View loaded configuration
curl http://localhost:8000/api/v1/system/stats | jq
```

### Restart After Changes

```bash
# Restart service to apply changes
sudo timemachine restart

# Check logs for errors
timemachine logs-error
```

## Security Recommendations

1. **Change default passwords** if authentication enabled
2. **Use HTTPS** for public deployments (Let's Encrypt)
3. **Enable rate limiting** to prevent abuse
4. **Restrict CORS origins** to known domains
5. **Regular backups** of database and configuration
6. **Monitor logs** for suspicious activity
7. **Keep system updated** with security patches
8. **Use USB storage** for media files (not exposed to internet)

## Performance Tuning

### High-Performance Settings

```bash
# Increase cache size for database
# Edit /etc/timemachine/custom.sql
PRAGMA cache_size=-128000  # 128MB

# Increase rate limits for high-traffic
TIMEMACHINE_RATE_LIMIT_REQUESTS=1000
TIMEMACHINE_RATE_LIMIT_WINDOW=60

# Use ramdisk for temporary preview frames (optional)
# Add to /etc/fstab:
tmpfs /tmp tmpfs defaults,size=128M 0 0
```

### Low-Resource Settings

```bash
# Reduce memory limits
TIMEMACHINE_MAX_MEMORY_MB=500

# Lower cache size
PRAGMA cache_size=-32000  # 32MB

# Stricter rate limits
TIMEMACHINE_RATE_LIMIT_REQUESTS=30

# Lower preview quality/framerate
# (Modify preview.py manually)
```

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for configuration-related issues.

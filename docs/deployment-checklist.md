# TimeMachine - Deployment Checklist

This checklist guides you through deploying TimeMachine to a Raspberry Pi for production use.

## Pre-Deployment Checklist

### Hardware Requirements
- [ ] Raspberry Pi 3B+ or newer (Pi 4/5 recommended)
- [ ] 16GB+ microSD card (Class 10 or UHS-1)
- [ ] 2.5A+ power supply (official Raspberry Pi PSU recommended)
- [ ] Ethernet cable (recommended) or WiFi configured
- [ ] Camera(s): CSI and/or USB
- [ ] Optional: External USB storage or NAS for media

### Software Requirements
- [ ] Raspberry Pi OS (Bullseye or newer) installed
- [ ] SSH enabled for remote access
- [ ] Static IP configured (recommended for production)
- [ ] Internet connection for initial setup

## Phase 1: System Preparation

### 1.1 Update System
```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### 1.2 Install Dependencies
```bash
sudo apt install -y \
  python3.11 python3.11-venv python3-pip \
  nginx git \
  libcamera-dev libcamera-apps \
  gstreamer1.0-tools \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  v4l-utils

# Install Node.js 18+ (for frontend build)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

**Verification:**
```bash
python3.11 --version  # Should be 3.11.x
node --version         # Should be v18.x or newer
libcamera-hello --version
```

- [ ] Python 3.11 installed
- [ ] Node.js 18+ installed
- [ ] libcamera installed
- [ ] GStreamer installed
- [ ] nginx installed

## Phase 2: Application Installation

### 2.1 Clone Repository
```bash
cd /opt
sudo git clone https://github.com/YOUR_USERNAME/timemachine.git
sudo chown -R $USER:$USER /opt/timemachine
cd /opt/timemachine
```

- [ ] Repository cloned to `/opt/timemachine`
- [ ] Permissions set correctly

### 2.2 Run Installation Script
```bash
chmod +x scripts/install.sh
sudo ./scripts/install.sh
```

The install script will:
- Create `timemachine` system user and group
- Set up Python virtual environment
- Install Python dependencies
- Build frontend static files
- Create `/var/lib/timemachine` directories
- Copy systemd service file
- Copy nginx configuration
- Set file permissions

**Verification:**
```bash
# Check user created
id timemachine

# Check directories
ls -la /var/lib/timemachine
ls -la /opt/timemachine/backend/venv

# Check systemd service
systemctl status timemachine
```

- [ ] timemachine user created
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Frontend built
- [ ] Directories created
- [ ] systemd service installed
- [ ] nginx configuration installed

## Phase 3: Configuration

### 3.1 Configure Environment
```bash
sudo nano /etc/timemachine/timemachine.env
```

**Required settings:**
```bash
# Environment
TIMEMACHINE_ENV=production
TIMEMACHINE_LOG_LEVEL=INFO

# Server
TIMEMACHINE_HOST=127.0.0.1
TIMEMACHINE_PORT=8000

# Database
TIMEMACHINE_DB_PATH=/var/lib/timemachine/timemachine.db

# Storage (modify if using external storage)
TIMEMACHINE_MEDIA_PATH=/var/lib/timemachine/media

# CORS (add your Pi's IP address)
TIMEMACHINE_CORS_ORIGINS=http://192.168.1.XXX

# Authentication (HIGHLY RECOMMENDED for production)
TIMEMACHINE_AUTH_ENABLED=true
TIMEMACHINE_AUTH_USERNAME=admin
TIMEMACHINE_AUTH_PASSWORD=CHANGE_ME_TO_SECURE_PASSWORD

# Resource limits
TIMEMACHINE_MIN_MEMORY_MB=100
TIMEMACHINE_MIN_DISK_MB=500
```

- [ ] Environment file configured
- [ ] CORS origins set
- [ ] Authentication enabled with strong password
- [ ] Storage paths verified

### 3.2 Configure nginx
```bash
sudo nano /etc/nginx/sites-available/timemachine
```

**Verify:**
- [ ] `server_name` matches your Pi's hostname or IP
- [ ] Static files path: `/opt/timemachine/static`
- [ ] API proxy: `http://127.0.0.1:8000`
- [ ] WebSocket proxy configured

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/timemachine /etc/nginx/sites-enabled/
sudo nginx -t
```

- [ ] nginx configuration valid
- [ ] Site enabled

### 3.3 Configure systemd
```bash
sudo nano /etc/systemd/system/timemachine.service
```

**Verify:**
- [ ] `EnvironmentFile` points to `/etc/timemachine/timemachine.env`
- [ ] `WorkingDirectory` is `/opt/timemachine/backend`
- [ ] Memory limits appropriate (800MB for Pi 3, can increase for Pi 4/5)
- [ ] Device access includes `/dev/video*`

```bash
sudo systemctl daemon-reload
```

- [ ] systemd service configured
- [ ] daemon reloaded

## Phase 4: Start Services

### 4.1 Start TimeMachine Service
```bash
sudo systemctl enable timemachine
sudo systemctl start timemachine
sudo systemctl status timemachine
```

**Check logs:**
```bash
sudo journalctl -u timemachine -n 50 --no-pager
```

**Look for:**
- "application_starting"
- "database_initialized"
- "stats_broadcaster_started"
- No ERROR messages

- [ ] Service starts successfully
- [ ] No errors in logs
- [ ] Database initialized

### 4.2 Start nginx
```bash
sudo systemctl enable nginx
sudo systemctl restart nginx
sudo systemctl status nginx
```

- [ ] nginx running
- [ ] No errors in nginx logs

## Phase 5: Verification

### 5.1 Test Backend API
```bash
# Health check
curl http://localhost/api/v1/health | jq .

# Stats endpoint
curl http://localhost/api/v1/stats | jq .

# Camera discovery
curl -X POST http://localhost/api/v1/cameras/discover | jq .
```

**Expected results:**
- Health check returns `{"status": "ok"}`
- Stats returns CPU, memory, disk, temperature
- Discovery returns detected cameras

- [ ] Health endpoint working
- [ ] Stats endpoint working
- [ ] Discovery endpoint working

### 5.2 Test Frontend
Open browser and navigate to `http://<pi-ip-address>` or `http://raspberrypi.local`

**Verify:**
- [ ] Login page appears (if auth enabled)
- [ ] Dashboard loads
- [ ] System stats display
- [ ] WebSocket shows "Live Updates"
- [ ] No JavaScript errors in browser console

### 5.3 Test Camera Operations
1. **Add Camera:**
   - Go to Settings > Cameras
   - Click "Add Camera"
   - Fill in detected camera details
   - Save

2. **Test Preview:**
   - Go to camera page
   - Click Preview tab
   - Click "Start Preview"
   - Verify video stream appears

3. **Test Capture:**
   - Go to Capture tab
   - Click "Capture"
   - Verify image captured

- [ ] Camera added successfully
- [ ] Preview working
- [ ] Capture working

## Phase 6: External Storage (Optional)

### 6.1 USB Drive Setup
```bash
# Format drive
sudo mkfs.ext4 /dev/sda1

# Create mount point
sudo mkdir -p /mnt/usb

# Get UUID
sudo blkid /dev/sda1

# Add to fstab
echo "UUID=YOUR_UUID /mnt/usb ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab

# Mount
sudo mount /mnt/usb

# Create media directory
sudo mkdir -p /mnt/usb/timemachine/media
sudo chown -R timemachine:timemachine /mnt/usb/timemachine

# Update environment
sudo nano /etc/timemachine/timemachine.env
# Set: TIMEMACHINE_MEDIA_PATH=/mnt/usb/timemachine/media

# Restart service
sudo systemctl restart timemachine
```

- [ ] External storage mounted
- [ ] Media path updated
- [ ] Permissions set
- [ ] Service restarted

### 6.2 NAS Setup (Alternative)
```bash
# Install NFS client
sudo apt install -y nfs-common

# Create mount point
sudo mkdir -p /mnt/nas

# Test mount
sudo mount -t nfs 192.168.1.NAS_IP:/volume1/timemachine /mnt/nas

# Add to fstab
echo "192.168.1.NAS_IP:/volume1/timemachine /mnt/nas nfs defaults,nofail 0 0" | sudo tee -a /etc/fstab

# Create media directory
sudo mkdir -p /mnt/nas/media
sudo chown -R timemachine:timemachine /mnt/nas

# Update environment and restart (same as USB)
```

- [ ] NAS mounted
- [ ] Media path updated
- [ ] Permissions set
- [ ] Service restarted

## Phase 7: Security Hardening

### 7.1 Firewall Configuration
```bash
# Install ufw
sudo apt install -y ufw

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP (or HTTPS if configured)
sudo ufw allow 80/tcp

# Enable firewall
sudo ufw enable
```

- [ ] Firewall configured
- [ ] Essential ports allowed

### 7.2 HTTPS Setup (Recommended)
```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate (requires domain name)
sudo certbot --nginx -d timemachine.yourdomain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

- [ ] HTTPS configured (if using domain)
- [ ] Auto-renewal tested

### 7.3 Secure Environment File
```bash
sudo chmod 600 /etc/timemachine/timemachine.env
sudo chown root:root /etc/timemachine/timemachine.env
```

- [ ] Environment file permissions secured

## Phase 8: Monitoring Setup

### 8.1 Configure Log Rotation
```bash
sudo nano /etc/logrotate.d/timemachine
```

```
/var/log/timemachine/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 0644 timemachine timemachine
}
```

- [ ] Log rotation configured

### 8.2 Set Up Watchdog (Optional)
```bash
# Already configured in systemd service
# WatchdogSec=60

# Verify service restarts on hang
sudo systemctl show timemachine | grep Watchdog
```

- [ ] Watchdog configured

## Phase 9: Backup Configuration

### 9.1 Create Backup Script
```bash
sudo nano /usr/local/bin/timemachine-backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/mnt/usb/backups"
DATE=$(date +%Y%m%d)

mkdir -p $BACKUP_DIR

# Backup database and config
tar czf $BACKUP_DIR/timemachine-$DATE.tar.gz \
  /var/lib/timemachine/timemachine.db \
  /etc/timemachine/timemachine.env

# Keep only last 7 backups
find $BACKUP_DIR -name "timemachine-*.tar.gz" -mtime +7 -delete
```

```bash
sudo chmod +x /usr/local/bin/timemachine-backup.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /usr/local/bin/timemachine-backup.sh" | sudo crontab -
```

- [ ] Backup script created
- [ ] Cron job scheduled

## Phase 10: Final Verification

### 10.1 System Health Check
```bash
# Check service status
sudo systemctl status timemachine nginx

# Check logs
sudo journalctl -u timemachine -n 20 --no-pager

# Check disk space
df -h

# Check memory
free -h

# Check temperature
vcgencmd measure_temp

# Check throttling
vcgencmd get_throttled
```

- [ ] All services running
- [ ] No errors in logs
- [ ] Sufficient disk space (>10% free)
- [ ] Memory usage acceptable
- [ ] Temperature < 70°C
- [ ] No throttling flags

### 10.2 End-to-End Test
1. [ ] Record 30-second video
2. [ ] Verify file created in media directory
3. [ ] Access video through web interface
4. [ ] Create timelapse (1 min, 10s interval)
5. [ ] Verify timelapse completes
6. [ ] Check system stats during operations
7. [ ] Verify retention policy works (if configured)

## Post-Deployment

### Documentation
- [ ] Document camera names and device paths
- [ ] Document network configuration (IP, hostname)
- [ ] Document login credentials (store securely)
- [ ] Document backup locations

### User Training
- [ ] Demonstrate web interface
- [ ] Show how to add/configure cameras
- [ ] Explain recording workflows
- [ ] Show how to access recorded media
- [ ] Demonstrate system monitoring

### Monitoring Plan
- [ ] Set up remote monitoring (if needed)
- [ ] Configure alerts (email/SMS for failures)
- [ ] Schedule periodic health checks
- [ ] Plan for software updates

## Troubleshooting Reference

If issues occur, refer to:
- [Troubleshooting Guide](troubleshooting.md)
- Service logs: `sudo journalctl -u timemachine -f`
- nginx logs: `sudo tail -f /var/log/nginx/timemachine-error.log`
- System logs: `sudo dmesg | tail -50`

## Success Criteria

Deployment is complete when:
- [ ] All checklist items marked complete
- [ ] Web interface accessible from network
- [ ] Cameras operational (preview, capture, record)
- [ ] Real-time stats updating via WebSocket
- [ ] No errors in service logs
- [ ] System performance acceptable (CPU < 60%, Memory < 700MB)
- [ ] External storage working (if configured)
- [ ] Backups automated
- [ ] User can perform all basic operations

**Deployment Date:** ________________  
**Deployed By:** ________________  
**Pi Model:** ________________  
**Pi IP Address:** ________________  
**Notes:** ________________

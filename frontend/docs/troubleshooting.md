# TimeMachine - Troubleshooting Guide

## Service Issues

### Service Won't Start

**Symptoms**: `systemctl status timemachine` shows "failed" or "inactive"

**Diagnosis**:

```bash
# Check service status
sudo systemctl status timemachine

# View recent logs
sudo journalctl -u timemachine -n 100 --no-pager

# Check for errors
sudo journalctl -u timemachine -p err -n 50
```

**Common causes**:

1. **Port already in use**:
```bash
# Check if port 8000 is occupied
sudo netstat -tlnp | grep 8000

# Kill conflicting process
sudo kill <PID>
```

2. **Missing Python dependencies**:
```bash
cd /opt/timemachine/backend
source venv/bin/activate
pip install -r requirements.txt
```

3. **Database locked**:
```bash
# Stop service
sudo systemctl stop timemachine

# Remove lock file
sudo rm -f /var/lib/timemachine/timemachine.db-shm
sudo rm -f /var/lib/timemachine/timemachine.db-wal

# Start service
sudo systemctl start timemachine
```

4. **Permission issues**:
```bash
# Fix ownership
sudo chown -R timemachine:timemachine /var/lib/timemachine
sudo chown -R timemachine:timemachine /opt/timemachine

# Fix permissions
sudo chmod 755 /var/lib/timemachine
sudo chmod 644 /var/lib/timemachine/timemachine.db
```

### Service Crashes or Restarts Frequently

**Diagnosis**:

```bash
# Check for OOM (Out of Memory) kills
sudo journalctl -u timemachine | grep -i "killed"
sudo dmesg | grep -i "out of memory"

# Check memory usage
free -h
```

**Solutions**:

1. **Increase memory limit**:
```bash
# Edit service file
sudo nano /etc/systemd/system/timemachine.service

# Increase limits
MemoryMax=1G
MemoryHigh=900M

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart timemachine
```

2. **Reduce concurrent operations**:
- Don't run multiple recordings simultaneously
- Stop preview before starting recording
- Close unused browser tabs

3. **Disable auto-restart for debugging**:
```bash
# Edit service file
Restart=no

# Reload
sudo systemctl daemon-reload
```

## Camera Issues

### Camera Not Detected

**Symptoms**: Camera doesn't appear in device list

**Diagnosis**:

```bash
# List video devices
ls -l /dev/video*

# For CSI cameras
libcamera-hello --list-cameras

# For USB cameras
v4l2-ctl --list-devices
```

**Solutions**:

1. **CSI camera not detected**:
```bash
# Enable camera in raspi-config
sudo raspi-config
# Navigate to Interface Options > Camera > Enable

# Reboot
sudo reboot

# Check again
libcamera-hello --list-cameras
```

2. **USB camera not detected**:
```bash
# Check USB devices
lsusb

# Check kernel messages
dmesg | grep -i "video\|camera\|uvc"

# Try different USB port
# Ensure sufficient power supply
```

3. **Permission denied**:
```bash
# Add timemachine user to video group
sudo usermod -a -G video timemachine

# Restart service
sudo systemctl restart timemachine
```

### Preview Won't Start

**Symptoms**: "Start Preview" button doesn't work or shows error

**Diagnosis**:

```bash
# Check logs
sudo journalctl -u timemachine -f

# Test camera manually
libcamera-hello -t 5000  # CSI
ffplay -f v4l2 /dev/video2  # USB
```

**Solutions**:

1. **Camera busy**:
- Stop any other preview or recording
- Check if another application is using the camera
- Restart timemachine service

2. **GStreamer pipeline error**:
```bash
# Test GStreamer directly
gst-launch-1.0 v4l2src device=/dev/video0 ! videoconvert ! autovideosink
```

3. **Memory or CPU limits**:
- Check system stats in dashboard
- Free up resources
- Reduce preview resolution in code

### Recording Fails

**Symptoms**: Recording stops prematurely or fails to start

**Diagnosis**:

```bash
# Check disk space
df -h /var/lib/timemachine

# Check system resources
top
free -h
vcgencmd measure_temp
vcgencmd get_throttled
```

**Solutions**:

1. **Insufficient disk space**:
```bash
# Clean up old files
sudo find /var/lib/timemachine/media -type f -mtime +30 -delete

# Use external storage (see configuration.md)
```

2. **SD card too slow**:
- Use Class 10 or UHS-1 SD card
- Consider external USB storage
- Reduce bitrate: `TIMEMACHINE_DEFAULT_BITRATE=3000000`

3. **Thermal throttling**:
```bash
# Check throttle status
vcgencmd get_throttled

# If throttled (output != 0x0):
# - Improve cooling (heatsink, fan)
# - Reduce workload
# - Lower resolution/FPS
```

4. **H.264 encoder busy**:
- Only one H.264 recording at a time on Pi 3
- Stop other recordings
- Wait for timelapse to complete

## Network Issues

### Can't Access Web Interface

**Symptoms**: Browser shows "Connection refused" or times out

**Diagnosis**:

```bash
# Check if nginx is running
sudo systemctl status nginx

# Check if backend is running
sudo systemctl status timemachine

# Test locally
curl http://localhost/api/v1/health
```

**Solutions**:

1. **nginx not running**:
```bash
# Start nginx
sudo systemctl start nginx

# Check for errors
sudo nginx -t
sudo journalctl -u nginx -n 50
```

2. **Backend not responding**:
```bash
# Restart timemachine
sudo systemctl restart timemachine

# Check if listening
sudo netstat -tlnp | grep 8000
```

3. **Firewall blocking**:
```bash
# Check firewall status
sudo ufw status

# Allow HTTP if needed
sudo ufw allow 80/tcp
```

4. **Wrong IP address**:
```bash
# Find Pi's IP address
hostname -I
ip addr show

# Access via correct IP
# Example: http://192.168.1.100
```

### WebSocket Connection Fails

**Symptoms**: "Disconnected" status in dashboard, stats not updating

**Diagnosis**:

```bash
# Check nginx WebSocket config
sudo nginx -t

# Check backend logs
sudo journalctl -u timemachine | grep -i websocket

# Test WebSocket endpoint
websocat ws://localhost:8000/api/v1/ws  # requires websocat
```

**Solutions**:

1. **nginx WebSocket configuration**:

Ensure `/etc/nginx/sites-available/timemachine` has:

```nginx
location /api/v1/ws {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

2. **Reload nginx**:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Performance Issues

### High CPU Usage

**Diagnosis**:

```bash
# Check CPU usage
top -u timemachine

# Check temperature
vcgencmd measure_temp
```

**Solutions**:

1. **Reduce encoding load**:
```bash
# Lower resolution
TIMEMACHINE_DEFAULT_RESOLUTION=1280x720

# Lower FPS
TIMEMACHINE_DEFAULT_FPS=24

# Lower bitrate
TIMEMACHINE_DEFAULT_BITRATE=2500000
```

2. **Stop unnecessary services**:
```bash
# List running services
systemctl list-units --type=service --state=running

# Disable unnecessary ones
sudo systemctl disable <service-name>
```

3. **Improve cooling**:
- Add heatsink
- Add active cooling fan
- Improve airflow

### High Memory Usage

**Diagnosis**:

```bash
# Check memory
free -h

# Check process memory
ps aux --sort=-%mem | head -10
```

**Solutions**:

1. **Increase system memory limit**:
```bash
# Edit /etc/systemd/system/timemachine.service
MemoryMax=1200M  # If Pi has more RAM

sudo systemctl daemon-reload
sudo systemctl restart timemachine
```

2. **Reduce buffer sizes** (requires code change):
- Lower preview quality
- Reduce WebSocket broadcast frequency

### Slow Web Interface

**Symptoms**: Pages load slowly, UI lags

**Solutions**:

1. **Use Ethernet instead of WiFi**
2. **Clear browser cache**
3. **Use modern browser** (Chrome, Firefox, Edge)
4. **Close unused browser tabs**
5. **Check network latency**:
```bash
ping <pi-ip-address>
```

## Database Issues

### Database Locked

**Symptoms**: "database is locked" errors in logs

**Solutions**:

```bash
# Stop service
sudo systemctl stop timemachine

# Remove WAL files
sudo rm -f /var/lib/timemachine/timemachine.db-shm
sudo rm -f /var/lib/timemachine/timemachine.db-wal

# Check database integrity
sqlite3 /var/lib/timemachine/timemachine.db "PRAGMA integrity_check;"

# Start service
sudo systemctl start timemachine
```

### Database Corruption

**Symptoms**: Service fails to start with database errors

**Recovery**:

```bash
# Stop service
sudo systemctl stop timemachine

# Backup corrupted database
sudo cp /var/lib/timemachine/timemachine.db \
     /var/lib/timemachine/timemachine.db.corrupt

# Try to repair
sqlite3 /var/lib/timemachine/timemachine.db ".recover" | \
  sqlite3 /var/lib/timemachine/timemachine.db.recovered

# If recovery works, replace
sudo mv /var/lib/timemachine/timemachine.db.recovered \
     /var/lib/timemachine/timemachine.db

# If recovery fails, start fresh (LOSES DATA)
sudo rm /var/lib/timemachine/timemachine.db
sudo systemctl start timemachine  # Creates new DB
```

## Storage Issues

### Retention Not Working

**Symptoms**: Old files not being deleted automatically

**Diagnosis**:

```bash
# Check retention job logs
sudo journalctl -u timemachine | grep retention

# Check environment variables
sudo cat /etc/timemachine/timemachine.env | grep RETENTION
```

**Solutions**:

1. **Verify retention settings**:
```bash
# Edit config
sudo nano /etc/timemachine/timemachine.env

# Ensure values are set
TIMEMACHINE_RETENTION_DAYS=30
TIMEMACHINE_RETENTION_MAX_GB=50

# Restart service
sudo systemctl restart timemachine
```

2. **Manual cleanup**:
```bash
# Delete files older than 30 days
sudo find /var/lib/timemachine/media -type f -mtime +30 -delete
```

### Files Not Accessible

**Symptoms**: Can't view recorded videos or images

**Diagnosis**:

```bash
# Check file permissions
ls -la /var/lib/timemachine/media/recordings/

# Check nginx media serving config
sudo nginx -t
```

**Solutions**:

1. **Fix permissions**:
```bash
sudo chown -R timemachine:timemachine /var/lib/timemachine/media
sudo chmod -R 755 /var/lib/timemachine/media
```

2. **Check nginx configuration**:

Ensure `/etc/nginx/sites-available/timemachine` has:

```nginx
location /media/ {
    alias /var/lib/timemachine/media/;
    autoindex off;
}
```

## Logging and Debugging

### Enable Debug Logging

```bash
# Edit environment
sudo nano /etc/timemachine/timemachine.env

# Set debug level
TIMEMACHINE_LOG_LEVEL=DEBUG

# Restart service
sudo systemctl restart timemachine

# View debug logs
sudo journalctl -u timemachine -f
```

### Collect Diagnostic Information

```bash
# Create diagnostic report
cat > /tmp/timemachine-diag.txt << EOF
=== System Info ===
$(uname -a)
$(cat /etc/os-release)

=== Service Status ===
$(sudo systemctl status timemachine)

=== Recent Logs ===
$(sudo journalctl -u timemachine -n 100 --no-pager)

=== Disk Space ===
$(df -h)

=== Memory ===
$(free -h)

=== Temperature ===
$(vcgencmd measure_temp)

=== Throttling ===
$(vcgencmd get_throttled)

=== Cameras ===
$(ls -l /dev/video*)

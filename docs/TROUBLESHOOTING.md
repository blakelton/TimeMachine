# TimeMachine Troubleshooting Guide

Common issues and solutions for TimeMachine Observation Chamber.

## Table of Contents

- [Service Issues](#service-issues)
- [Camera Problems](#camera-problems)
- [Database Issues](#database-issues)
- [Network and API Issues](#network-and-api-issues)
- [Performance Problems](#performance-problems)
- [Resource Exhaustion](#resource-exhaustion)
- [GStreamer Errors](#gstreamer-errors)
- [Nginx Issues](#nginx-issues)

## Service Issues

### Service Won't Start

**Symptom:** `sudo systemctl start timemachine` fails

**Check status:**
```bash
sudo systemctl status timemachine
```

**Common causes:**

1. **Missing dependencies:**
   ```bash
   # Verify Python packages
   /opt/timemachine/venv/bin/pip list

   # Reinstall requirements
   sudo -u timemachine /opt/timemachine/venv/bin/pip install -r /opt/timemachine/requirements.txt
   ```

2. **Database permission error:**
   ```bash
   # Check database permissions
   ls -l /var/lib/timemachine/

   # Fix permissions
   sudo chown -R timemachine:timemachine /var/lib/timemachine
   ```

3. **Port already in use:**
   ```bash
   # Check if port 8000 is in use
   sudo lsof -i :8000

   # Kill conflicting process or change port in config
   ```

4. **Invalid configuration:**
   ```bash
   # Test config syntax
   sudo -u timemachine /opt/timemachine/venv/bin/python -c "from app.core.config import settings"

   # Check for typos in /etc/timemachine/timemachine.env
   ```

### Service Crashes on Startup

**Check logs:**
```bash
timemachine logs-error
# or
sudo journalctl -u timemachine -n 100
```

**Common errors:**

1. **Import error:**
   ```
   ModuleNotFoundError: No module named 'app'
   ```
   **Fix:** Working directory must be `/opt/timemachine/backend`
   ```bash
   # Check systemd service WorkingDirectory
   sudo nano /etc/systemd/system/timemachine.service
   ```

2. **Database locked:**
   ```
   sqlite3.OperationalError: database is locked
   ```
   **Fix:** Kill all processes using database
   ```bash
   # Find processes
   sudo fuser /var/lib/timemachine/timemachine.db

   # Kill if safe
   sudo fuser -k /var/lib/timemachine/timemachine.db
   ```

3. **Memory limit exceeded:**
   ```
   systemd[1]: timemachine.service: A process of this unit has been killed by the OOM killer.
   ```
   **Fix:** Increase memory limit or reduce usage
   ```bash
   # Edit service file
   sudo nano /etc/systemd/system/timemachine.service
   # Increase MemoryMax=1000M

   sudo systemctl daemon-reload
   sudo systemctl restart timemachine
   ```

### Service Restarts Frequently

**Check restart count:**
```bash
sudo systemctl show timemachine | grep NRestarts
```

**Common causes:**

1. **GStreamer pipeline crashes:**
   ```bash
   # Check logs for pipeline errors
   timemachine logs | grep pipeline

   # Managed pipelines should auto-restart
   # If persistent, check camera connection
   ```

2. **Memory pressure:**
   ```bash
   # Check memory usage
   timemachine check

   # Monitor during operation
   watch -n 1 free -h
   ```

3. **Deadlock or timeout:**
   ```bash
   # Check for stuck processes
   ps aux | grep gst-launch

   # Kill hung processes
   sudo killall gst-launch-1.0
   ```

## Camera Problems

### No Cameras Detected

**Run discovery manually:**
```bash
curl -X POST http://localhost:8000/api/v1/cameras/discover
```

**Check CSI camera:**
```bash
# Test with libcamera
libcamera-hello --list-cameras

# Expected output:
# Available cameras
# 0 : imx219 [3280x2464] (/base/soc/i2c0mux/i2c@1/imx219@10)
```

**Troubleshooting CSI:**
```bash
# Check camera connection
vcgencmd get_camera

# Expected: supported=1 detected=1

# Enable camera in raspi-config
sudo raspi-config
# Interface Options → Camera → Enable

# Reboot
sudo reboot
```

**Check USB camera:**
```bash
# List video devices
ls -l /dev/video*

# Get camera info
v4l2-ctl --list-devices

# Test capture
v4l2-ctl -d /dev/video0 --list-formats-ext
```

**Troubleshooting USB:**
```bash
# Check USB devices
lsusb

# Check dmesg for errors
dmesg | grep video

# Common issue: insufficient power
# Use powered USB hub for multiple cameras
```

### Camera Permission Denied

**Error:**
```
Permission denied: /dev/video0
```

**Fix:**
```bash
# Add timemachine user to video group
sudo usermod -aG video timemachine

# Verify
groups timemachine

# Restart service
sudo systemctl restart timemachine
```

### Preview Stream Not Working

**Check preview status:**
```bash
curl http://localhost:8000/api/v1/cameras/1/preview/status
```

**Test preview port directly:**
```bash
# Preview streams on ports 8080+
curl http://localhost:8080
```

**Common issues:**

1. **Pipeline not running:**
   ```bash
   # Check GStreamer processes
   ps aux | grep gst-launch

   # Check logs
   timemachine logs | grep preview
   ```

2. **Port blocked:**
   ```bash
   # Check firewall
   sudo ufw status

   # Allow preview ports
   sudo ufw allow 8080:8089/tcp
   ```

3. **Nginx proxy issue:**
   ```bash
   # Test backend directly
   curl http://localhost:8080

   # Check nginx config
   sudo nginx -t

   # Reload nginx
   sudo systemctl reload nginx
   ```

### Recording Fails

**Error:**
```
H.264 encoder busy (in use by camera_1_recording)
```

**Explanation:** Raspberry Pi 3 has only one hardware H.264 encoder.

**Fix:** Stop other recordings first
```bash
# Check active recordings
curl http://localhost:8000/api/v1/cameras

# Stop recording
curl -X POST http://localhost:8000/api/v1/cameras/1/recording/stop
```

**Recording timeout:**
```bash
# Check disk space
df -h /var/lib/timemachine

# Check memory
free -h

# Review logs for errors
timemachine logs | grep recording
```

## Database Issues

### Database Locked

**Error:**
```
sqlite3.OperationalError: database is locked
```

**Immediate fix:**
```bash
# Stop service
sudo systemctl stop timemachine

# Check for lock files
ls -l /var/lib/timemachine/timemachine.db*

# Remove WAL and SHM files (when service stopped)
sudo rm /var/lib/timemachine/timemachine.db-wal
sudo rm /var/lib/timemachine/timemachine.db-shm

# Start service
sudo systemctl start timemachine
```

**Long-term fix:**
```bash
# Ensure WAL mode is enabled
sudo -u timemachine /opt/timemachine/venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('/var/lib/timemachine/timemachine.db')
conn.execute('PRAGMA journal_mode=WAL')
conn.close()
"
```

### Database Corruption

**Symptoms:**
- Service won't start
- SQL errors in logs
- Incomplete data

**Check integrity:**
```bash
sqlite3 /var/lib/timemachine/timemachine.db "PRAGMA integrity_check;"
```

**Restore from backup:**
```bash
# List backups
ls -lh /var/backups/timemachine/

# Restore (CAUTION: Overwrites current database)
sudo timemachine restore /var/backups/timemachine/timemachine_20250115_020000.tar.gz
```

**Rebuild database (last resort):**
```bash
# Backup current database
sudo cp /var/lib/timemachine/timemachine.db /var/lib/timemachine/timemachine.db.broken

# Remove database
sudo rm /var/lib/timemachine/timemachine.db*

# Reinitialize
sudo -u timemachine /opt/timemachine/venv/bin/python -c "
import asyncio
from app.db.session import init_db
asyncio.run(init_db())
"

# Restart service
sudo systemctl restart timemachine
```

### Migration Errors

**Error during upgrade:**
```
alembic.util.exc.CommandError: Can't locate revision identified by 'xxxxx'
```

**Fix:**
```bash
# Check current revision
cd /opt/timemachine/backend
source ../venv/bin/activate
alembic current

# Stamp database to latest revision
alembic stamp head

# Run migrations
alembic upgrade head
```

## Network and API Issues

### API Not Responding

**Check service:**
```bash
# Service status
sudo systemctl status timemachine

# Test API directly
curl http://localhost:8000/api/v1/health
```

**Check nginx:**
```bash
# Nginx status
sudo systemctl status nginx

# Test nginx config
sudo nginx -t

# Reload if needed
sudo systemctl reload nginx
```

**Network connectivity:**
```bash
# Check listening ports
sudo netstat -tlnp | grep 8000

# Check firewall
sudo ufw status
```

### CORS Errors

**Browser error:**
```
Access to fetch at 'http://raspberrypi:8000' from origin 'http://localhost:5173'
has been blocked by CORS policy
```

**Fix:**
```bash
# Edit environment
sudo nano /etc/timemachine/timemachine.env

# Add frontend origin
TIMEMACHINE_CORS_ORIGINS=["http://localhost:5173","http://raspberrypi.local"]

# Restart service
sudo systemctl restart timemachine
```

### WebSocket Connection Failed

**Check WebSocket endpoint:**
```bash
# Test WebSocket with wscat
npm install -g wscat
wscat -c ws://localhost:8000/api/v1/ws
```

**Check nginx WebSocket config:**
```bash
# Verify nginx has WebSocket proxy settings
sudo nano /etc/nginx/sites-available/timemachine

# Should have:
# proxy_http_version 1.1;
# proxy_set_header Upgrade $http_upgrade;
# proxy_set_header Connection "upgrade";
```

### Authentication Failures

**Error:**
```
401 Unauthorized
```

**Check credentials:**
```bash
# Test with correct credentials
curl -u username:password http://localhost:8000/api/v1/health

# Verify environment config
sudo cat /etc/timemachine/timemachine.env | grep AUTH
```

**Reset password:**
```bash
# Edit environment
sudo nano /etc/timemachine/timemachine.env

# Change password
TIMEMACHINE_API_PASSWORD=new-secure-password

# Restart service
sudo systemctl restart timemachine
```

## Performance Problems

### High CPU Usage

**Check processes:**
```bash
top -u timemachine

# Look for gst-launch processes
```

**Common causes:**

1. **Multiple preview streams:**
   - Each preview uses ~20-30% CPU
   - Limit concurrent previews to 2-3

2. **High framerate/quality:**
   - Reduce preview framerate from 30fps to 15fps
   - Lower JPEG quality from 50 to 30

3. **Encoding overhead:**
   - H.264 encoding uses significant CPU
   - Only one recording at a time

**Mitigation:**
```bash
# Stop unnecessary previews
curl -X POST http://localhost:8000/api/v1/cameras/1/preview/stop

# Monitor CPU
watch -n 1 'top -b -n 1 -u timemachine | head -20'
```

### High Memory Usage

**Check memory:**
```bash
timemachine check

# Detailed memory breakdown
sudo systemctl status timemachine | grep Memory
```

**Common causes:**

1. **Memory leak in pipeline:**
   - Restart service to clear
   - Check for GStreamer memory leaks

2. **Large database cache:**
   - Reduce cache size in database pragmas

3. **Multiple active operations:**
   - Limit concurrent cameras
   - Stop unnecessary previews

**Mitigation:**
```bash
# Restart service to clear memory
sudo systemctl restart timemachine

# Reduce memory limit to force cleanup
sudo nano /etc/systemd/system/timemachine.service
# MemoryMax=600M

sudo systemctl daemon-reload
sudo systemctl restart timemachine
```

### Slow API Responses

**Check system load:**
```bash
uptime

# Load average should be < number of CPU cores
```

**Database performance:**
```bash
# Check database size
ls -lh /var/lib/timemachine/timemachine.db

# Vacuum database
sudo -u timemachine sqlite3 /var/lib/timemachine/timemachine.db "VACUUM;"

# Analyze for query optimization
sudo -u timemachine sqlite3 /var/lib/timemachine/timemachine.db "ANALYZE;"
```

**SD card performance:**
```bash
# Test write speed
sudo dd if=/dev/zero of=/var/lib/timemachine/test.img bs=1M count=100 oflag=direct

# If slow, consider USB storage
```

## Resource Exhaustion

### Out of Memory (OOM)

**Symptoms:**
- Service crashes
- Kernel messages about OOM killer

**Check logs:**
```bash
dmesg | grep -i oom
sudo journalctl -k | grep -i "killed process"
```

**Fix:**
```bash
# Increase swap
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# CONF_SWAPSIZE=1024
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Reduce memory usage
# Stop unnecessary services
sudo systemctl stop bluetooth
sudo systemctl disable bluetooth
```

### Disk Full

**Check space:**
```bash
df -h /var/lib/timemachine
```

**Clean up:**
```bash
# Find large recordings
find /var/lib/timemachine/media -type f -size +100M -exec ls -lh {} \;

# Delete old recordings
find /var/lib/timemachine/media/recordings -mtime +30 -delete

# Delete old stills
find /var/lib/timemachine/media/stills -mtime +7 -delete
```

**Automate cleanup:**
```bash
# Add cron job
sudo crontab -e

# Delete recordings older than 30 days (daily at 3 AM)
0 3 * * * find /var/lib/timemachine/media/recordings -mtime +30 -delete
```

### USB Bandwidth Exhaustion

**Symptoms:**
- Dropped frames
- USB devices disconnecting
- Slow network (if using USB ethernet)

**Solutions:**
```bash
# Use CSI camera instead of USB when possible

# Lower USB camera resolution/framerate

# Use Ethernet via GPIO header instead of USB

# Limit concurrent USB cameras to 2

# Use powered USB hub
```

## GStreamer Errors

### Pipeline Construction Failed

**Error:**
```
WARNING: erroneous pipeline: no element "libcamerasrc"
```

**Fix:**
```bash
# Install missing GStreamer plugins
sudo apt install gstreamer1.0-libcamera

# Verify installation
gst-inspect-1.0 libcamerasrc
```

### Element Linking Failed

**Error:**
```
Could not link v4l2src to capsfilter
```

**Troubleshooting:**
```bash
# Test pipeline manually
gst-launch-1.0 v4l2src device=/dev/video0 ! video/x-raw,width=1920,height=1080 ! fakesink

# Check supported formats
v4l2-ctl -d /dev/video0 --list-formats-ext
```

### Encoder Not Available

**Error:**
```
No element "v4l2h264enc"
```

**Fix:**
```bash
# Install V4L2 encoder plugin
sudo apt install gstreamer1.0-plugins-good

# Verify
gst-inspect-1.0 v4l2h264enc

# If still missing, use software encoder (slow)
# Replace v4l2h264enc with x264enc in pipeline config
```

## Nginx Issues

### 502 Bad Gateway

**Check backend:**
```bash
# Is backend running?
curl http://localhost:8000/api/v1/health

# Check backend logs
timemachine logs-error
```

**Check nginx config:**
```bash
# Test config
sudo nginx -t

# Check nginx error log
sudo tail -f /var/log/nginx/error.log
```

**Fix:**
```bash
# Restart both services
sudo systemctl restart timemachine
sudo systemctl restart nginx
```

### Static Files Not Served

**Check nginx config:**
```bash
sudo nano /etc/nginx/sites-available/timemachine

# Verify media location
location /media/ {
  alias /var/lib/timemachine/media/;
}
```

**Check permissions:**
```bash
# Nginx user needs read access
sudo chmod 755 /var/lib/timemachine/media
sudo chmod 644 /var/lib/timemachine/media/recordings/*
```

## Getting Help

If you can't resolve your issue:

1. **Gather information:**
   ```bash
   # Run health check
   timemachine check

   # Collect logs
   timemachine logs-error > /tmp/timemachine-error.log

   # System info
   uname -a > /tmp/system-info.txt
   cat /proc/cpuinfo >> /tmp/system-info.txt
   free -h >> /tmp/system-info.txt
   df -h >> /tmp/system-info.txt
   ```

2. **Check GitHub issues:**
   - Search existing issues
   - Check closed issues for solutions

3. **Create detailed issue report:**
   - Describe problem clearly
   - Include error messages
   - Attach logs
   - Specify hardware (Pi model, cameras)
   - List software versions

4. **Community support:**
   - Raspberry Pi forums
   - GStreamer mailing list
   - FastAPI Discord

## Preventive Maintenance

**Weekly:**
- Check disk space: `df -h`
- Review error logs: `timemachine logs-error`
- Test camera discovery

**Monthly:**
- Run health check: `timemachine check`
- Backup database: `timemachine backup`
- Update system: `sudo apt update && sudo apt upgrade`

**Quarterly:**
- Clean old recordings
- Vacuum database
- Review performance metrics
- Update TimeMachine: `timemachine update`

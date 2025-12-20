# Troubleshooting Log: CSI Camera Discovery on Raspberry Pi 4

**Status**: 🟡 INVESTIGATING
**Created**: 2025-12-20
**Last Updated**: 2025-12-20
**Failed Attempts**: 0 (initial setup, not yet verified)

---

## Project Goal

TimeMachine is a temperature-controlled observation chamber management system for Raspberry Pi. The goal is to support both USB webcams and CSI cameras (connected via ribbon cable) for recording, timelapse, and live preview functionality.

**Current Hardware Setup:**
- Raspberry Pi 4 (replaced faulty Pi 3)
- Debian Trixie (Python 3.13)
- 2x USB microscope cameras (working, already in database)
- 1x CSI camera: OV5647 (connected via ribbon cable, needs verification)
- 1x DSI display (ribbon cable, not yet configured)

---

## Related Files

| File | Purpose |
|------|---------|
| [backend/app/services/camera/discovery.py](backend/app/services/camera/discovery.py) | Camera discovery logic - CSI and USB detection |
| [backend/app/api/routes/cameras.py](backend/app/api/routes/cameras.py) | Camera API endpoints including `/discover` |
| [scripts/install.sh](scripts/install.sh) | Installation script with all Pi setup fixes |
| [backend/requirements.txt](backend/requirements.txt) | Python dependencies (updated for Python 3.13) |

---

## Current State

### What's Working
1. **TimeMachine installed and running** on Pi 4
2. **USB cameras detected** - 2 microscopes at `/dev/video0` and `/dev/video2`
3. **Web UI accessible** at `http://timemachine.local`
4. **Camera discovery API** - POST `/api/v1/cameras/discover` works
5. **CSI camera hardware detected** - `rpicam-hello --list-cameras` shows OV5647

### What's Not Working (Needs Verification)
1. **CSI camera not appearing in discover endpoint** - The OV5647 wasn't returned by the API
2. **Cause identified**: Discovery code was using `libcamera-hello` which doesn't exist on newer Pi OS (uses `rpicam-hello` instead)

---

## Troubleshooting Log

### [2025-12-20 ~14:00] Initial CSI Discovery Fix
**Attempt**: #1
**Hypothesis**: CSI camera discovery fails because code uses `libcamera-hello` but Pi 4 with newer OS uses `rpicam-hello`
**Action Taken**:
- Updated `discover_csi_cameras()` to try `rpicam-hello` first, then `libcamera-hello`
- Changed device path format from `/dev/video0` to `libcamera:0` for CSI cameras
- Added `rp1-cfe` driver detection for Pi 5 compatibility in v4l2 fallback
- Committed as `d0cd1b0` and pushed to `develop` branch

**Result**: ⏳ PENDING USER VERIFICATION
**Evidence**:
- User confirmed `rpicam-hello --list-cameras` shows the OV5647:
  ```
  0 : ov5647 [2592x1944 10-bit GBRG] (/base/soc/i2c0mux/i2c@1/ov5647@36)
  ```
- Discovery code was only trying `libcamera-hello` which raises `FileNotFoundError`

**Next Steps**:
1. User needs to pull latest code and restart service:
   ```bash
   cd ~/projects/TimeMachine && git pull && sudo systemctl restart timemachine
   ```
2. Test discovery endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/v1/cameras/discover | python3 -m json.tool
   ```
3. Expected result: CSI camera should appear with `device_path: "libcamera:0"`

---

## Key Technical Details

### Camera Discovery Flow
1. `POST /api/v1/cameras/discover` calls `CameraDiscovery.discover_all()`
2. Runs CSI and USB discovery in parallel
3. CSI discovery tries:
   - `rpicam-hello --list-cameras` (newer Pi OS)
   - `libcamera-hello --list-cameras` (older Pi OS)
   - v4l2 fallback checking for `unicam` or `rp1-cfe` drivers
4. USB discovery uses `v4l2-ctl` to find `uvcvideo` devices
5. Results filtered to exclude cameras already in database

### Device Path Convention
- **USB cameras**: `/dev/video0`, `/dev/video2`, etc.
- **CSI cameras**: `libcamera:0`, `libcamera:1`, etc. (new format after fix)

### Important Commands on Pi
```bash
# Check CSI camera detection
rpicam-hello --list-cameras

# Check all video devices
v4l2-ctl --list-devices

# Check specific device info
v4l2-ctl --device /dev/video0 --info

# View service logs
sudo journalctl -u timemachine -f

# Restart service
sudo systemctl restart timemachine

# Test discovery endpoint
curl -X POST http://localhost:8000/api/v1/cameras/discover | python3 -m json.tool

# List cameras in database
curl http://localhost:8000/api/v1/cameras | python3 -m json.tool
```

---

## Next Tasks After CSI Discovery Works

Once the CSI camera appears in discover endpoint:

1. **Add CSI camera to database**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/cameras \
     -H "Content-Type: application/json" \
     -d '{"name": "CSI OV5647", "device_path": "libcamera:0", "camera_type": "csi", "enabled": true}'
   ```

2. **Test preview functionality** - CSI cameras use different capture method than USB

3. **Verify recording works** - May need GStreamer pipeline adjustments for libcamera

4. **Configure DSI display** - User mentioned ribbon cable display, not yet set up

---

## Installation Issues Already Fixed

These were resolved during initial Pi 4 setup (documented in git history):

| Issue | Fix | Commit |
|-------|-----|--------|
| Node.js version check failed when not installed | Check if `node` command exists before getting version | `a1590b0` |
| pydantic build failure on Python 3.13 | Updated to `pydantic>=2.10.0` | `a1590b0` |
| Type generation hung indefinitely | Added 60s timeout to `npx openapi-typescript` | `a1590b0` |
| Database init ran as root | Run as timemachine user with proper env | `a1590b0` |
| Alembic migrations failed | Added PYTHONPATH and env loading | `a1590b0` |
| Nginx showing default page | Added `systemctl reload nginx` after config | `a1590b0` |
| 500 error - nginx couldn't read static files | Added `chmod 755 /opt/timemachine` | `a1590b0` |
| Services not auto-started on fresh install | Always start services, not just on upgrade | `a1590b0` |

---

## Environment Details

- **Pi Model**: Raspberry Pi 4
- **OS**: Debian Trixie
- **Python**: 3.13
- **Node.js**: 22.x
- **Camera stack**: rpicam-apps (libcamera-based)
- **CSI camera**: OV5647 sensor
- **Branch**: `develop`

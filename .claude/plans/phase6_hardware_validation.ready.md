# Phase 6: Hardware Validation

> Full testing on Raspberry Pi with real hardware

**Status**: ready
**Created**: 2025-12-21
**Parent**: [masterplan.md](masterplan.md)
**Depends On**: All previous phases (or subset depending on scope)

---

## Objective

Thoroughly test all TimeMachine features on actual Raspberry Pi hardware with real cameras and sensors. Identify and resolve any hardware-specific issues, optimize performance, and validate long-running stability.

## Prerequisites

- [ ] All (or most) previous phases complete
- [ ] Raspberry Pi 3B+ or 4 available
- [ ] CSI camera module available
- [ ] USB webcam available (optional, for multi-camera testing)
- [ ] DHT22 temperature sensor available
- [ ] Relay module available (for temperature control testing)
- [ ] Heater/cooler device available (optional)

---

## Hardware Test Inventory

### Required Equipment
| Item | Model/Spec | Purpose |
|------|------------|---------|
| Raspberry Pi | 3B+ or 4 (2GB+) | Test platform |
| MicroSD Card | 16GB+ Class 10 | OS and app |
| CSI Camera | Pi Camera V2 or HQ | Primary camera tests |
| USB Storage | 32GB+ | Media storage tests |
| Power Supply | 5V 3A | Stable power |

### Optional Equipment
| Item | Model/Spec | Purpose |
|------|------------|---------|
| USB Webcam | Any V4L2 compatible | Multi-camera tests |
| DHT22 Sensor | AM2302 | Temperature tests |
| Relay Module | 5V 1-channel | Control tests |
| Reference Thermometer | Digital | Calibration |
| Network Cable | Cat5e+ | Stable network |

---

## Test Categories

### 1. Camera Operations

#### 1.1 CSI Camera Tests
- [ ] Camera detection via `libcamera-hello`
- [ ] Preview stream starts and displays
- [ ] Preview stream stops cleanly
- [ ] Still capture saves JPEG correctly
- [ ] Recording starts and encodes H.264
- [ ] Recording stops with clean EOS (no corruption)
- [ ] Timelapse captures at correct intervals
- [ ] Timelapse assembles to video correctly

#### 1.2 USB Camera Tests
- [ ] Camera detection via V4L2
- [ ] Preview stream (may differ from CSI)
- [ ] Still capture
- [ ] Recording (software encoding if needed)

#### 1.3 Multi-Camera Tests
- [ ] Both cameras detected simultaneously
- [ ] Preview one camera while other idle
- [ ] Switch preview between cameras
- [ ] Record from one camera only (H.264 limit)
- [ ] Sequential recording from both cameras

#### 1.4 Edge Cases
- [ ] Camera disconnect during preview
- [ ] Camera disconnect during recording
- [ ] Camera reconnect detection
- [ ] Rapid start/stop cycles
- [ ] Long recordings (1+ hours)

---

### 2. GStreamer Pipeline Validation

#### 2.1 Pipeline Health
- [ ] Pipelines start without errors
- [ ] Memory usage stable during preview
- [ ] Memory usage stable during recording
- [ ] No GStreamer warnings/errors in logs
- [ ] Clean pipeline teardown

#### 2.2 Encoding Tests
- [ ] H.264 hardware encoder utilized
- [ ] Correct resolution and framerate
- [ ] MP4 files playable in VLC
- [ ] File size reasonable for duration

#### 2.3 MJPEG Streaming
- [ ] Preview stream visible in browser
- [ ] Multiple browser tabs can view
- [ ] Stream quality acceptable
- [ ] Bandwidth reasonable

---

### 3. Temperature System Tests

#### 3.1 DHT22 Sensor
- [ ] Sensor detected on GPIO
- [ ] Temperature reading within ±0.5°C of reference
- [ ] Humidity reading reasonable
- [ ] Readings persist to database
- [ ] WebSocket updates received in UI

#### 3.2 Temperature Control
- [ ] Relay switches on command
- [ ] Hysteresis control maintains setpoint
- [ ] Heater ON when below setpoint
- [ ] Heater OFF when above setpoint + hysteresis
- [ ] Safety limits prevent runaway
- [ ] Control events logged

#### 3.3 Sensor Failures
- [ ] Graceful handling of disconnected sensor
- [ ] Alert triggers on sensor failure
- [ ] Control stops safely on sensor failure
- [ ] Recovery when sensor reconnected

---

### 4. Performance Tests

#### 4.1 Memory Usage
- [ ] Baseline memory with no operations
- [ ] Memory during preview
- [ ] Memory during recording
- [ ] Memory during timelapse
- [ ] No memory leaks over 24 hours
- [ ] Stays under 800MB limit

#### 4.2 CPU Usage
- [ ] Baseline CPU idle
- [ ] CPU during preview
- [ ] CPU during recording (H.264 should be low)
- [ ] CPU during timelapse
- [ ] No thermal throttling under load

#### 4.3 Disk I/O
- [ ] Write speed to USB storage
- [ ] Read speed for file serving
- [ ] No I/O bottlenecks during recording

#### 4.4 Network
- [ ] WebSocket latency acceptable
- [ ] Preview stream bandwidth
- [ ] API response times
- [ ] Multiple concurrent clients

---

### 5. Long-Running Stability Tests

#### 5.1 24-Hour Test
- [ ] Service runs 24 hours without crash
- [ ] Memory stable over time
- [ ] No file descriptor leaks
- [ ] Database size reasonable
- [ ] Logs don't fill disk

#### 5.2 Recording Marathon
- [ ] Record continuously for 8 hours
- [ ] File saves correctly
- [ ] No frame drops
- [ ] Disk space estimated correctly

#### 5.3 Timelapse Marathon
- [ ] Run 24-hour timelapse (2880 frames at 30s interval)
- [ ] All frames captured
- [ ] Resume works after interruption
- [ ] Video assembly completes

---

### 6. Web Interface Tests

#### 6.1 Browser Compatibility
- [ ] Chrome on desktop
- [ ] Firefox on desktop
- [ ] Safari on macOS
- [ ] Chrome on Android
- [ ] Safari on iOS

#### 6.2 Responsiveness
- [ ] Mobile layout correct
- [ ] Touch controls work
- [ ] Orientation changes handled

#### 6.3 WebSocket Stability
- [ ] Reconnects after network blip
- [ ] Updates resume after reconnect
- [ ] No duplicate connections

---

### 7. Deployment Tests

#### 7.1 Installation Script
- [ ] Fresh install on clean Raspbian
- [ ] All dependencies installed
- [ ] Service starts successfully
- [ ] Nginx proxy works

#### 7.2 Service Management
- [ ] Start/stop/restart via timemachine command
- [ ] Service auto-starts on boot
- [ ] Logs accessible via journalctl
- [ ] Clean shutdown

#### 7.3 Updates
- [ ] Git pull updates work
- [ ] Database migrations apply
- [ ] Frontend rebuild works

---

## Test Procedures

### Procedure 1: Basic Smoke Test
1. Install TimeMachine on fresh Pi
2. Access web UI from browser
3. Add camera via discovery
4. Start preview (verify video displayed)
5. Capture still (verify file saved)
6. Start/stop 30-second recording
7. Verify MP4 playable
8. Check system stats display

### Procedure 2: 24-Hour Stability Test
1. Start TimeMachine service
2. Start continuous preview
3. Schedule hourly captures
4. Monitor: memory, CPU, disk usage
5. Check for errors every 4 hours
6. After 24 hours, verify:
   - All captures saved
   - No crashes in logs
   - Memory stable
   - No zombie processes

### Procedure 3: Temperature Validation
1. Place DHT22 near reference thermometer
2. Start temperature monitoring
3. Compare readings every hour for 8 hours
4. Calculate deviation
5. Test alert thresholds
6. Test relay control (if available)

---

## Issue Tracking

### Known Issues to Verify
| Issue | Source | Status |
|-------|--------|--------|
| GStreamer EOS handling | Previous testing | Verify fixed |
| Preview reconnect race | User report | Verify fixed |

### Issues Found During Testing
| Issue | Severity | Description | Resolution |
|-------|----------|-------------|------------|

---

## Documentation Updates

Based on testing, update:
- [ ] Installation guide with Pi-specific notes
- [ ] Troubleshooting guide with real issues
- [ ] Configuration guide with optimal settings
- [ ] Hardware requirements with tested models

---

## Quality Gate

- [ ] All core camera operations work
- [ ] 24-hour stability test passes
- [ ] Memory stays under 800MB
- [ ] No CRITICAL issues
- [ ] Documentation updated

---

## Success Criteria

1. All operations work reliably on Pi 3B+
2. Memory usage stays under 800MB
3. No crashes during extended operation
4. Temperature readings accurate (if sensor available)
5. Documentation reflects real-world usage

---

## Notes

- Test on Pi 3B+ for minimum spec validation
- Pi 4 may have fewer constraints
- USB storage recommended for media
- Keep reference thermometer nearby for calibration
- Document any hardware-specific workarounds

---

**Estimated Effort**: 3-5 days (including wait time for long tests)
**Dependencies**: Feature phases complete
**Parallel**: Partially; some tests can run overnight

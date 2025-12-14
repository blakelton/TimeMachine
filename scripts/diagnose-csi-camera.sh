#!/bin/bash
# CSI Camera Diagnostic Script for TimeMachine
# Run this on the Raspberry Pi to diagnose CSI camera preview issues

echo "=========================================="
echo "TimeMachine CSI Camera Diagnostics"
echo "=========================================="
echo ""

# 1. Check if CSI camera is detected
echo "1. Checking CSI camera detection..."
echo "-----------------------------------"
if command -v libcamera-hello &> /dev/null; then
    echo "Running: libcamera-hello --list-cameras"
    libcamera-hello --list-cameras 2>&1
else
    echo "ERROR: libcamera-hello not found. Install with: sudo apt install libcamera-apps"
fi
echo ""

# 2. Check camera enable status
echo "2. Checking camera configuration..."
echo "-----------------------------------"
if command -v vcgencmd &> /dev/null; then
    echo "Running: vcgencmd get_camera"
    vcgencmd get_camera
else
    echo "vcgencmd not available"
fi

echo ""
echo "Checking /boot/config.txt for camera settings..."
grep -E "^(camera|dtoverlay.*camera|start_x|gpu_mem)" /boot/config.txt 2>/dev/null || \
grep -E "^(camera|dtoverlay.*camera|start_x|gpu_mem)" /boot/firmware/config.txt 2>/dev/null || \
echo "Could not find camera settings in config.txt"
echo ""

# 3. Check GStreamer libcamera plugin
echo "3. Checking GStreamer libcamera plugin..."
echo "-----------------------------------------"
echo "Running: gst-inspect-1.0 libcamerasrc"
if gst-inspect-1.0 libcamerasrc &> /dev/null; then
    gst-inspect-1.0 libcamerasrc | head -20
    echo "..."
    echo "libcamerasrc plugin: AVAILABLE"
else
    echo "ERROR: libcamerasrc not found!"
    echo "Install with: sudo apt install gstreamer1.0-libcamera"
fi
echo ""

# 4. Check video devices
echo "4. Checking video devices..."
echo "----------------------------"
echo "Listing /dev/video* devices:"
ls -la /dev/video* 2>/dev/null || echo "No video devices found"
echo ""

echo "Running: v4l2-ctl --list-devices"
v4l2-ctl --list-devices 2>&1
echo ""

# 5. Test CSI camera capture
echo "5. Testing CSI camera capabilities..."
echo "-------------------------------------"
echo "Running: libcamera-hello -t 1000 (1 second test)"
timeout 5 libcamera-hello -t 1000 2>&1 || echo "libcamera-hello test failed or timed out"
echo ""

# 6. Test GStreamer pipeline
echo "6. Testing GStreamer CSI pipeline..."
echo "------------------------------------"
echo "Running: gst-launch-1.0 libcamerasrc ! video/x-raw,width=640,height=480 ! fakesink (3 second test)"
timeout 5 gst-launch-1.0 libcamerasrc ! "video/x-raw,width=640,height=480" ! fakesink 2>&1 || echo "GStreamer pipeline test failed"
echo ""

# 7. Check supported formats
echo "7. Checking supported CSI camera formats..."
echo "-------------------------------------------"
# Find CSI camera device (usually video0 on Pi with CSI only)
CSI_DEV=""
for dev in /dev/video0 /dev/video1; do
    if [ -e "$dev" ]; then
        DRIVER=$(v4l2-ctl -d "$dev" --info 2>/dev/null | grep "Driver name" | awk '{print $4}')
        if [ "$DRIVER" = "unicam" ] || [ "$DRIVER" = "bcm2835-v4l2" ]; then
            CSI_DEV="$dev"
            break
        fi
    fi
done

if [ -n "$CSI_DEV" ]; then
    echo "Found CSI camera at: $CSI_DEV"
    echo "Supported formats:"
    v4l2-ctl -d "$CSI_DEV" --list-formats-ext 2>&1 | head -50
else
    echo "Could not identify CSI camera device"
    echo "Note: libcamerasrc doesn't use /dev/video* directly"
fi
echo ""

# 8. Check TimeMachine service status
echo "8. Checking TimeMachine service..."
echo "----------------------------------"
if systemctl is-active --quiet timemachine; then
    echo "TimeMachine service: RUNNING"
    echo ""
    echo "Recent logs related to CSI/preview:"
    journalctl -u timemachine --no-pager -n 50 2>/dev/null | grep -iE "(csi|preview|libcamera|pipeline)" | tail -20
else
    echo "TimeMachine service: NOT RUNNING"
fi
echo ""

# 9. Check permissions
echo "9. Checking permissions..."
echo "--------------------------"
echo "timemachine user groups:"
groups timemachine 2>/dev/null || echo "timemachine user not found"
echo ""
echo "Video device permissions:"
ls -la /dev/video* 2>/dev/null
echo ""

# 10. Summary
echo "=========================================="
echo "DIAGNOSTIC SUMMARY"
echo "=========================================="
echo ""
echo "Common CSI camera issues:"
echo "1. Camera not enabled: Edit /boot/config.txt, add 'start_x=1' and 'gpu_mem=128'"
echo "2. Wrong dtoverlay: For Camera Module v3, use 'dtoverlay=imx708'"
echo "3. Missing packages: sudo apt install libcamera-apps gstreamer1.0-libcamera"
echo "4. Permission issues: sudo usermod -aG video timemachine"
echo "5. GStreamer caps mismatch: Check supported resolutions above"
echo ""
echo "If libcamera-hello works but GStreamer doesn't, the issue is likely"
echo "in the GStreamer pipeline configuration or caps negotiation."
echo ""

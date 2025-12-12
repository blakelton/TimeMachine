#!/bin/bash
# Diagnostic script to identify actual capture devices vs metadata/codec devices
# Run this on the Raspberry Pi to understand /dev/video* device mapping

echo "=========================================="
echo "Camera Device Diagnostic Script"
echo "=========================================="
echo ""

echo "1. Listing all /dev/video* devices:"
ls -la /dev/video* 2>/dev/null || echo "   No video devices found"
echo ""

echo "2. Checking each device with v4l2-ctl:"
echo ""

for device in /dev/video*; do
    if [ -e "$device" ]; then
        echo "----------------------------------------"
        echo "Device: $device"
        echo "----------------------------------------"

        # Get device info
        v4l2-ctl --device="$device" --info 2>&1 | grep -E "(Driver name|Card type|Bus info|Capabilities)"

        # Check if it's a VIDEO_CAPTURE device
        echo ""
        echo "Capabilities check:"
        caps=$(v4l2-ctl --device="$device" --info 2>&1 | grep -oP '0x[0-9a-fA-F]+' | head -1)
        if [ -n "$caps" ]; then
            # VIDEO_CAPTURE = 0x00000001
            # VIDEO_CAPTURE_MPLANE = 0x00001000
            # META_CAPTURE = 0x00800000
            cap_num=$((caps))
            if [ $((cap_num & 0x00000001)) -ne 0 ]; then
                echo "   ✓ VIDEO_CAPTURE (single-plane) supported"
            fi
            if [ $((cap_num & 0x00001000)) -ne 0 ]; then
                echo "   ✓ VIDEO_CAPTURE_MPLANE (multi-plane) supported"
            fi
            if [ $((cap_num & 0x00800000)) -ne 0 ]; then
                echo "   ⚠ META_CAPTURE only - NOT a video capture device"
            fi
        fi

        # List formats if it's a capture device
        echo ""
        echo "Supported formats:"
        v4l2-ctl --device="$device" --list-formats 2>&1 | head -20

        echo ""
    fi
done

echo "=========================================="
echo "3. Summary of UVC (USB) video capture devices:"
echo "=========================================="
echo ""

for device in /dev/video*; do
    if [ -e "$device" ]; then
        driver=$(v4l2-ctl --device="$device" --info 2>&1 | grep "Driver name" | awk -F: '{print $2}' | tr -d ' ')
        caps=$(v4l2-ctl --device="$device" --info 2>&1 | grep -oP '0x[0-9a-fA-F]+' | head -1)
        card=$(v4l2-ctl --device="$device" --info 2>&1 | grep "Card type" | cut -d: -f2- | sed 's/^ *//')

        if [ "$driver" = "uvcvideo" ]; then
            cap_num=$((caps))
            if [ $((cap_num & 0x00000001)) -ne 0 ] || [ $((cap_num & 0x00001000)) -ne 0 ]; then
                echo "✓ $device - $card (VIDEO CAPTURE)"
            else
                echo "✗ $device - $card (METADATA ONLY - skip this)"
            fi
        fi
    fi
done

echo ""
echo "=========================================="
echo "4. Database camera records:"
echo "=========================================="
sqlite3 /var/lib/timemachine/timemachine.db "SELECT id, name, device_path, camera_type FROM cameras;" 2>/dev/null || echo "   Could not read database"
echo ""

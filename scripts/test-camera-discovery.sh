#!/bin/bash
#
# Test camera discovery on Raspberry Pi
# Run this to check if cameras can be detected
#

echo "╔══════════════════════════════════════════════════════════╗"
echo "║       TimeMachine Camera Discovery Test                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check for CSI cameras using libcamera
echo "🔍 Checking for CSI cameras (libcamera)..."
if command -v libcamera-hello &> /dev/null; then
    echo "✓ libcamera-hello found"
    echo "Running: libcamera-hello --list-cameras"
    timeout 5s libcamera-hello --list-cameras 2>&1 | head -20
    echo ""
else
    echo "✗ libcamera-hello not found"
    echo "  Install with: sudo apt-get install libcamera-apps"
    echo ""
fi

# Check for USB cameras using v4l2
echo "🔍 Checking for USB cameras (V4L2)..."
if command -v v4l2-ctl &> /dev/null; then
    echo "✓ v4l2-ctl found"

    # List all video devices
    VIDEO_DEVICES=$(ls /dev/video* 2>/dev/null)

    if [ -z "$VIDEO_DEVICES" ]; then
        echo "✗ No /dev/video* devices found"
    else
        echo "✓ Found video devices:"
        for device in $VIDEO_DEVICES; do
            echo ""
            echo "  Device: $device"
            # Get device info
            v4l2-ctl --device=$device --info 2>&1 | grep -E "Card type|Driver name" | sed 's/^/    /'
        done
    fi
    echo ""
else
    echo "✗ v4l2-ctl not found"
    echo "  Install with: sudo apt-get install v4l-utils"
    echo ""
fi

# Check permissions
echo "🔐 Checking user permissions..."
CURRENT_USER=$(whoami)
echo "  Current user: $CURRENT_USER"

if groups $CURRENT_USER | grep -q video; then
    echo "  ✓ User is in 'video' group"
else
    echo "  ✗ User is NOT in 'video' group"
    echo "    Add with: sudo usermod -aG video $CURRENT_USER"
fi
echo ""

# Test backend endpoint if running
echo "🌐 Testing backend discovery endpoint..."
if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "✓ Backend is running"
    echo "Testing POST /api/v1/cameras/discover"

    RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/cameras/discover")

    if [ $? -eq 0 ]; then
        echo "✓ Discovery endpoint responded"
        echo "Response:"
        echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    else
        echo "✗ Discovery endpoint failed"
    fi
else
    echo "✗ Backend not running on localhost:8000"
    echo "  Start with: sudo systemctl start timemachine"
fi
echo ""

echo "╔══════════════════════════════════════════════════════════╗"
echo "║                   Test Complete                          ║"
echo "╚══════════════════════════════════════════════════════════╝"

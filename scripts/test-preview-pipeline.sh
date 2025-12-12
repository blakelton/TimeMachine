#!/bin/bash
# Test GStreamer preview pipeline manually
# Run this on the Raspberry Pi to verify the pipeline works

echo "=========================================="
echo "GStreamer Preview Pipeline Test"
echo "=========================================="
echo ""

# Get the first USB capture device
DEVICE=""
for dev in /dev/video1 /dev/video3 /dev/video0; do
    if [ -e "$dev" ]; then
        # Check if it has formats
        formats=$(v4l2-ctl --device="$dev" --list-formats 2>&1 | grep -E "\[[0-9]+\]:")
        if [ -n "$formats" ]; then
            DEVICE="$dev"
            break
        fi
    fi
done

if [ -z "$DEVICE" ]; then
    echo "ERROR: No USB capture device found with video formats"
    exit 1
fi

echo "Using device: $DEVICE"
echo ""

echo "1. Checking device info:"
v4l2-ctl --device="$DEVICE" --info
echo ""

echo "2. Checking supported formats:"
v4l2-ctl --device="$DEVICE" --list-formats
echo ""

echo "3. Checking supported resolutions for YUYV:"
v4l2-ctl --device="$DEVICE" --list-formats-ext | grep -A20 "YUYV"
echo ""

echo "4. Testing GStreamer elements availability:"
for element in v4l2src videoconvert jpegenc multipartmux tcpserversink; do
    if gst-inspect-1.0 "$element" > /dev/null 2>&1; then
        echo "   ✓ $element available"
    else
        echo "   ✗ $element NOT FOUND"
    fi
done
echo ""

echo "5. Testing basic camera capture (will timeout after 3 seconds):"
timeout 3 gst-launch-1.0 -v \
    v4l2src device=$DEVICE num-buffers=10 ! \
    video/x-raw,format=YUY2,width=640,height=480 ! \
    videoconvert ! \
    fakesink
RESULT=$?
if [ $RESULT -eq 124 ]; then
    echo "   ✓ Basic pipeline working (timed out as expected)"
elif [ $RESULT -eq 0 ]; then
    echo "   ✓ Basic pipeline completed successfully"
else
    echo "   ✗ Pipeline failed with code $RESULT"
fi
echo ""

echo "6. Testing MJPEG preview pipeline (will run for 5 seconds):"
echo "   Starting pipeline on port 8081..."
timeout 5 gst-launch-1.0 -v \
    v4l2src device=$DEVICE ! \
    video/x-raw,format=YUY2,width=640,height=480,framerate=15/1 ! \
    videoconvert ! \
    jpegenc quality=50 ! \
    multipartmux boundary=--frame ! \
    tcpserversink host=0.0.0.0 port=8081 &
PIPE_PID=$!
sleep 2

echo "   Testing TCP connection to port 8081..."
if timeout 2 bash -c 'cat < /dev/tcp/127.0.0.1/8081' > /dev/null 2>&1; then
    echo "   ✓ TCP stream is working!"
else
    echo "   ✗ TCP stream connection failed"
fi

kill $PIPE_PID 2>/dev/null
wait $PIPE_PID 2>/dev/null
echo ""

echo "7. Checking service logs for errors:"
echo "   Recent timemachine service logs:"
journalctl -u timemachine -n 20 --no-pager 2>/dev/null || echo "   Could not read service logs"
echo ""

echo "=========================================="
echo "Test complete"
echo "=========================================="

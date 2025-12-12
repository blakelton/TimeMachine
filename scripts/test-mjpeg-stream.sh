#!/bin/bash
# Test MJPEG stream format from GStreamer
# Run this on the Raspberry Pi to diagnose streaming issues

echo "==========================================="
echo "MJPEG Stream Format Test"
echo "==========================================="
echo ""

# Get the first USB capture device
DEVICE=""
for dev in /dev/video1 /dev/video3 /dev/video0; do
    if [ -e "$dev" ]; then
        formats=$(v4l2-ctl --device="$dev" --list-formats 2>&1 | grep -E "\[[0-9]+\]:")
        if [ -n "$formats" ]; then
            DEVICE="$dev"
            break
        fi
    fi
done

if [ -z "$DEVICE" ]; then
    echo "ERROR: No USB capture device found"
    exit 1
fi

echo "Using device: $DEVICE"
echo ""

PORT=8082

echo "1. Starting GStreamer pipeline on port $PORT..."
gst-launch-1.0 -v \
    v4l2src device=$DEVICE ! \
    video/x-raw,format=YUY2,width=640,height=480 ! \
    videoconvert ! \
    jpegenc quality=50 ! \
    multipartmux boundary=--frame ! \
    tcpserversink host=0.0.0.0 port=$PORT &
PIPE_PID=$!
sleep 2

echo ""
echo "2. Checking if pipeline is running (PID: $PIPE_PID)..."
if kill -0 $PIPE_PID 2>/dev/null; then
    echo "   Pipeline is running"
else
    echo "   ERROR: Pipeline failed to start"
    exit 1
fi

echo ""
echo "3. Capturing first 2KB of stream data to analyze format..."
# Capture raw bytes and show hex dump
timeout 2 bash -c "cat < /dev/tcp/127.0.0.1/$PORT" 2>/dev/null | head -c 2048 | xxd | head -40

echo ""
echo "4. Looking for boundary marker in stream..."
timeout 2 bash -c "cat < /dev/tcp/127.0.0.1/$PORT" 2>/dev/null | head -c 4096 | strings | grep -E "frame|Content|boundary" | head -10

echo ""
echo "Stopping pipeline..."
kill $PIPE_PID 2>/dev/null
wait $PIPE_PID 2>/dev/null

echo ""
echo "==========================================="
echo "Analysis Notes:"
echo "==========================================="
echo "For MJPEG to work in browsers, each frame should have:"
echo "  --frame"
echo "  Content-Type: image/jpeg"
echo "  Content-Length: <size>"
echo "  <blank line>"
echo "  <JPEG data>"
echo ""
echo "GStreamer's multipartmux may not include Content-Type headers."
echo "If missing, we need to add them in the Python streaming code."
echo "==========================================="

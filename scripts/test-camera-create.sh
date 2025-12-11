#!/bin/bash
#
# Test camera creation via API
# This simulates what the frontend does when saving a camera
#

echo "╔══════════════════════════════════════════════════════════╗"
echo "║           Test Camera Create Endpoint                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Test data - using discovered camera path
CAMERA_DATA='{
  "name": "Test USB Camera",
  "device_path": "/dev/video4",
  "camera_type": "usb",
  "enabled": true
}'

echo "Sending POST request to /api/v1/cameras..."
echo "Request body: $CAMERA_DATA"
echo ""

# Make the request
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST \
  -H "Content-Type: application/json" \
  -d "$CAMERA_DATA" \
  "http://localhost:8000/api/v1/cameras")

# Extract HTTP status code (last line) and body (everything else)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "HTTP Status: $HTTP_CODE"
echo "Response:"
echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║           Check Backend Logs                             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Run this to see backend logs:"
echo "  sudo journalctl -u timemachine -n 50 --no-pager"

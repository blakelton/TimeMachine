#!/bin/bash
# Fix GPU permission issue for TimeMachine timelapse capture
# Resolves: MESA: error: Opening /dev/dri/renderD128 failed: Permission denied

set -e

echo "=== TimeMachine GPU Permission Fix ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Step 1: Add timemachine user to render group
echo "Step 1: Adding timemachine user to render group..."
if id -nG timemachine | grep -qw render; then
    echo "  → timemachine already in render group"
else
    usermod -aG render timemachine
    echo "  → Added timemachine to render group"
fi

# Step 2: Update systemd service file
SERVICE_FILE="/etc/systemd/system/timemachine.service"
echo ""
echo "Step 2: Updating systemd service file..."

if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: Service file not found at $SERVICE_FILE"
    exit 1
fi

# Check current SupplementaryGroups setting
if grep -q "SupplementaryGroups=video render" "$SERVICE_FILE"; then
    echo "  → Service file already has render group"
elif grep -q "SupplementaryGroups=video" "$SERVICE_FILE"; then
    sed -i 's/SupplementaryGroups=video/SupplementaryGroups=video render/' "$SERVICE_FILE"
    echo "  → Added render to SupplementaryGroups"
elif grep -q "SupplementaryGroups=" "$SERVICE_FILE"; then
    # Append render to existing groups
    sed -i 's/SupplementaryGroups=\(.*\)/SupplementaryGroups=\1 render/' "$SERVICE_FILE"
    echo "  → Appended render to existing SupplementaryGroups"
else
    # No SupplementaryGroups line, add one after Group=
    sed -i '/^Group=/a SupplementaryGroups=video render' "$SERVICE_FILE"
    echo "  → Added SupplementaryGroups=video render"
fi

# Step 3: Reload systemd and restart service
echo ""
echo "Step 3: Reloading systemd and restarting service..."
systemctl daemon-reload
echo "  → Systemd daemon reloaded"

systemctl restart timemachine
echo "  → TimeMachine service restarted"

# Step 4: Verify the fix
echo ""
echo "Step 4: Verifying fix..."
echo ""

echo "User groups for timemachine:"
id timemachine

echo ""
echo "Device permissions:"
ls -la /dev/dri/renderD128

echo ""
echo "Service status:"
systemctl status timemachine --no-pager | head -10

echo ""
echo "=== Fix Complete ==="
echo ""
echo "The timemachine user now has access to /dev/dri/renderD128."
echo "Future timelapse captures should no longer have GPU permission errors."

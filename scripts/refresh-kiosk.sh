#!/bin/bash
# Refresh the TimeMachine kiosk browser
# This script kills and restarts Chromium to force a fresh page load
# Useful after deploying frontend updates

set -e

KIOSK_USER="blake"
KIOSK_URL="http://localhost"

echo "Stopping Chromium..."
pkill -u "$KIOSK_USER" chromium 2>/dev/null || true
sleep 2

echo "Starting Chromium kiosk..."
sudo -u "$KIOSK_USER" \
    XDG_RUNTIME_DIR="/run/user/$(id -u $KIOSK_USER)" \
    WAYLAND_DISPLAY=wayland-0 \
    DISPLAY=:0 \
    /usr/bin/chromium \
        --kiosk \
        --noerrdialogs \
        --disable-infobars \
        --disable-session-crashed-bubble \
        --disable-restore-session-state \
        --start-fullscreen \
        --force-dark-mode \
        --enable-features=WebContentsForceDark,OverlayScrollbar \
        --password-store=basic \
        --hide-scrollbars \
        --window-size=800,480 \
        --window-position=0,0 \
        "$KIOSK_URL" &

sleep 3

if pgrep -u "$KIOSK_USER" chromium > /dev/null; then
    echo "Chromium kiosk restarted successfully"
else
    echo "ERROR: Failed to start Chromium"
    exit 1
fi

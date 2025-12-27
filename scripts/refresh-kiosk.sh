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

# Clear browser cache to ensure fresh loads - prevents stale React state
rm -rf /home/"$KIOSK_USER"/.cache/chromium/Default/Cache/* 2>/dev/null || true
rm -rf /home/"$KIOSK_USER"/.cache/chromium/Default/Code\ Cache/* 2>/dev/null || true

echo "Starting Chromium kiosk..."
sudo -u "$KIOSK_USER" \
    XDG_RUNTIME_DIR="/run/user/$(id -u $KIOSK_USER)" \
    WAYLAND_DISPLAY=wayland-0 \
    DISPLAY=:0 \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u $KIOSK_USER)/bus" \
    /usr/bin/chromium \
        --kiosk \
        --noerrdialogs \
        --disable-infobars \
        --disable-session-crashed-bubble \
        --disable-restore-session-state \
        --start-fullscreen \
        --enable-features=OverlayScrollbar \
        --password-store=basic \
        --hide-scrollbars \
        --disable-background-networking \
        --disable-sync \
        --disable-translate \
        --disable-extensions \
        --disable-default-apps \
        --disable-component-update \
        --window-size=800,480 \
        --window-position=0,0 \
        "$KIOSK_URL" 2>/dev/null &

sleep 3

if pgrep -u "$KIOSK_USER" chromium > /dev/null; then
    echo "Chromium kiosk restarted successfully"
else
    echo "ERROR: Failed to start Chromium"
    exit 1
fi

#!/bin/bash
#
# Deploy backend code to the production location
# This script handles rsync and permissions correctly
#
# Usage: ./scripts/deploy-backend.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SOURCE_DIR="$PROJECT_ROOT/backend/app"
TARGET_DIR="/opt/timemachine/backend/app"

echo "Deploying backend from $SOURCE_DIR to $TARGET_DIR..."

# Stop service first
echo "Stopping timemachine service..."
sudo systemctl stop timemachine || true

# Deploy with rsync
echo "Syncing files..."
sudo rsync -av --delete "$SOURCE_DIR/" "$TARGET_DIR/"

# Fix permissions - timemachine user needs to read the files
echo "Fixing permissions..."
sudo chown -R timemachine:timemachine "$TARGET_DIR"
sudo chmod -R u+r,g+r "$TARGET_DIR"

# Clear any pycache that might have been copied
echo "Clearing pycache..."
sudo find "$TARGET_DIR" -name "*.pyc" -delete 2>/dev/null || true
sudo find "$TARGET_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Start service
echo "Starting timemachine service..."
sudo systemctl start timemachine

# Wait for service to be ready
echo "Waiting for service to start..."
for i in {1..20}; do
    if curl -s http://127.0.0.1:8000/api/v1/health > /dev/null 2>&1; then
        echo "Service is ready!"
        exit 0
    fi
    sleep 0.5
done

echo "Warning: Service may not be ready, checking status..."
sudo systemctl status timemachine --no-pager || true

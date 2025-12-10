#!/bin/bash
#
# Test camera discovery as the timemachine service user
# This simulates the exact environment the backend service runs in
#

echo "╔══════════════════════════════════════════════════════════╗"
echo "║     Test Discovery as timemachine Service User          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Run Python discovery script as timemachine user
echo "Running camera discovery as timemachine user..."
echo ""

sudo -u timemachine bash << 'EOFSUDO'
cd /opt/timemachine/backend

# Activate virtual environment
source /opt/timemachine/venv/bin/activate

# Run Python test script
python3 << 'EOFPYTHON'
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, '/opt/timemachine/backend')

from app.services.camera.discovery import CameraDiscovery

async def test():
    print("=" * 60)
    print("Testing USB Camera Discovery")
    print("=" * 60)
    try:
        usb_cameras = await CameraDiscovery.discover_usb_cameras()
        print(f"\nFound {len(usb_cameras)} USB cameras:")
        for cam in usb_cameras:
            print(f"  - {cam.name}")
            print(f"    Device: {cam.device_path}")
            print(f"    Type: {cam.camera_type}")
            print(f"    Capabilities: {cam.capabilities}")
    except Exception as e:
        print(f"\nERROR during USB discovery: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Testing CSI Camera Discovery")
    print("=" * 60)
    try:
        csi_cameras = await CameraDiscovery.discover_csi_cameras()
        print(f"\nFound {len(csi_cameras)} CSI cameras:")
        for cam in csi_cameras:
            print(f"  - {cam.name}")
            print(f"    Device: {cam.device_path}")
            print(f"    Type: {cam.camera_type}")
            print(f"    Capabilities: {cam.capabilities}")
    except Exception as e:
        print(f"\nERROR during CSI discovery: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
EOFPYTHON

EOFSUDO

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                   Test Complete                          ║"
echo "╚══════════════════════════════════════════════════════════╝"

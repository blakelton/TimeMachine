#!/bin/bash
#
# Diagnostic script for camera discovery issues
# Run this script on the Pi as the timemachine user to diagnose why discovery returns empty
#

echo "╔══════════════════════════════════════════════════════════╗"
echo "║     TimeMachine Camera Discovery Diagnostic              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check current user
CURRENT_USER=$(whoami)
echo "✓ Current user: $CURRENT_USER"
echo ""

# Check if v4l2-ctl is in PATH
echo "🔍 Checking v4l2-ctl availability..."
if command -v v4l2-ctl &> /dev/null; then
    echo "✓ v4l2-ctl found at: $(which v4l2-ctl)"
else
    echo "✗ v4l2-ctl NOT found in PATH"
    echo "  PATH: $PATH"
fi
echo ""

# Check if libcamera-hello is in PATH
echo "🔍 Checking libcamera-hello availability..."
if command -v libcamera-hello &> /dev/null; then
    echo "✓ libcamera-hello found at: $(which libcamera-hello)"
else
    echo "✗ libcamera-hello NOT found in PATH"
    echo "  PATH: $PATH"
fi
echo ""

# Check group membership
echo "🔐 Checking group membership..."
echo "  Groups: $(groups)"
if groups | grep -q video; then
    echo "  ✓ User is in 'video' group"
else
    echo "  ✗ User is NOT in 'video' group"
fi
echo ""

# Check video device permissions
echo "📹 Checking video device permissions..."
for device in /dev/video*; do
    if [ -e "$device" ]; then
        echo "  Device: $device"
        ls -l "$device" | sed 's/^/    /'
    fi
done
echo ""

# Test v4l2-ctl on each video device (0-9 only)
echo "🧪 Testing v4l2-ctl on video devices..."
for i in {0..9}; do
    device="/dev/video$i"
    if [ -e "$device" ]; then
        echo ""
        echo "  Testing: $device"
        echo "  ─────────────────────────────────────────────────────────"

        # Test --info
        if timeout 3s v4l2-ctl --device="$device" --info 2>&1 > /tmp/v4l2_test_$i.txt; then
            echo "    ✓ v4l2-ctl --info succeeded"

            # Extract driver and card info
            driver=$(grep "Driver name" /tmp/v4l2_test_$i.txt | sed 's/.*: //')
            card=$(grep "Card type" /tmp/v4l2_test_$i.txt | sed 's/.*: //')

            echo "    Driver: $driver"
            echo "    Card: $card"

            # Categorize camera type
            if [ "$driver" = "unicam" ]; then
                echo "    Type: CSI Camera (unicam driver)"
            elif [ "$driver" = "uvcvideo" ]; then
                echo "    Type: USB Camera (uvcvideo driver)"
            elif [[ "$driver" =~ ^bcm2835-(codec|isp)$ ]]; then
                echo "    Type: Codec/ISP (not a camera, should be skipped)"
            else
                echo "    Type: Unknown driver ($driver)"
            fi
        else
            exit_code=$?
            echo "    ✗ v4l2-ctl --info failed (exit code: $exit_code)"
            cat /tmp/v4l2_test_$i.txt 2>&1 | sed 's/^/      /'
        fi

        rm -f /tmp/v4l2_test_$i.txt
    fi
done
echo ""

# Test Python subprocess execution (simulate what backend does)
echo "🐍 Testing Python subprocess execution (simulating backend)..."
cat > /tmp/test_discovery.py << 'EOF'
import asyncio
import re
from pathlib import Path

async def test_discovery():
    """Test camera discovery logic"""
    print("Testing USB camera discovery...")

    video_devices = list(Path("/dev").glob("video*"))
    print(f"Found {len(video_devices)} video devices: {[str(d) for d in video_devices]}")

    cameras_found = 0

    for device_path in video_devices:
        device_str = str(device_path)
        device_num = int(re.search(r"\d+", device_str).group())

        # Skip devices >= 10
        if device_num >= 10:
            print(f"  Skipping {device_str} (device number >= 10)")
            continue

        print(f"\n  Testing {device_str}...")

        try:
            proc = await asyncio.create_subprocess_exec(
                "v4l2-ctl",
                "--device",
                device_str,
                "--info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=3.0)
            output = stdout.decode() if stdout else ""
            error_output = stderr.decode() if stderr else ""

            if proc.returncode != 0:
                print(f"    ✗ v4l2-ctl failed with exit code {proc.returncode}")
                print(f"    stderr: {error_output}")
                continue

            if not output:
                print(f"    ✗ No output from v4l2-ctl")
                continue

            # Extract driver name
            driver_match = re.search(r"Driver name\s*:\s*(.+)", output, re.IGNORECASE)
            driver_name = driver_match.group(1).strip() if driver_match else ""

            print(f"    Driver: {driver_name}")

            # Skip non-USB cameras
            if driver_name in ["unicam", "bcm2835-codec", "bcm2835-isp"]:
                print(f"    Skipping (non-USB driver)")
                continue

            # Only process uvcvideo
            if driver_name != "uvcvideo":
                print(f"    Skipping (not uvcvideo)")
                continue

            # Extract camera name
            card_match = re.search(r"Card type\s*:\s*(.+)", output, re.IGNORECASE)
            card_name = card_match.group(1).strip() if card_match else "Unknown USB Camera"

            print(f"    ✓ USB Camera found: {card_name}")
            cameras_found += 1

        except asyncio.TimeoutError:
            print(f"    ✗ Timeout waiting for v4l2-ctl")
        except FileNotFoundError:
            print(f"    ✗ v4l2-ctl command not found")
            break
        except Exception as e:
            print(f"    ✗ Error: {e}")

    print(f"\nTotal USB cameras found: {cameras_found}")

    # Test CSI discovery
    print("\n\nTesting CSI camera discovery...")

    try:
        proc = await asyncio.create_subprocess_exec(
            "libcamera-hello",
            "--list-cameras",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        output = stdout.decode() if stdout else stderr.decode()

        print(f"libcamera-hello output:\n{output}")

        camera_pattern = re.compile(r"(\d+)\s*:\s*(\w+)")
        csi_found = 0

        for match in camera_pattern.finditer(output):
            camera_id = match.group(1)
            sensor_name = match.group(2)
            print(f"  ✓ CSI Camera found: {sensor_name} (ID: {camera_id})")
            csi_found += 1

        print(f"\nTotal CSI cameras found: {csi_found}")

    except FileNotFoundError:
        print("✗ libcamera-hello not found, trying v4l2 fallback...")

        # Test v4l2 fallback for CSI
        csi_found = 0
        for device_path in video_devices:
            device_str = str(device_path)
            device_num = int(re.search(r"\d+", device_str).group())

            if device_num >= 10:
                continue

            try:
                proc = await asyncio.create_subprocess_exec(
                    "v4l2-ctl",
                    "--device",
                    device_str,
                    "--info",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
                output = stdout.decode() if stdout else ""

                driver_match = re.search(r"Driver name\s*:\s*(.+)", output, re.IGNORECASE)
                driver_name = driver_match.group(1).strip() if driver_match else ""

                if driver_name == "unicam":
                    card_match = re.search(r"Card type\s*:\s*(.+)", output, re.IGNORECASE)
                    card_name = card_match.group(1).strip() if card_match else "CSI Camera"
                    print(f"  ✓ CSI Camera found via v4l2: {card_name} ({device_str})")
                    csi_found += 1

            except Exception as e:
                pass

        print(f"\nTotal CSI cameras found (v4l2 fallback): {csi_found}")

    except asyncio.TimeoutError:
        print("✗ libcamera-hello timed out")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_discovery())
EOF

python3 /tmp/test_discovery.py
rm -f /tmp/test_discovery.py
echo ""

echo "╔══════════════════════════════════════════════════════════╗"
echo "║                   Diagnostic Complete                    ║"
echo "╚══════════════════════════════════════════════════════════╝"

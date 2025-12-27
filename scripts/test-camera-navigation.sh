#!/bin/bash
# Test camera navigation - verifies streams remain working after navigation
#
# Acceptance Criteria:
# 1. Navigate to home page - see all live feeds
# 2. Navigate to Micro 1 (/camera/1)
# 3. Navigate to Micro 2 (/camera/4)
# 4. Navigate back to home page - feeds should still work
# 5. Repeat navigation to Micro 1 and Micro 2
# 6. All video feeds should work without interruption

set -e

TIMEOUT=10
STREAM_CHECK_TIMEOUT=5
LOG_FILE="/tmp/camera-navigation-test.log"
PASS_COUNT=0
FAIL_COUNT=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

check_stream_active() {
    local camera_id=$1
    local timeout=$2

    # Check if there's a recent stream request in nginx logs (within last $timeout seconds)
    local now=$(date +%s)
    local cutoff=$((now - timeout))

    # Get the stream endpoint access time
    local last_access=$(sudo grep "cameras/${camera_id}/preview/stream" /var/log/nginx/timemachine-access.log 2>/dev/null | tail -1 | awk '{print $4}' | tr -d '[]' | cut -d: -f1-4)

    if [ -z "$last_access" ]; then
        return 1
    fi

    # Check response size (should be > 10KB for active stream)
    local response_size=$(sudo grep "cameras/${camera_id}/preview/stream" /var/log/nginx/timemachine-access.log 2>/dev/null | tail -1 | awk '{print $10}')

    if [ "$response_size" -gt 10000 ] 2>/dev/null; then
        return 0
    fi

    return 1
}

wait_for_streams() {
    local timeout=$1
    local start=$(date +%s)

    log "${YELLOW}Waiting for streams to appear (max ${timeout}s)...${NC}"

    while true; do
        local now=$(date +%s)
        local elapsed=$((now - start))

        if [ $elapsed -ge $timeout ]; then
            return 1
        fi

        # Check if streams are being requested (look at last 5 seconds of logs)
        local stream_count=$(sudo tail -50 /var/log/nginx/timemachine-access.log 2>/dev/null | grep -c "preview/stream" || echo "0")

        if [ "$stream_count" -gt 0 ]; then
            return 0
        fi

        sleep 1
    done
}

verify_dashboard_streams() {
    log "\n${YELLOW}=== Verifying Dashboard Streams ===${NC}"

    # Wait a moment for streams to start
    sleep 3

    # Check nginx logs for stream requests in the last 10 seconds
    local recent_streams=$(sudo tail -100 /var/log/nginx/timemachine-access.log 2>/dev/null | grep "preview/stream" | grep -v "status" | tail -10)

    if [ -z "$recent_streams" ]; then
        log "${RED}FAIL: No stream requests found in logs${NC}"
        return 1
    fi

    # Count unique cameras with stream requests
    local camera_count=$(echo "$recent_streams" | grep -oE "cameras/[0-9]+" | sort -u | wc -l)

    if [ "$camera_count" -lt 2 ]; then
        log "${RED}FAIL: Only $camera_count camera(s) streaming (expected at least 2)${NC}"
        log "Recent streams:\n$recent_streams"
        return 1
    fi

    log "${GREEN}PASS: Found $camera_count cameras streaming${NC}"
    return 0
}

navigate_to() {
    local path=$1
    local name=$2

    log "\n${YELLOW}Navigating to $name ($path)...${NC}"

    # Use xdotool to navigate - simulate click or keyboard
    # For SPA, we need to use the browser's URL bar or click navigation
    DISPLAY=:0 xdotool key ctrl+l
    sleep 0.2
    DISPLAY=:0 xdotool type "http://localhost${path}"
    DISPLAY=:0 xdotool key Return

    sleep 2
}

navigate_home() {
    log "\n${YELLOW}Navigating to Home (/)...${NC}"
    DISPLAY=:0 xdotool key ctrl+l
    sleep 0.2
    DISPLAY=:0 xdotool type "http://localhost/"
    DISPLAY=:0 xdotool key Return
    sleep 3
}

run_test() {
    local test_name=$1
    shift
    local test_fn=$1

    log "\n${YELLOW}>>> TEST: $test_name${NC}"

    if $test_fn "$@"; then
        log "${GREEN}>>> PASSED: $test_name${NC}"
        PASS_COUNT=$((PASS_COUNT + 1))
        return 0
    else
        log "${RED}>>> FAILED: $test_name${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        return 1
    fi
}

test_initial_dashboard() {
    navigate_home
    sleep 3
    verify_dashboard_streams
}

test_navigation_cycle() {
    local cycle=$1

    log "\n${YELLOW}=== Navigation Cycle $cycle ===${NC}"

    # Navigate to Micro 1
    navigate_to "/camera/1" "Micro 1"
    sleep 2

    # Navigate to Micro 2
    navigate_to "/camera/4" "Micro 2"
    sleep 2

    # Navigate back to home
    navigate_home

    # Verify streams are working
    verify_dashboard_streams
}

# Main test execution
main() {
    log "============================================"
    log "Camera Navigation Test - $(date)"
    log "============================================"

    # Clear old log entries marker
    echo "=== TEST START $(date) ===" | sudo tee -a /var/log/nginx/timemachine-access.log > /dev/null

    # Test 1: Initial dashboard load
    run_test "Initial Dashboard Load" test_initial_dashboard || true

    # Test 2: First navigation cycle
    run_test "Navigation Cycle 1" test_navigation_cycle 1 || true

    # Test 3: Second navigation cycle
    run_test "Navigation Cycle 2" test_navigation_cycle 2 || true

    # Summary
    log "\n============================================"
    log "TEST SUMMARY"
    log "============================================"
    log "Passed: $PASS_COUNT"
    log "Failed: $FAIL_COUNT"
    log "============================================"

    if [ $FAIL_COUNT -gt 0 ]; then
        log "${RED}OVERALL: FAILED${NC}"
        exit 1
    else
        log "${GREEN}OVERALL: PASSED${NC}"
        exit 0
    fi
}

main "$@"

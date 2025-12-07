#!/bin/bash
#
# TimeMachine Camera Operations Test Script
# Tests camera operations (preview, capture, record, timelapse)
#
# Usage: ./test-camera.sh [--camera-id ID] [--report] [--host HOST] [--port PORT]
#
# WARNING: This script performs actual camera operations.
#          Ensure you have a camera connected before running.
#

set -euo pipefail

# Default configuration
HOST="${TIMEMACHINE_HOST:-localhost}"
PORT="${TIMEMACHINE_PORT:-8000}"
BASE_URL="http://${HOST}:${PORT}/api/v1"
CAMERA_ID="${TIMEMACHINE_CAMERA_ID:-1}"
GENERATE_REPORT=false
REPORT_FILE=""
VERBOSE=false
DRY_RUN=false
SKIP_TIMELAPSE=false

# Test timing
PREVIEW_DURATION=5
RECORD_DURATION=10
TIMELAPSE_INTERVAL=2
TIMELAPSE_DURATION=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0
declare -a FAILED_TESTS=()
declare -a TEST_RESULTS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --camera-id|-c)
            CAMERA_ID="$2"
            shift 2
            ;;
        --report)
            GENERATE_REPORT=true
            REPORT_FILE="${2:-}"
            if [[ -n "$REPORT_FILE" && ! "$REPORT_FILE" =~ ^-- ]]; then
                shift
            else
                REPORT_FILE="camera-test-report-$(date +%Y%m%d-%H%M%S).md"
            fi
            shift
            ;;
        --host)
            HOST="$2"
            BASE_URL="http://${HOST}:${PORT}/api/v1"
            shift 2
            ;;
        --port)
            PORT="$2"
            BASE_URL="http://${HOST}:${PORT}/api/v1"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-timelapse)
            SKIP_TIMELAPSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --camera-id, -c ID   Camera ID to test (default: 1)"
            echo "  --report [FILE]      Generate markdown report"
            echo "  --host HOST          API host (default: localhost)"
            echo "  --port PORT          API port (default: 8000)"
            echo "  --verbose, -v        Show detailed output"
            echo "  --dry-run            Show what would be tested without executing"
            echo "  --skip-timelapse     Skip timelapse tests (faster)"
            echo "  --help, -h           Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  TIMEMACHINE_HOST       API host"
            echo "  TIMEMACHINE_PORT       API port"
            echo "  TIMEMACHINE_CAMERA_ID  Default camera ID"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

log_skip() {
    echo -e "${YELLOW}[SKIP]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

log_verbose() {
    if $VERBOSE; then
        echo -e "       $1"
    fi
}

# Record test result
record_result() {
    local name="$1"
    local status="$2"
    local message="${3:-}"
    local details="${4:-}"

    TEST_RESULTS+=("$name|$status|$message|$details")
}

# API request helper
api_request() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"

    local url="${BASE_URL}${endpoint}"
    local response

    if [[ -n "$data" ]]; then
        response=$(curl -s -X "$method" -H "Content-Type: application/json" -d "$data" "$url" 2>&1)
    else
        response=$(curl -s -X "$method" "$url" 2>&1)
    fi

    echo "$response"
}

# Check if server is running
check_server() {
    log_info "Checking server at $BASE_URL..."

    if curl -s --connect-timeout 5 "${BASE_URL}/health" > /dev/null 2>&1; then
        log_pass "Server is running"
        return 0
    else
        log_fail "Server is not responding at $BASE_URL"
        echo ""
        echo "Please start the server with:"
        echo "  cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
        return 1
    fi
}

# Check if camera exists
check_camera() {
    log_info "Checking camera ID $CAMERA_ID..."

    local response
    response=$(api_request "GET" "/cameras/$CAMERA_ID")

    if echo "$response" | grep -q '"id":'; then
        log_pass "Camera $CAMERA_ID found"
        log_verbose "Camera info: $(echo "$response" | head -c 200)..."
        return 0
    else
        log_fail "Camera $CAMERA_ID not found"
        echo ""
        echo "Available cameras:"
        api_request "GET" "/cameras" | python3 -m json.tool 2>/dev/null || echo "$response"
        echo ""
        echo "Try discovering cameras first:"
        echo "  curl -X POST $BASE_URL/cameras/discover"
        return 1
    fi
}

# Test preview operations
test_preview() {
    log_step "Testing Preview Operations"
    echo ""

    if $DRY_RUN; then
        log_info "[DRY RUN] Would test preview start/stop"
        return 0
    fi

    # Start preview
    log_info "Starting preview..."
    local start_response
    start_response=$(api_request "POST" "/cameras/$CAMERA_ID/preview/start")

    if echo "$start_response" | grep -qE '"success":\s*true|"status":\s*"started"'; then
        log_pass "Preview started"
        log_verbose "Response: $start_response"
        ((TESTS_PASSED++))
        record_result "Preview Start" "PASS" "Preview started successfully" "$start_response"
    else
        log_fail "Preview start failed: $start_response"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Preview Start: $start_response")
        record_result "Preview Start" "FAIL" "Failed to start" "$start_response"
        return 1
    fi

    # Wait for preview
    log_info "Preview running for ${PREVIEW_DURATION}s..."
    sleep "$PREVIEW_DURATION"

    # Stop preview
    log_info "Stopping preview..."
    local stop_response
    stop_response=$(api_request "POST" "/cameras/$CAMERA_ID/preview/stop")

    if echo "$stop_response" | grep -qE '"success":\s*true|"status":\s*"stopped"'; then
        log_pass "Preview stopped"
        ((TESTS_PASSED++))
        record_result "Preview Stop" "PASS" "Preview stopped successfully" "$stop_response"
    else
        log_fail "Preview stop failed: $stop_response"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Preview Stop: $stop_response")
        record_result "Preview Stop" "FAIL" "Failed to stop" "$stop_response"
    fi

    echo ""
}

# Test capture operations
test_capture() {
    log_step "Testing Capture Operations"
    echo ""

    if $DRY_RUN; then
        log_info "[DRY RUN] Would test image capture"
        return 0
    fi

    log_info "Capturing image..."
    local response
    response=$(api_request "POST" "/cameras/$CAMERA_ID/capture")

    if echo "$response" | grep -qE '"success":\s*true|"path":'; then
        log_pass "Image captured"

        # Extract path if available
        local path
        path=$(echo "$response" | grep -oP '"path":\s*"\K[^"]+' || echo "")
        if [[ -n "$path" ]]; then
            log_verbose "Image saved to: $path"
        fi

        ((TESTS_PASSED++))
        record_result "Image Capture" "PASS" "Image captured successfully" "$response"
    else
        log_fail "Capture failed: $response"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Image Capture: $response")
        record_result "Image Capture" "FAIL" "Failed to capture" "$response"
    fi

    echo ""
}

# Test recording operations
test_recording() {
    log_step "Testing Recording Operations"
    echo ""

    if $DRY_RUN; then
        log_info "[DRY RUN] Would test recording start/stop"
        return 0
    fi

    # Start recording
    log_info "Starting recording..."
    local start_response
    start_response=$(api_request "POST" "/cameras/$CAMERA_ID/recording/start")

    if echo "$start_response" | grep -qE '"success":\s*true|"job_id":'; then
        log_pass "Recording started"

        # Extract job_id
        local job_id
        job_id=$(echo "$start_response" | grep -oP '"job_id":\s*\K\d+' || echo "")
        if [[ -n "$job_id" ]]; then
            log_verbose "Job ID: $job_id"
        fi

        ((TESTS_PASSED++))
        record_result "Recording Start" "PASS" "Recording started (job: $job_id)" "$start_response"
    else
        log_fail "Recording start failed: $start_response"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Recording Start: $start_response")
        record_result "Recording Start" "FAIL" "Failed to start" "$start_response"
        return 1
    fi

    # Wait for recording
    log_info "Recording for ${RECORD_DURATION}s..."
    sleep "$RECORD_DURATION"

    # Check status
    log_info "Checking recording status..."
    local status_response
    status_response=$(api_request "GET" "/cameras/$CAMERA_ID/recording/status")
    log_verbose "Status: $status_response"

    # Stop recording
    log_info "Stopping recording..."
    local stop_response
    stop_response=$(api_request "POST" "/cameras/$CAMERA_ID/recording/stop")

    if echo "$stop_response" | grep -qE '"success":\s*true|"path":'; then
        log_pass "Recording stopped"

        # Extract path
        local path
        path=$(echo "$stop_response" | grep -oP '"path":\s*"\K[^"]+' || echo "")
        if [[ -n "$path" ]]; then
            log_verbose "Video saved to: $path"
        fi

        ((TESTS_PASSED++))
        record_result "Recording Stop" "PASS" "Recording stopped with EOS" "$stop_response"
    else
        log_fail "Recording stop failed: $stop_response"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Recording Stop: $stop_response")
        record_result "Recording Stop" "FAIL" "Failed to stop" "$stop_response"
    fi

    echo ""
}

# Test timelapse operations
test_timelapse() {
    log_step "Testing Timelapse Operations"
    echo ""

    if $SKIP_TIMELAPSE; then
        log_skip "Timelapse tests skipped (--skip-timelapse)"
        ((TESTS_SKIPPED++))
        record_result "Timelapse Start" "SKIP" "Skipped by user" ""
        record_result "Timelapse Stop" "SKIP" "Skipped by user" ""
        echo ""
        return 0
    fi

    if $DRY_RUN; then
        log_info "[DRY RUN] Would test timelapse start/stop"
        return 0
    fi

    # Start timelapse
    log_info "Starting timelapse (interval: ${TIMELAPSE_INTERVAL}s, duration: ${TIMELAPSE_DURATION}s)..."
    local config="{\"config\": {\"interval_seconds\": $TIMELAPSE_INTERVAL, \"duration_seconds\": $TIMELAPSE_DURATION}}"
    local start_response
    start_response=$(api_request "POST" "/cameras/$CAMERA_ID/timelapse/start" "$config")

    if echo "$start_response" | grep -qE '"success":\s*true|"job_id":'; then
        log_pass "Timelapse started"

        local job_id
        job_id=$(echo "$start_response" | grep -oP '"job_id":\s*\K\d+' || echo "")
        if [[ -n "$job_id" ]]; then
            log_verbose "Job ID: $job_id"
        fi

        ((TESTS_PASSED++))
        record_result "Timelapse Start" "PASS" "Timelapse started (job: $job_id)" "$start_response"
    else
        log_fail "Timelapse start failed: $start_response"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Timelapse Start: $start_response")
        record_result "Timelapse Start" "FAIL" "Failed to start" "$start_response"
        return 1
    fi

    # Wait for some frames to be captured
    local wait_time=$((TIMELAPSE_DURATION + 5))
    log_info "Waiting ${wait_time}s for timelapse to complete..."

    for ((i=0; i<wait_time; i+=5)); do
        sleep 5
        local status
        status=$(api_request "GET" "/cameras/$CAMERA_ID/timelapse/status")
        local progress
        progress=$(echo "$status" | grep -oP '"frames_captured":\s*\K\d+' || echo "0")
        log_verbose "Progress: $progress frames captured"
    done

    # Stop timelapse (should assemble video)
    log_info "Stopping timelapse and assembling video..."
    local stop_response
    stop_response=$(api_request "POST" "/cameras/$CAMERA_ID/timelapse/stop")

    if echo "$stop_response" | grep -qE '"success":\s*true|"video_path":'; then
        log_pass "Timelapse stopped and assembled"

        local video_path
        video_path=$(echo "$stop_response" | grep -oP '"video_path":\s*"\K[^"]+' || echo "")
        if [[ -n "$video_path" ]]; then
            log_verbose "Video saved to: $video_path"
        fi

        ((TESTS_PASSED++))
        record_result "Timelapse Stop" "PASS" "Timelapse assembled" "$stop_response"
    else
        log_fail "Timelapse stop failed: $stop_response"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Timelapse Stop: $stop_response")
        record_result "Timelapse Stop" "FAIL" "Failed to stop/assemble" "$stop_response"
    fi

    echo ""
}

# Generate markdown report
generate_report() {
    local report_path="$1"

    cat > "$report_path" << EOF
# TimeMachine Camera Test Report

**Generated:** $(date '+%Y-%m-%d %H:%M:%S')
**Server:** ${BASE_URL}
**Camera ID:** ${CAMERA_ID}
**Host:** $(hostname)

## Summary

| Metric | Count |
|--------|-------|
| Tests Passed | $TESTS_PASSED |
| Tests Failed | $TESTS_FAILED |
| Tests Skipped | $TESTS_SKIPPED |
| **Total** | $((TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED)) |

**Status:** $(if [[ $TESTS_FAILED -eq 0 ]]; then echo "✅ ALL TESTS PASSED"; else echo "❌ SOME TESTS FAILED"; fi)

## Test Configuration

| Setting | Value |
|---------|-------|
| Preview Duration | ${PREVIEW_DURATION}s |
| Record Duration | ${RECORD_DURATION}s |
| Timelapse Interval | ${TIMELAPSE_INTERVAL}s |
| Timelapse Duration | ${TIMELAPSE_DURATION}s |

## Test Results

| Test Name | Status | Details |
|-----------|--------|---------|
EOF

    for result in "${TEST_RESULTS[@]}"; do
        IFS='|' read -r name status message details <<< "$result"
        local status_icon
        case $status in
            PASS) status_icon="✅" ;;
            FAIL) status_icon="❌" ;;
            SKIP) status_icon="⏭️" ;;
            *) status_icon="❓" ;;
        esac
        echo "| $name | $status_icon $status | $message |" >> "$report_path"
    done

    if [[ $TESTS_FAILED -gt 0 ]]; then
        cat >> "$report_path" << EOF

## Failed Tests Details

EOF
        for failed in "${FAILED_TESTS[@]}"; do
            echo "- $failed" >> "$report_path"
        done

        cat >> "$report_path" << EOF

## Troubleshooting

Based on the failed tests, check:

1. **Camera connectivity:**
   \`\`\`bash
   # CSI camera
   libcamera-hello --list-cameras

   # USB camera
   ls -la /dev/video*
   v4l2-ctl --list-devices
   \`\`\`

2. **GStreamer pipelines:**
   \`\`\`bash
   # Test CSI camera
   gst-launch-1.0 libcamerasrc ! fakesink

   # Test USB camera
   gst-launch-1.0 v4l2src device=/dev/video0 ! fakesink
   \`\`\`

3. **Check logs:**
   \`\`\`bash
   timemachine logs | grep -E "(error|fail|camera)"
   \`\`\`

4. **Check for orphan processes:**
   \`\`\`bash
   pgrep -f gst-launch
   pgrep -f libcamera
   \`\`\`
EOF
    fi

    cat >> "$report_path" << EOF

## System Information

- **OS:** $(uname -s) $(uname -r)
- **Architecture:** $(uname -m)
- **Python Version:** $(python3 --version 2>&1 || echo "N/A")
- **GStreamer:** $(gst-launch-1.0 --version 2>&1 | head -1 || echo "N/A")
- **FFmpeg:** $(ffmpeg -version 2>&1 | head -1 || echo "N/A")

---
*Report generated by TimeMachine test-camera.sh*
EOF
}

# Main test execution
main() {
    echo ""
    echo "=========================================="
    echo "  TimeMachine Camera Test Suite"
    echo "=========================================="
    echo ""

    if $DRY_RUN; then
        log_info "DRY RUN MODE - No actual operations will be performed"
        echo ""
    fi

    # Check server
    if ! check_server; then
        exit 1
    fi

    echo ""

    # Check camera
    if ! check_camera; then
        exit 1
    fi

    echo ""

    # Run tests
    test_preview
    test_capture
    test_recording
    test_timelapse

    # Summary
    echo "=========================================="
    echo "  Test Summary"
    echo "=========================================="
    echo ""
    echo -e "  ${GREEN}Passed:${NC}  $TESTS_PASSED"
    echo -e "  ${RED}Failed:${NC}  $TESTS_FAILED"
    echo -e "  ${YELLOW}Skipped:${NC} $TESTS_SKIPPED"
    echo ""

    if [[ $TESTS_FAILED -gt 0 ]]; then
        echo -e "${RED}Some tests failed!${NC}"
        echo ""
        echo "Failed tests:"
        for failed in "${FAILED_TESTS[@]}"; do
            echo "  - $failed"
        done
    else
        echo -e "${GREEN}All tests passed!${NC}"
    fi

    # Generate report if requested
    if $GENERATE_REPORT; then
        echo ""
        generate_report "$REPORT_FILE"
        log_info "Report saved to: $REPORT_FILE"
    fi

    echo ""

    # Exit with appropriate code
    if [[ $TESTS_FAILED -gt 0 ]]; then
        exit 1
    fi
    exit 0
}

main "$@"

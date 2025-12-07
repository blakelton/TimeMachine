#!/bin/bash
#
# TimeMachine Master Test Runner
# Runs all test suites and generates a comprehensive report
#
# Usage: ./run-tests.sh [OPTIONS]
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default configuration
HOST="${TIMEMACHINE_HOST:-localhost}"
PORT="${TIMEMACHINE_PORT:-8000}"
GENERATE_REPORT=true
REPORT_DIR="${PROJECT_ROOT}/test-reports"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
VERBOSE=false
RUN_API_TESTS=true
RUN_CAMERA_TESTS=false
CAMERA_ID="${TIMEMACHINE_CAMERA_ID:-1}"
SKIP_TIMELAPSE=true
START_SERVER=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Results
API_RESULT=""
CAMERA_RESULT=""
SERVER_PID=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --all|-a)
            RUN_API_TESTS=true
            RUN_CAMERA_TESTS=true
            shift
            ;;
        --api-only)
            RUN_API_TESTS=true
            RUN_CAMERA_TESTS=false
            shift
            ;;
        --camera-only)
            RUN_API_TESTS=false
            RUN_CAMERA_TESTS=true
            shift
            ;;
        --camera-id|-c)
            CAMERA_ID="$2"
            shift 2
            ;;
        --with-timelapse)
            SKIP_TIMELAPSE=false
            shift
            ;;
        --no-report)
            GENERATE_REPORT=false
            shift
            ;;
        --report-dir)
            REPORT_DIR="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --start-server)
            START_SERVER=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            cat << EOF
TimeMachine Test Runner

Usage: $0 [OPTIONS]

Test Selection:
  --all, -a           Run all tests (API + Camera)
  --api-only          Run only API tests (default)
  --camera-only       Run only camera tests
  --camera-id, -c ID  Camera ID for camera tests (default: 1)
  --with-timelapse    Include timelapse tests (slow)

Server Options:
  --host HOST         API host (default: localhost)
  --port PORT         API port (default: 8000)
  --start-server      Auto-start backend server before tests

Report Options:
  --no-report         Don't generate reports
  --report-dir DIR    Report output directory (default: test-reports/)

Other:
  --verbose, -v       Verbose output
  --help, -h          Show this help

Examples:
  $0                          # Run API tests only
  $0 --all                    # Run all tests
  $0 --camera-only -c 2       # Run camera tests on camera 2
  $0 --all --with-timelapse   # Run all tests including timelapse
  $0 --start-server --all     # Start server and run all tests
EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Logging
log_header() {
    echo ""
    echo -e "${BOLD}${CYAN}$1${NC}"
    echo "$(printf '=%.0s' {1..50})"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Cleanup function
cleanup() {
    if [[ -n "$SERVER_PID" ]]; then
        log_info "Stopping test server (PID: $SERVER_PID)..."
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Start server if requested
start_server() {
    log_info "Starting backend server..."

    cd "$PROJECT_ROOT/backend"

    # Check for virtual environment
    if [[ -d "venv" ]]; then
        source venv/bin/activate
    fi

    # Start server in background
    uvicorn app.main:app --host 0.0.0.0 --port "$PORT" &
    SERVER_PID=$!

    log_info "Server starting (PID: $SERVER_PID)..."

    # Wait for server to be ready
    local max_attempts=30
    local attempt=0

    while [[ $attempt -lt $max_attempts ]]; do
        if curl -s "http://${HOST}:${PORT}/api/v1/health" > /dev/null 2>&1; then
            log_success "Server is ready"
            return 0
        fi
        ((attempt++))
        sleep 1
    done

    log_error "Server failed to start within ${max_attempts}s"
    return 1
}

# Check if server is running
check_server() {
    if curl -s --connect-timeout 5 "http://${HOST}:${PORT}/api/v1/health" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

# Run API tests
run_api_tests() {
    log_header "Running API Tests"

    local args=("--host" "$HOST" "--port" "$PORT")

    if $GENERATE_REPORT; then
        args+=("--report" "${REPORT_DIR}/api-test-${TIMESTAMP}.md")
    fi

    if $VERBOSE; then
        args+=("--verbose")
    fi

    if "$SCRIPT_DIR/test-api.sh" "${args[@]}"; then
        API_RESULT="PASS"
        log_success "API tests passed"
    else
        API_RESULT="FAIL"
        log_error "API tests failed"
    fi
}

# Run camera tests
run_camera_tests() {
    log_header "Running Camera Tests"

    local args=("--host" "$HOST" "--port" "$PORT" "--camera-id" "$CAMERA_ID")

    if $GENERATE_REPORT; then
        args+=("--report" "${REPORT_DIR}/camera-test-${TIMESTAMP}.md")
    fi

    if $VERBOSE; then
        args+=("--verbose")
    fi

    if $SKIP_TIMELAPSE; then
        args+=("--skip-timelapse")
    fi

    if "$SCRIPT_DIR/test-camera.sh" "${args[@]}"; then
        CAMERA_RESULT="PASS"
        log_success "Camera tests passed"
    else
        CAMERA_RESULT="FAIL"
        log_error "Camera tests failed"
    fi
}

# Generate summary report
generate_summary() {
    local summary_file="${REPORT_DIR}/summary-${TIMESTAMP}.md"

    cat > "$summary_file" << EOF
# TimeMachine Test Summary

**Generated:** $(date '+%Y-%m-%d %H:%M:%S')
**Host:** $(hostname)
**Server:** http://${HOST}:${PORT}

## Test Configuration

| Setting | Value |
|---------|-------|
| API Tests | $(if $RUN_API_TESTS; then echo "Enabled"; else echo "Disabled"; fi) |
| Camera Tests | $(if $RUN_CAMERA_TESTS; then echo "Enabled"; else echo "Disabled"; fi) |
| Camera ID | $CAMERA_ID |
| Timelapse Tests | $(if $SKIP_TIMELAPSE; then echo "Skipped"; else echo "Enabled"; fi) |

## Results

| Test Suite | Status |
|------------|--------|
EOF

    if $RUN_API_TESTS; then
        local api_icon="❓"
        [[ "$API_RESULT" == "PASS" ]] && api_icon="✅"
        [[ "$API_RESULT" == "FAIL" ]] && api_icon="❌"
        echo "| API Tests | $api_icon $API_RESULT |" >> "$summary_file"
    fi

    if $RUN_CAMERA_TESTS; then
        local camera_icon="❓"
        [[ "$CAMERA_RESULT" == "PASS" ]] && camera_icon="✅"
        [[ "$CAMERA_RESULT" == "FAIL" ]] && camera_icon="❌"
        echo "| Camera Tests | $camera_icon $CAMERA_RESULT |" >> "$summary_file"
    fi

    local overall="PASS"
    if [[ "$API_RESULT" == "FAIL" || "$CAMERA_RESULT" == "FAIL" ]]; then
        overall="FAIL"
    fi

    cat >> "$summary_file" << EOF

## Overall Status

$(if [[ "$overall" == "PASS" ]]; then echo "✅ **ALL TESTS PASSED**"; else echo "❌ **SOME TESTS FAILED**"; fi)

## Individual Reports

EOF

    if $RUN_API_TESTS && [[ -f "${REPORT_DIR}/api-test-${TIMESTAMP}.md" ]]; then
        echo "- [API Test Report](api-test-${TIMESTAMP}.md)" >> "$summary_file"
    fi

    if $RUN_CAMERA_TESTS && [[ -f "${REPORT_DIR}/camera-test-${TIMESTAMP}.md" ]]; then
        echo "- [Camera Test Report](camera-test-${TIMESTAMP}.md)" >> "$summary_file"
    fi

    cat >> "$summary_file" << EOF

## System Information

\`\`\`
OS: $(uname -s) $(uname -r) ($(uname -m))
Python: $(python3 --version 2>&1 || echo "N/A")
Node: $(node --version 2>&1 || echo "N/A")
\`\`\`

## Quick Commands

\`\`\`bash
# View detailed logs
timemachine logs

# Check service status
timemachine status

# Restart service
sudo timemachine restart
\`\`\`

---
*Generated by TimeMachine run-tests.sh*
EOF

    echo "$summary_file"
}

# Main
main() {
    echo ""
    echo -e "${BOLD}=========================================${NC}"
    echo -e "${BOLD}  TimeMachine Test Runner${NC}"
    echo -e "${BOLD}=========================================${NC}"
    echo ""

    # Create report directory
    if $GENERATE_REPORT; then
        mkdir -p "$REPORT_DIR"
        log_info "Reports will be saved to: $REPORT_DIR"
    fi

    # Start server if requested
    if $START_SERVER; then
        if check_server; then
            log_warn "Server already running, skipping auto-start"
        else
            start_server || exit 1
        fi
    fi

    # Check server is running
    if ! check_server; then
        log_error "Server is not running at http://${HOST}:${PORT}"
        echo ""
        echo "Start the server with:"
        echo "  cd $PROJECT_ROOT/backend"
        echo "  uvicorn app.main:app --host 0.0.0.0 --port $PORT"
        echo ""
        echo "Or use --start-server to auto-start:"
        echo "  $0 --start-server"
        exit 1
    fi

    # Run tests
    if $RUN_API_TESTS; then
        run_api_tests || true
    fi

    if $RUN_CAMERA_TESTS; then
        run_camera_tests || true
    fi

    # Generate summary
    if $GENERATE_REPORT; then
        log_header "Generating Summary Report"
        local summary
        summary=$(generate_summary)
        log_info "Summary report: $summary"
    fi

    # Final summary
    log_header "Test Run Complete"
    echo ""

    if $RUN_API_TESTS; then
        if [[ "$API_RESULT" == "PASS" ]]; then
            echo -e "  API Tests:    ${GREEN}✓ PASSED${NC}"
        else
            echo -e "  API Tests:    ${RED}✗ FAILED${NC}"
        fi
    fi

    if $RUN_CAMERA_TESTS; then
        if [[ "$CAMERA_RESULT" == "PASS" ]]; then
            echo -e "  Camera Tests: ${GREEN}✓ PASSED${NC}"
        else
            echo -e "  Camera Tests: ${RED}✗ FAILED${NC}"
        fi
    fi

    echo ""

    if $GENERATE_REPORT; then
        echo "Reports saved to: $REPORT_DIR/"
        ls -la "$REPORT_DIR"/*-${TIMESTAMP}.md 2>/dev/null || true
    fi

    echo ""

    # Exit code
    if [[ "$API_RESULT" == "FAIL" || "$CAMERA_RESULT" == "FAIL" ]]; then
        exit 1
    fi

    exit 0
}

main "$@"

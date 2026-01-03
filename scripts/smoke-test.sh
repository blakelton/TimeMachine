#!/bin/bash
#
# TimeMachine Post-Deployment Smoke Test
# Quick verification that critical system components are operational
#
# Usage: ./smoke-test.sh [--host HOST] [--port PORT] [--timeout SECS]
#
# Exit codes:
#   0 - All smoke tests passed
#   1 - One or more smoke tests failed
#   2 - Service not running / unreachable
#

set -euo pipefail

# Default configuration
HOST="${TIMEMACHINE_HOST:-localhost}"
PORT="${TIMEMACHINE_PORT:-8000}"
BASE_URL="http://${HOST}:${PORT}/api/v1"
TIMEOUT=${SMOKE_TEST_TIMEOUT:-60}
CURL_TIMEOUT=5

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Counters
TESTS_PASSED=0
TESTS_FAILED=0
START_TIME=$(date +%s)

# Log functions
log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; ((TESTS_PASSED++)) || true; }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; ((TESTS_FAILED++)) || true; }
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Check if jq is available
JQ_AVAILABLE=true
if ! command -v jq &> /dev/null; then
    log_warn "jq not installed - using basic response validation"
    JQ_AVAILABLE=false
fi

# Core smoke test function
smoke_test() {
    local name="$1"
    local endpoint="$2"
    local expected_code="${3:-200}"
    local json_check="${4:-}"

    local url="${BASE_URL}${endpoint}"
    local response
    local http_code
    local body

    # Make request with timeout
    if response=$(curl -s -w '\n%{http_code}' \
                       --connect-timeout "$CURL_TIMEOUT" \
                       --max-time "$CURL_TIMEOUT" \
                       -X GET "$url" 2>&1); then
        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | sed '$d')

        # Check HTTP status
        if [[ "$http_code" != "$expected_code" ]]; then
            log_fail "$name - Expected HTTP $expected_code, got $http_code"
            return 1
        fi

        # Optional JSON validation
        if [[ -n "$json_check" && "$JQ_AVAILABLE" == "true" ]]; then
            if ! echo "$body" | jq -e "$json_check" > /dev/null 2>&1; then
                log_fail "$name - Response validation failed: $json_check"
                return 1
            fi
        fi

        log_pass "$name"
        return 0
    else
        log_fail "$name - Request failed (network error or timeout)"
        return 1
    fi
}

# Check elapsed time against timeout
check_timeout() {
    local elapsed=$(($(date +%s) - START_TIME))
    if [[ $elapsed -ge $TIMEOUT ]]; then
        log_warn "Smoke test timeout exceeded (${elapsed}s >= ${TIMEOUT}s)"
        return 1
    fi
    return 0
}

# Verify service is running before tests
check_service_running() {
    log_info "Checking TimeMachine service..."

    # Check systemd service status (if available)
    if command -v systemctl &> /dev/null; then
        if ! systemctl is-active --quiet timemachine 2>/dev/null; then
            log_warn "TimeMachine systemd service is not active (may be running differently)"
        fi
    fi

    # Check API is responding
    if ! curl -s --connect-timeout 3 "${BASE_URL}/health" > /dev/null 2>&1; then
        log_fail "API is not responding at ${BASE_URL}/health"
        echo ""
        echo "Service may be starting. Wait and retry, or check logs:"
        echo "  journalctl -u timemachine -n 50"
        return 1
    fi

    log_pass "Service is responding"
    return 0
}

run_smoke_tests() {
    echo ""
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD}  TimeMachine Smoke Tests${NC}"
    echo -e "${BOLD}========================================${NC}"
    echo ""
    log_info "Target: ${BASE_URL}"
    log_info "Timeout: ${TIMEOUT}s"
    echo ""

    # ==========================================
    # CRITICAL: Service Health
    # ==========================================
    echo "--- Service Health ---"

    # Test 1: Health endpoint returns OK
    smoke_test \
        "Health endpoint responds" \
        "/health" \
        200 \
        '.data.status == "ok"'

    check_timeout || return 1

    # Test 2: System stats available
    smoke_test \
        "System stats available" \
        "/health/stats" \
        200 \
        '.data.cpu_percent != null'

    check_timeout || return 1

    # ==========================================
    # CRITICAL: Camera System
    # ==========================================
    echo ""
    echo "--- Camera System ---"

    # Test 3: Camera list endpoint works
    smoke_test \
        "Camera list endpoint" \
        "/cameras/" \
        200 \
        '.cameras != null'

    check_timeout || return 1

    # Test 4: Check timelapse status for first camera (if cameras exist)
    local camera_response
    camera_response=$(curl -s --connect-timeout "$CURL_TIMEOUT" \
                          "${BASE_URL}/cameras/" 2>/dev/null || echo '{"cameras":[]}')

    if [[ "$JQ_AVAILABLE" == "true" ]] && echo "$camera_response" | jq -e '.cameras | length > 0' > /dev/null 2>&1; then
        local first_camera_id
        first_camera_id=$(echo "$camera_response" | jq -r '.cameras[0].id')

        smoke_test \
            "Timelapse status (camera ${first_camera_id})" \
            "/cameras/${first_camera_id}/timelapse/status" \
            200 \
            '.camera_id != null'
    else
        log_warn "No cameras configured - skipping timelapse status test"
    fi

    check_timeout || return 1

    # ==========================================
    # CRITICAL: Observations System
    # ==========================================
    echo ""
    echo "--- Observations System ---"

    # Test 5: Completed observations endpoint works
    smoke_test \
        "Completed observations endpoint" \
        "/observations/completed" \
        200 \
        '.observations != null'

    check_timeout || return 1

    # Test 6: Active observations endpoint
    smoke_test \
        "Active observations endpoint" \
        "/observations/active" \
        200 \
        '.observations != null'

    check_timeout || return 1

    # ==========================================
    # CRITICAL: Jobs System
    # ==========================================
    echo ""
    echo "--- Jobs System ---"

    # Test 7: Jobs list endpoint
    smoke_test \
        "Jobs list endpoint" \
        "/jobs" \
        200 \
        '.jobs != null'

    check_timeout || return 1

    # Test 8: Running jobs endpoint
    smoke_test \
        "Running jobs endpoint" \
        "/jobs/running" \
        200 \
        '.jobs != null'

    check_timeout || return 1

    # ==========================================
    # Configuration Endpoints
    # ==========================================
    echo ""
    echo "--- Configuration ---"

    # Test 9: Output config
    smoke_test \
        "Output config endpoint" \
        "/output-config" \
        200

    check_timeout || return 1

    # Test 10: Environment devices
    smoke_test \
        "Environment devices endpoint" \
        "/environment/devices" \
        200 \
        '.devices != null'

    return 0
}

print_summary() {
    local elapsed=$(($(date +%s) - START_TIME))
    local total=$((TESTS_PASSED + TESTS_FAILED))

    echo ""
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD}  Smoke Test Summary${NC}"
    echo -e "${BOLD}========================================${NC}"
    echo ""
    echo -e "  ${GREEN}Passed:${NC}  $TESTS_PASSED"
    echo -e "  ${RED}Failed:${NC}  $TESTS_FAILED"
    echo -e "  Total:   $total"
    echo -e "  Time:    ${elapsed}s"
    echo ""

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}${BOLD}ALL SMOKE TESTS PASSED${NC}"
        return 0
    else
        echo -e "${RED}${BOLD}SMOKE TESTS FAILED${NC}"
        echo ""
        echo "Troubleshooting:"
        echo "  1. Check service logs: journalctl -u timemachine -n 100"
        echo "  2. Check service status: systemctl status timemachine"
        echo "  3. Run full test suite: cd backend && pytest tests/ -v"
        return 1
    fi
}

# Main entry point
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
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
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --host HOST     API host (default: localhost)"
                echo "  --port PORT     API port (default: 8000)"
                echo "  --timeout SECS  Maximum test duration (default: 60)"
                echo "  --help, -h      Show this help"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Pre-flight check
    if ! check_service_running; then
        exit 2
    fi

    # Run smoke tests
    run_smoke_tests || true

    # Print summary and exit
    if print_summary; then
        exit 0
    else
        exit 1
    fi
}

main "$@"

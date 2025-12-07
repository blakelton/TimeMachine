#!/bin/bash
#
# TimeMachine API Test Script
# Tests core API endpoints and reports results
#
# Usage: ./test-api.sh [--report] [--host HOST] [--port PORT]
#

set -euo pipefail

# Default configuration
HOST="${TIMEMACHINE_HOST:-localhost}"
PORT="${TIMEMACHINE_PORT:-8000}"
BASE_URL="http://${HOST}:${PORT}/api/v1"
GENERATE_REPORT=false
REPORT_FILE=""
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0
declare -a FAILED_TESTS=()
declare -a TEST_RESULTS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --report)
            GENERATE_REPORT=true
            REPORT_FILE="${2:-}"
            if [[ -n "$REPORT_FILE" && ! "$REPORT_FILE" =~ ^-- ]]; then
                shift
            else
                REPORT_FILE="test-report-$(date +%Y%m%d-%H%M%S).md"
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
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --report [FILE]  Generate markdown report (default: test-report-TIMESTAMP.md)"
            echo "  --host HOST      API host (default: localhost, or TIMEMACHINE_HOST env)"
            echo "  --port PORT      API port (default: 8000, or TIMEMACHINE_PORT env)"
            echo "  --verbose, -v    Show detailed output"
            echo "  --help, -h       Show this help message"
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
    local response="${4:-}"

    TEST_RESULTS+=("$name|$status|$message|$response")
}

# Test a single endpoint
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local expected_code="${4:-200}"
    local data="${5:-}"
    local content_type="${6:-application/json}"

    local url="${BASE_URL}${endpoint}"
    local response
    local http_code
    local body

    # Build curl command
    local curl_cmd="curl -s -w '\n%{http_code}' -X $method"

    if [[ -n "$data" ]]; then
        curl_cmd="$curl_cmd -H 'Content-Type: $content_type' -d '$data'"
    fi

    curl_cmd="$curl_cmd '$url'"

    # Execute request
    if response=$(eval "$curl_cmd" 2>&1); then
        # Split response into body and status code
        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | sed '$d')

        if [[ "$http_code" == "$expected_code" ]]; then
            log_pass "$name (HTTP $http_code)"
            log_verbose "Response: ${body:0:200}..."
            ((TESTS_PASSED++))
            record_result "$name" "PASS" "HTTP $http_code" "$body"
            return 0
        else
            log_fail "$name - Expected HTTP $expected_code, got $http_code"
            log_verbose "Response: $body"
            ((TESTS_FAILED++))
            FAILED_TESTS+=("$name: Expected HTTP $expected_code, got $http_code")
            record_result "$name" "FAIL" "Expected HTTP $expected_code, got $http_code" "$body"
            return 1
        fi
    else
        log_fail "$name - Request failed: $response"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$name: Request failed - $response")
        record_result "$name" "FAIL" "Request failed: $response" ""
        return 1
    fi
}

# Collect system diagnostics
collect_diagnostics() {
    local diag=""

    diag+="### Service Status\n\n"
    diag+="\`\`\`\n"
    if command -v systemctl &> /dev/null; then
        diag+="$(systemctl status timemachine 2>&1 | head -20 || echo 'Service not found')\n"
    else
        diag+="systemctl not available\n"
    fi
    diag+="\`\`\`\n\n"

    diag+="### Nginx Status\n\n"
    diag+="\`\`\`\n"
    if command -v systemctl &> /dev/null; then
        diag+="$(systemctl status nginx 2>&1 | head -15 || echo 'Nginx not found')\n"
    fi
    diag+="\`\`\`\n\n"

    diag+="### Nginx Configuration Test\n\n"
    diag+="\`\`\`\n"
    if command -v nginx &> /dev/null; then
        diag+="$(sudo nginx -t 2>&1 || echo 'Cannot test nginx config')\n"
    else
        diag+="nginx not installed\n"
    fi
    diag+="\`\`\`\n\n"

    diag+="### Port Listening\n\n"
    diag+="\`\`\`\n"
    diag+="Port $PORT: $(ss -tlnp 2>/dev/null | grep ":$PORT " || netstat -tlnp 2>/dev/null | grep ":$PORT " || echo 'Not listening')\n"
    diag+="Port 80: $(ss -tlnp 2>/dev/null | grep ":80 " || netstat -tlnp 2>/dev/null | grep ":80 " || echo 'Not listening')\n"
    diag+="\`\`\`\n\n"

    diag+="### Process Check\n\n"
    diag+="\`\`\`\n"
    diag+="Uvicorn: $(pgrep -fa uvicorn 2>/dev/null || echo 'Not running')\n"
    diag+="Python/FastAPI: $(pgrep -fa 'python.*app.main' 2>/dev/null || echo 'Not running')\n"
    diag+="\`\`\`\n\n"

    diag+="### Recent Service Logs\n\n"
    diag+="\`\`\`\n"
    if command -v journalctl &> /dev/null; then
        diag+="$(journalctl -u timemachine -n 20 --no-pager 2>&1 || echo 'No logs available')\n"
    else
        diag+="journalctl not available\n"
    fi
    diag+="\`\`\`\n\n"

    diag+="### Nginx Error Logs\n\n"
    diag+="\`\`\`\n"
    if [[ -f /var/log/nginx/error.log ]]; then
        diag+="$(sudo tail -20 /var/log/nginx/error.log 2>&1 || echo 'Cannot read nginx logs')\n"
    else
        diag+="Nginx error log not found at /var/log/nginx/error.log\n"
    fi
    diag+="\`\`\`\n"

    echo -e "$diag"
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

        # Quick diagnostics to console
        echo "--- Quick Diagnostics ---"
        echo ""
        echo "Service status:"
        systemctl is-active timemachine 2>/dev/null || echo "  timemachine service: not found/inactive"
        systemctl is-active nginx 2>/dev/null || echo "  nginx service: not found/inactive"
        echo ""
        echo "Port check:"
        if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
            echo "  Port $PORT: LISTENING"
        else
            echo "  Port $PORT: NOT LISTENING"
        fi
        if ss -tlnp 2>/dev/null | grep -q ":80 "; then
            echo "  Port 80: LISTENING"
        else
            echo "  Port 80: NOT LISTENING"
        fi
        echo ""
        echo "To start manually:"
        echo "  sudo systemctl start timemachine"
        echo "  # OR for development:"
        echo "  cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
        return 1
    fi
}

# Generate markdown report
generate_report() {
    local report_path="$1"

    cat > "$report_path" << EOF
# TimeMachine API Test Report

**Generated:** $(date '+%Y-%m-%d %H:%M:%S')
**Server:** ${BASE_URL}
**Host:** $(hostname)

## Summary

| Metric | Count |
|--------|-------|
| Tests Passed | $TESTS_PASSED |
| Tests Failed | $TESTS_FAILED |
| Tests Skipped | $TESTS_SKIPPED |
| **Total** | $((TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED)) |

**Status:** $(if [[ $TESTS_FAILED -eq 0 ]]; then echo "✅ ALL TESTS PASSED"; else echo "❌ SOME TESTS FAILED"; fi)

## Test Results

| Test Name | Status | Details |
|-----------|--------|---------|
EOF

    for result in "${TEST_RESULTS[@]}"; do
        IFS='|' read -r name status message response <<< "$result"
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
    fi

    cat >> "$report_path" << EOF

## Environment

- **Python Version:** $(python3 --version 2>&1 || echo "Not available")
- **OS:** $(uname -s) $(uname -r)
- **Date:** $(date)

## Recommendations

EOF

    if [[ $TESTS_FAILED -gt 0 ]]; then
        cat >> "$report_path" << EOF
Based on the failed tests, consider:

1. Check server logs: \`timemachine logs\` or \`journalctl -u timemachine\`
2. Verify database connectivity: \`sqlite3 /var/lib/timemachine/timemachine.db ".tables"\`
3. Check for port conflicts: \`lsof -i :$PORT\`
4. Review application configuration in \`/etc/timemachine/timemachine.env\`

## System Diagnostics

EOF
        # Add detailed diagnostics to report
        collect_diagnostics >> "$report_path"
    else
        echo "All tests passed. System is functioning correctly." >> "$report_path"
    fi

    echo "" >> "$report_path"
    echo "---" >> "$report_path"
    echo "*Report generated by TimeMachine test-api.sh*" >> "$report_path"
}

# Generate failure report when server is unreachable
generate_server_failure_report() {
    local report_path="$1"

    cat > "$report_path" << EOF
# TimeMachine API Test Report

**Generated:** $(date '+%Y-%m-%d %H:%M:%S')
**Server:** ${BASE_URL}
**Host:** $(hostname)

## Summary

| Metric | Count |
|--------|-------|
| Tests Passed | 0 |
| Tests Failed | 1 |
| Tests Skipped | 0 |
| **Total** | 1 |

**Status:** ❌ SERVER UNREACHABLE

## Test Results

| Test Name | Status | Details |
|-----------|--------|---------|
| Server Connectivity | ❌ FAIL | Server not responding at ${BASE_URL} |

## Environment

- **Python Version:** $(python3 --version 2>&1 || echo "Not available")
- **OS:** $(uname -s) $(uname -r)
- **Architecture:** $(uname -m)
- **Date:** $(date)

## System Diagnostics

EOF

    collect_diagnostics >> "$report_path"

    cat >> "$report_path" << EOF

## Troubleshooting Steps

1. **Check if TimeMachine service is running:**
   \`\`\`bash
   sudo systemctl status timemachine
   sudo systemctl start timemachine
   \`\`\`

2. **Check if nginx is running (if using reverse proxy):**
   \`\`\`bash
   sudo systemctl status nginx
   sudo systemctl start nginx
   \`\`\`

3. **Check nginx configuration:**
   \`\`\`bash
   sudo nginx -t
   sudo cat /etc/nginx/sites-enabled/timemachine
   \`\`\`

4. **Start manually for debugging:**
   \`\`\`bash
   cd ~/projects/TimeMachine/backend
   source venv/bin/activate
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   \`\`\`

5. **Check logs:**
   \`\`\`bash
   journalctl -u timemachine -f
   sudo tail -f /var/log/nginx/error.log
   \`\`\`

---
*Report generated by TimeMachine test-api.sh*
EOF
}

# Main test execution
main() {
    echo ""
    echo "=========================================="
    echo "  TimeMachine API Test Suite"
    echo "=========================================="
    echo ""

    # Check server
    if ! check_server; then
        # Generate failure report if requested
        if $GENERATE_REPORT; then
            generate_server_failure_report "$REPORT_FILE"
            log_info "Failure report saved to: $REPORT_FILE"
        fi
        exit 1
    fi

    echo ""
    log_info "Running API tests..."
    echo ""

    # ==========================================
    # Health & System Tests
    # ==========================================
    echo "--- Health & System ---"

    test_endpoint "Health Check" "GET" "/health" 200

    # ==========================================
    # Camera Tests
    # ==========================================
    echo ""
    echo "--- Camera Endpoints ---"

    test_endpoint "List Cameras" "GET" "/cameras" 200
    test_endpoint "Discover Cameras" "POST" "/cameras/discover" 200

    # Try to get a specific camera (may not exist)
    if curl -s "${BASE_URL}/cameras" | grep -q '"id":'; then
        test_endpoint "Get Camera (ID 1)" "GET" "/cameras/1" 200 || true
    else
        log_skip "Get Camera - No cameras configured"
        ((TESTS_SKIPPED++))
        record_result "Get Camera (ID 1)" "SKIP" "No cameras configured" ""
    fi

    # ==========================================
    # Jobs Tests
    # ==========================================
    echo ""
    echo "--- Jobs Endpoints ---"

    test_endpoint "List Jobs" "GET" "/jobs" 200
    test_endpoint "List Running Jobs" "GET" "/jobs/running" 200

    # ==========================================
    # Output Config Tests
    # ==========================================
    echo ""
    echo "--- Output Config Endpoints ---"

    test_endpoint "Get Output Config" "GET" "/output-config" 200

    # ==========================================
    # Temperature Tests (Stub)
    # ==========================================
    echo ""
    echo "--- Temperature Endpoints (Stub) ---"

    test_endpoint "Get Temperature Config" "GET" "/temperature/config" 200
    test_endpoint "Get Temperature Status" "GET" "/temperature/status" 200

    # ==========================================
    # WebSocket Test (basic connectivity)
    # ==========================================
    echo ""
    echo "--- WebSocket ---"

    # WebSocket test is more complex, just check the endpoint exists
    log_skip "WebSocket - Manual testing recommended"
    ((TESTS_SKIPPED++))
    record_result "WebSocket Connection" "SKIP" "Requires WebSocket client" ""

    # ==========================================
    # Summary
    # ==========================================
    echo ""
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

#!/bin/bash
# Generate test coverage report in Markdown format
# Usage: ./scripts/generate-coverage-report.sh
# Output: backend/COVERAGE.md

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
OUTPUT_FILE="$BACKEND_DIR/COVERAGE.md"

cd "$BACKEND_DIR"

echo "Running tests with coverage..."

# Run pytest with coverage and capture output
source /opt/timemachine/venv/bin/activate

# Run tests and capture results
TEST_OUTPUT=$(python -m pytest tests/ -v --tb=no --no-header -q 2>&1) || true
COVERAGE_OUTPUT=$(python -m pytest tests/ --cov=app --cov-report=term-missing --tb=no -q 2>&1) || true

# Extract test counts
PASSED=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= passed)' | tail -1 || echo "0")
FAILED=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= failed)' | tail -1 || echo "0")
WARNINGS=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= warning)' | tail -1 || echo "0")
TOTAL=$((PASSED + FAILED))

# Extract overall coverage percentage
TOTAL_COVERAGE=$(echo "$COVERAGE_OUTPUT" | grep "^TOTAL" | awk '{print $NF}' | tr -d '%')

# Get timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Generate the markdown report
cat > "$OUTPUT_FILE" << EOF
# Test Coverage Report

**Generated:** $TIMESTAMP
**Branch:** $(git branch --show-current 2>/dev/null || echo "unknown")
**Commit:** $(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | $TOTAL |
| Passed | $PASSED |
| Failed | $FAILED |
| Warnings | $WARNINGS |
| **Coverage** | **${TOTAL_COVERAGE}%** |

## Coverage by Module

| Module | Stmts | Miss | Cover | Status |
|--------|-------|------|-------|--------|
EOF

# Parse coverage output and add to report
echo "$COVERAGE_OUTPUT" | grep "^app/" | while read line; do
    # Parse each line: app/module.py    100    50    50%   1-25
    MODULE=$(echo "$line" | awk '{print $1}')
    STMTS=$(echo "$line" | awk '{print $2}')
    MISS=$(echo "$line" | awk '{print $3}')
    COVER=$(echo "$line" | awk '{print $4}' | tr -d '%')

    # Determine status emoji based on coverage
    if [ "$COVER" -ge 80 ]; then
        STATUS="✅"
    elif [ "$COVER" -ge 50 ]; then
        STATUS="⚠️"
    elif [ "$COVER" -gt 0 ]; then
        STATUS="🔶"
    else
        STATUS="❌"
    fi

    # Shorten module path for readability
    SHORT_MODULE=$(echo "$MODULE" | sed 's|app/||')

    echo "| \`$SHORT_MODULE\` | $STMTS | $MISS | ${COVER}% | $STATUS |" >> "$OUTPUT_FILE"
done

# Add legend and test details
cat >> "$OUTPUT_FILE" << 'EOF'

### Coverage Legend

| Status | Meaning |
|--------|---------|
| ✅ | 80%+ coverage (good) |
| ⚠️ | 50-79% coverage (acceptable) |
| 🔶 | 1-49% coverage (needs improvement) |
| ❌ | 0% coverage (not tested) |

## Test Files

EOF

# List test files with test counts
echo "| Test File | Tests |" >> "$OUTPUT_FILE"
echo "|-----------|-------|" >> "$OUTPUT_FILE"

for test_file in tests/test_*.py tests/api/test_*.py tests/services/test_*.py; do
    if [ -f "$test_file" ]; then
        TEST_COUNT=$(grep -c "def test_" "$test_file" 2>/dev/null || echo "0")
        SHORT_NAME=$(echo "$test_file" | sed 's|tests/||')
        echo "| \`$SHORT_NAME\` | $TEST_COUNT |" >> "$OUTPUT_FILE"
    fi
done

# Add notes section
cat >> "$OUTPUT_FILE" << 'EOF'

## Notes

### Hardware-Dependent Code (Expected Low Coverage)

The following modules have low coverage because they require real hardware:

- `services/camera/*` - Requires physical cameras, GStreamer, v4l2
- `services/environment/*` - Requires GPIO, I2C sensors
- `services/observation/*` - Integration with camera subsystems

### Running Tests

```bash
# Quick test run
cd backend && pytest tests/ -v

# With coverage report
cd backend && pytest tests/ --cov=app --cov-report=html

# Run specific test file
cd backend && pytest tests/test_timelapse_regressions.py -v

# Run smoke tests after deployment
./scripts/smoke-test.sh
```

### Improving Coverage

To increase coverage for hardware-dependent code:

1. Create mock implementations for camera/sensor interfaces
2. Use dependency injection to swap real hardware for mocks
3. Add integration tests that run on actual hardware (CI excluded)
EOF

echo ""
echo "✅ Coverage report generated: $OUTPUT_FILE"
echo ""
echo "Summary: $PASSED passed, $FAILED failed, ${TOTAL_COVERAGE}% coverage"

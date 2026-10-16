#!/bin/bash

# Test script for Makefile log management commands
# Tests all log commands with various scenarios

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

echo "🧪 Testing Makefile Log Management Commands"
echo "============================================="

# Function to print test results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ $2${NC}"
        ((TESTS_FAILED++))
    fi
}

# Function to cleanup test files
cleanup() {
    rm -f logs/test*.log* go-service/logs/test*.log* 2>/dev/null || true
    rm -f /tmp/test_*.txt 2>/dev/null || true
}

# Setup
setup() {
    mkdir -p logs go-service/logs
}

# Trap to ensure cleanup on exit
# trap cleanup EXIT

setup

echo ""
echo "📋 Test 1: make logs with existing log files"
# Create test log files
echo '{"time":"2025-07-19T21:21:33.366813248Z","level":"INFO","msg":"Test Go log entry"}' > go-service/logs/go-service.log
echo '2025-07-19 21:21:33,366 - test - INFO - Test Python log entry' > logs/evaluation.log

if make logs > /tmp/test_logs_output.txt 2>&1; then
    if grep -q "Test Go log entry" /tmp/test_logs_output.txt && grep -q "Test Python log entry" /tmp/test_logs_output.txt; then
        print_result 0 "make logs displays both log files correctly"
    else
        print_result 1 "make logs output missing expected content"
    fi
else
    print_result 1 "make logs failed with existing log files"
fi

echo ""
echo "📋 Test 2: make logs with missing log files"
rm -f logs/evaluation.log go-service/logs/go-service.log

if make logs > /tmp/test_logs_missing.txt 2>&1; then
    print_result 1 "make logs should fail with missing log files"
else
    if grep -q "No log files found" /tmp/test_logs_missing.txt; then
        print_result 0 "make logs shows appropriate error message for missing files"
    else
        print_result 1 "make logs error message incorrect for missing files"
    fi
fi

echo ""
echo "📋 Test 3: make logs with level filtering"
# Recreate test log files with multiple levels
echo '{"time":"2025-07-19T21:21:33.366813248Z","level":"INFO","msg":"Info message"}' > go-service/logs/go-service.log
echo '{"time":"2025-07-19T21:21:34.366813248Z","level":"ERROR","msg":"Error message"}' >> go-service/logs/go-service.log
echo '2025-07-19 21:21:33,366 - test - INFO - Info Python message' > logs/evaluation.log
echo '2025-07-19 21:21:34,366 - test - ERROR - Error Python message' >> logs/evaluation.log

if make logs level=ERROR > /tmp/test_logs_error.txt 2>&1; then
    if grep -q "Error message" /tmp/test_logs_error.txt && grep -q "Error Python message" /tmp/test_logs_error.txt; then
        if ! grep -q "Info message" /tmp/test_logs_error.txt; then
            print_result 0 "make logs level=ERROR filters correctly"
        else
            print_result 1 "make logs level=ERROR includes non-error messages"
        fi
    else
        print_result 1 "make logs level=ERROR missing expected error messages"
    fi
else
    print_result 1 "make logs level=ERROR failed"
fi

echo ""
echo "📋 Test 4: make logs-clean confirmation (cancel)"
# Test cancellation
if echo "n" | make logs-clean > /tmp/test_logs_cancel.txt 2>&1; then
    print_result 1 "make logs-clean should exit with error when cancelled"
else
    if grep -q "Cleanup cancelled" /tmp/test_logs_cancel.txt; then
        if [ -f go-service/logs/go-service.log ]; then
            print_result 0 "make logs-clean cancellation works correctly"
        else
            print_result 1 "make logs-clean cancelled but files were deleted"
        fi
    else
        print_result 1 "make logs-clean cancellation message missing"
    fi
fi

echo ""
echo "📋 Test 5: make logs-clean confirmation (proceed)"
# Create test files to be cleaned
touch logs/test1.log logs/test2.log.1 go-service/logs/test3.log go-service/logs/test4.log.2

if echo "y" | make logs-clean > /tmp/test_logs_clean.txt 2>&1; then
    if [ ! -f logs/test1.log ] && [ ! -f go-service/logs/test3.log ]; then
        print_result 0 "make logs-clean removes log files correctly"
    else
        print_result 1 "make logs-clean failed to remove all log files"
    fi
else
    print_result 1 "make logs-clean failed when confirmed"
fi

echo ""
echo "📋 Test 6: make logs-tail command exists and starts"
# Create test log files
echo 'Test tail entry' > go-service/logs/go-service.log
echo 'Test tail Python entry' > logs/evaluation.log

# Test that logs-tail starts (using timeout to prevent hanging)
if timeout 2s make logs-tail > /tmp/test_logs_tail.txt 2>&1; then
    print_result 1 "logs-tail should not exit normally in 2 seconds"
else
    # Check if it was terminated (expected) and produced output
    if grep -q "Following logs in real-time" /tmp/test_logs_tail.txt; then
        print_result 0 "make logs-tail starts correctly"
    else
        print_result 1 "make logs-tail output missing expected content"
    fi
fi

echo ""
echo "📋 Test 7: Help command includes log management"
if make help > /tmp/test_help.txt 2>&1; then
    if grep -q "Log Management:" /tmp/test_help.txt && grep -q "make logs" /tmp/test_help.txt; then
        print_result 0 "make help includes log management commands"
    else
        print_result 1 "make help missing log management section"
    fi
else
    print_result 1 "make help command failed"
fi

echo ""
echo "============================================="
echo "🧪 Test Summary"
echo "============================================="
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed!${NC}"
    exit 1
fi
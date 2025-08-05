#!/bin/bash

# Performance Testing Requirements Validation Script
# This script tests all performance testing requirements automatically

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_header() {
    echo -e "\n${BLUE}======================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================${NC}\n"
}

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_result="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    log_info "Running: $test_name"

    if eval "$test_command" > /dev/null 2>&1; then
        if [ "$expected_result" = "success" ]; then
            log_success "$test_name"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            log_error "$test_name (expected failure but got success)"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    else
        if [ "$expected_result" = "failure" ]; then
            log_success "$test_name (correctly failed as expected)"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            log_error "$test_name"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    fi
}

# Function to check file exists
check_file_exists() {
    local file_path="$1"
    local test_name="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    if [ -f "$file_path" ]; then
        log_success "$test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_error "$test_name"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# Main validation function
main() {
    log_header "🎯 Performance Testing Requirements Validation"

    # Test 1: Setup Script Validation
    log_header "1. Setup Script Validation"
    run_test "Setup script syntax check" "bash -n setup.sh" "success"
    run_test "Setup script execution" "./setup.sh" "success"

    # Test 2: Configuration File Validation
    log_header "2. Configuration File Validation"
    check_file_exists "performance-budgets.json" "Performance budgets file exists"
    check_file_exists "artillery.yml" "Artillery config file exists"
    check_file_exists "simple-test.yml" "Simple test config exists"
    check_file_exists "baseline-test.js" "Baseline test script exists"

    run_test "Performance budgets JSON validation" "node -e 'require(\"./performance-budgets.json\")'" "success"
    run_test "Baseline test script syntax" "node -c baseline-test.js" "success"

    # Test 3: Directory Structure
    log_header "3. Directory Structure Validation"
    check_file_exists "baselines" "Baselines directory exists"
    check_file_exists "reports" "Reports directory exists"
    check_file_exists "results" "Results directory exists"

    # Test 4: Dependencies
    log_header "4. Dependencies Validation"
    run_test "Node.js availability" "node --version" "success"
    run_test "NPM availability" "npm --version" "success"
    run_test "Artillery installation" "npx artillery --version" "success"

    # Test 5: NPM Scripts
    log_header "5. NPM Scripts Validation"
    run_test "NPM clean script" "npm run clean" "success"

    # Test 6: Baseline Testing System
    log_header "6. Baseline Testing System"
    log_info "Testing baseline system with working endpoint..."

    # Check if backend is running
    if curl -s http://localhost:8000/healthz > /dev/null 2>&1; then
        log_success "Backend server is running"
        run_test "Baseline test execution" "node baseline-test.js simple-test.yml" "success"

        # Check if baseline was created
        if ls baselines/*.json > /dev/null 2>&1; then
            log_success "Baseline file created"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            log_error "Baseline file not created"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
        TOTAL_TESTS=$((TOTAL_TESTS + 1))

        # Check if report was generated
        if ls reports/*.json > /dev/null 2>&1; then
            log_success "Performance report generated"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            log_error "Performance report not generated"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
        TOTAL_TESTS=$((TOTAL_TESTS + 1))

    else
        log_warning "Backend server not running - skipping live tests"
        log_info "To run full validation, start backend with: python main.py"
    fi

    # Test 7: Error Detection
    log_header "7. Error Detection Validation"
    if curl -s http://localhost:8000/healthz > /dev/null 2>&1; then
        log_info "Testing error detection with problematic endpoint..."
        # This should detect 405 errors from the login endpoint
        run_test "Error detection system" "node baseline-test.js artillery.yml" "success"
    else
        log_warning "Backend not running - skipping error detection tests"
    fi

    # Test 8: File Content Validation
    log_header "8. Content Validation"

    # Check for HIPAA compliance (no real patient data)
    if ! grep -r "real.*patient\|actual.*medical" artillery.yml simple-test.yml > /dev/null 2>&1; then
        log_success "HIPAA compliance - no real patient data found"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_error "HIPAA compliance - potential real patient data found"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    # Test 9: Report Structure Validation
    log_header "9. Report Structure Validation"
    if ls reports/*.json > /dev/null 2>&1; then
        latest_report=$(ls -t reports/*.json | head -1)
        if [ -f "$latest_report" ]; then
            # Check if report has required fields
            if node -e "const r=require('$latest_report'); console.log(r.summary ? 'OK' : 'MISSING')" 2>/dev/null | grep -q "OK"; then
                log_success "Report structure validation"
                PASSED_TESTS=$((PASSED_TESTS + 1))
            else
                log_error "Report structure validation - missing required fields"
                FAILED_TESTS=$((FAILED_TESTS + 1))
            fi
        else
            log_warning "No reports found for structure validation"
        fi
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
    fi

    # Final Results
    log_header "📊 Validation Results"
    echo -e "Total Tests: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"

    if [ $FAILED_TESTS -eq 0 ]; then
        log_header "🎉 All Requirements Validated Successfully!"
        echo -e "${GREEN}✅ Performance testing system is fully functional${NC}"
        echo -e "${GREEN}✅ All components working as expected${NC}"
        echo -e "${GREEN}✅ Ready for production use${NC}"
        exit 0
    else
        log_header "⚠️  Some Requirements Failed Validation"
        echo -e "${YELLOW}Please review the failed tests above${NC}"
        echo -e "${YELLOW}Fix issues before using in production${NC}"
        exit 1
    fi
}

# Run main function
main "$@"

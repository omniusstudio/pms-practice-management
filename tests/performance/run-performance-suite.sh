#!/bin/bash

# Performance Suite Runner
# Mental Health Practice Management System - HIPAA Compliant
# 
# This script runs the complete performance testing suite including:
# - Budget validation
# - Baseline comparison
# - Report generation
# - Dashboard updates

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_DIR="$SCRIPT_DIR/results"
REPORTS_DIR="$SCRIPT_DIR/reports"
LOG_FILE="$SCRIPT_DIR/performance-suite-$TIMESTAMP.log"

# Default configuration
ENVIRONMENT="${NODE_ENV:-development}"
SAVE_BASELINE="${SAVE_BASELINE:-false}"
TEST_SCENARIOS="baseline,load,stress"
SKIP_BUDGETS="false"
QUIET_MODE="false"
GENERATE_REPORT="true"
UPLOAD_METRICS="false"

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
}

log_step() {
    echo -e "${PURPLE}🔄 $1${NC}" | tee -a "$LOG_FILE"
}

log_metric() {
    echo -e "${CYAN}📊 $1${NC}" | tee -a "$LOG_FILE"
}

print_banner() {
    echo -e "${BLUE}"
    echo "═══════════════════════════════════════════════════════════════"
    echo "🎯 Performance Budget & Baseline Testing Suite"
    echo "   Mental Health Practice Management System"
    echo "═══════════════════════════════════════════════════════════════"
    echo -e "${NC}"
    echo "📅 Started: $(date)"
    echo "🌍 Environment: $ENVIRONMENT"
    echo "📝 Log File: $LOG_FILE"
    echo ""
}

print_summary() {
    local overall_status="$1"
    local test_count="$2"
    local violation_count="$3"
    local regression_count="$4"
    
    echo -e "${BLUE}"
    echo "═══════════════════════════════════════════════════════════════"
    echo "📊 PERFORMANCE SUITE SUMMARY"
    echo "═══════════════════════════════════════════════════════════════"
    echo -e "${NC}"
    
    if [ "$overall_status" = "PASS" ]; then
        echo -e "${GREEN}✅ Overall Status: PASS${NC}"
    else
        echo -e "${RED}❌ Overall Status: FAIL${NC}"
    fi
    
    echo "📈 Tests Executed: $test_count"
    echo "🚨 Budget Violations: $violation_count"
    echo "📉 Performance Regressions: $regression_count"
    echo "📅 Completed: $(date)"
    echo "⏱️  Duration: $(($(date +%s) - START_TIME)) seconds"
    echo ""
    
    if [ -d "$REPORTS_DIR" ] && [ "$(ls -A $REPORTS_DIR 2>/dev/null)" ]; then
        echo -e "${CYAN}📁 Generated Reports:${NC}"
        ls -la "$REPORTS_DIR"/*$TIMESTAMP* 2>/dev/null | while read -r line; do
            echo "   $line"
        done
        echo ""
    fi
    
    echo -e "${BLUE}🔗 Next Steps:${NC}"
    if [ "$overall_status" = "FAIL" ]; then
        echo "   1. Review detailed results in $REPORTS_DIR"
        echo "   2. Analyze performance regressions and budget violations"
        echo "   3. Investigate root causes and optimize code"
        echo "   4. Re-run tests after fixes"
    else
        echo "   1. Review performance trends in monitoring dashboard"
        echo "   2. Consider updating baselines if significant improvements"
        echo "   3. Monitor production performance"
    fi
    echo ""
}

check_prerequisites() {
    log_step "Checking prerequisites..."
    
    # Check Node.js
    if ! command -v node >/dev/null 2>&1; then
        log_error "Node.js is required but not installed"
        exit 1
    fi
    
    # Check npm
    if ! command -v npm >/dev/null 2>&1; then
        log_error "npm is required but not installed"
        exit 1
    fi
    
    # Check Artillery
    if ! command -v artillery >/dev/null 2>&1 && ! npx artillery --version >/dev/null 2>&1; then
        log_error "Artillery is required but not installed"
        log_info "Run: npm install -g artillery"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

setup_environment() {
    log_step "Setting up test environment..."
    
    cd "$SCRIPT_DIR"
    
    # Create directories
    mkdir -p "$RESULTS_DIR" "$REPORTS_DIR"
    
    # Install dependencies if needed
    if [ -f "package.json" ] && [ ! -d "node_modules" ]; then
        log_info "Installing dependencies..."
        npm install
    fi
    
    # Validate configuration
    if [ -f "performance-budgets.json" ]; then
        node -e "require('./performance-budgets.json'); console.log('✅ Performance budgets valid');" >> "$LOG_FILE" 2>&1
    else
        log_error "performance-budgets.json not found"
        exit 1
    fi
    
    if [ -f "artillery.yml" ]; then
        npx artillery validate artillery.yml >> "$LOG_FILE" 2>&1
        log_success "Artillery configuration validated"
    else
        log_error "artillery.yml not found"
        exit 1
    fi
    
    log_success "Environment setup completed"
}

check_target_availability() {
    log_step "Checking target application availability..."
    
    local target_url
    target_url=$(grep -o 'target: ["\']\?[^"\']\+' artillery.yml | cut -d' ' -f2 | tr -d '"\'' || echo "")
    
    if [ -n "$target_url" ]; then
        log_info "Testing connectivity to $target_url..."
        
        local max_attempts=5
        local attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            if curl -f -s "$target_url/api/health" >/dev/null 2>&1; then
                log_success "Target application is accessible"
                return 0
            fi
            
            log_warning "Attempt $attempt/$max_attempts: Target not accessible, retrying in 10s..."
            sleep 10
            attempt=$((attempt + 1))
        done
        
        log_error "Target application is not accessible after $max_attempts attempts"
        log_error "Please ensure the application is running at $target_url"
        exit 1
    else
        log_warning "Could not determine target URL from artillery.yml"
    fi
}

run_performance_test() {
    local scenario="$1"
    log_step "Running performance test: $scenario"
    
    local test_start_time
    test_start_time=$(date +%s)
    
    # Set environment variables for the test
    export NODE_ENV="$ENVIRONMENT"
    export GITHUB_SHA="${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo 'unknown')}"
    export CI="${CI:-false}"
    export TEST_SCENARIO="$scenario"
    
    if [ "$SAVE_BASELINE" = "true" ]; then
        export SAVE_BASELINE="true"
    fi
    
    # Build command arguments
    local cmd_args=()
    if [ "$QUIET_MODE" = "true" ]; then
        cmd_args+=("--quiet")
    fi
    if [ "$SKIP_BUDGETS" = "true" ]; then
        cmd_args+=("--skip-budgets")
    fi
    
    # Run the test
    local test_result=0
    if node baseline-test.js "${cmd_args[@]}" >> "$LOG_FILE" 2>&1; then
        local test_duration=$(($(date +%s) - test_start_time))
        log_success "Test '$scenario' completed in ${test_duration}s"
        return 0
    else
        local test_duration=$(($(date +%s) - test_start_time))
        log_error "Test '$scenario' failed after ${test_duration}s"
        return 1
    fi
}

parse_test_results() {
    log_step "Parsing test results..."
    
    local latest_report
    latest_report=$(ls -t "$REPORTS_DIR"/performance-report-*.json 2>/dev/null | head -n1 || echo "")
    
    if [ -n "$latest_report" ] && [ -f "$latest_report" ]; then
        log_info "Parsing results from: $(basename "$latest_report")"
        
        # Extract metrics using jq
        local overall_status
        local budget_status
        local regression_status
        local violation_count
        local regression_count
        
        overall_status=$(jq -r '.summary.overall_status // "UNKNOWN"' "$latest_report")
        budget_status=$(jq -r '.summary.budget_status // "UNKNOWN"' "$latest_report")
        regression_status=$(jq -r '.summary.regression_status // "UNKNOWN"' "$latest_report")
        violation_count=$(jq '.budget_validation.violations | length' "$latest_report" 2>/dev/null || echo "0")
        regression_count=$(jq '.baseline_comparison.regressions | length // 0' "$latest_report" 2>/dev/null || echo "0")
        
        # Log key metrics
        log_metric "Overall Status: $overall_status"
        log_metric "Budget Status: $budget_status"
        log_metric "Regression Status: $regression_status"
        log_metric "Budget Violations: $violation_count"
        log_metric "Performance Regressions: $regression_count"
        
        # Export for summary
        echo "$overall_status" > "$SCRIPT_DIR/.last_overall_status"
        echo "$violation_count" > "$SCRIPT_DIR/.last_violation_count"
        echo "$regression_count" > "$SCRIPT_DIR/.last_regression_count"
        
        return 0
    else
        log_error "No test results found to parse"
        return 1
    fi
}

generate_consolidated_report() {
    if [ "$GENERATE_REPORT" != "true" ]; then
        return 0
    fi
    
    log_step "Generating consolidated report..."
    
    local consolidated_file="$REPORTS_DIR/consolidated-report-$TIMESTAMP.json"
    
    # Create consolidated report structure
    cat > "$consolidated_file" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "environment": "$ENVIRONMENT",
  "git_commit": "${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo 'unknown')}",
  "test_scenarios": [],
  "summary": {
    "total_tests": 0,
    "passed_tests": 0,
    "failed_tests": 0,
    "total_violations": 0,
    "total_regressions": 0
  }
}
EOF
    
    # Aggregate individual reports
    local total_tests=0
    local passed_tests=0
    local failed_tests=0
    local total_violations=0
    local total_regressions=0
    
    for report in "$REPORTS_DIR"/performance-report-*$TIMESTAMP*.json; do
        if [ -f "$report" ]; then
            total_tests=$((total_tests + 1))
            
            local status
            status=$(jq -r '.summary.overall_status // "FAIL"' "$report")
            
            if [ "$status" = "PASS" ]; then
                passed_tests=$((passed_tests + 1))
            else
                failed_tests=$((failed_tests + 1))
            fi
            
            local violations
            local regressions
            violations=$(jq '.budget_validation.violations | length' "$report" 2>/dev/null || echo "0")
            regressions=$(jq '.baseline_comparison.regressions | length // 0' "$report" 2>/dev/null || echo "0")
            
            total_violations=$((total_violations + violations))
            total_regressions=$((total_regressions + regressions))
        fi
    done
    
    # Update consolidated report
    jq --arg total "$total_tests" \
       --arg passed "$passed_tests" \
       --arg failed "$failed_tests" \
       --arg violations "$total_violations" \
       --arg regressions "$total_regressions" \
       '.summary.total_tests = ($total | tonumber) |
        .summary.passed_tests = ($passed | tonumber) |
        .summary.failed_tests = ($failed | tonumber) |
        .summary.total_violations = ($violations | tonumber) |
        .summary.total_regressions = ($regressions | tonumber)' \
       "$consolidated_file" > "$consolidated_file.tmp" && mv "$consolidated_file.tmp" "$consolidated_file"
    
    log_success "Consolidated report generated: $(basename "$consolidated_file")"
}

upload_metrics_to_prometheus() {
    if [ "$UPLOAD_METRICS" != "true" ]; then
        return 0
    fi
    
    log_step "Uploading metrics to Prometheus..."
    
    # This would integrate with Prometheus pushgateway or similar
    # Implementation depends on your monitoring setup
    
    log_info "Metrics upload feature not implemented yet"
}

cleanup() {
    log_step "Cleaning up temporary files..."
    
    # Remove temporary status files
    rm -f "$SCRIPT_DIR/.last_overall_status"
    rm -f "$SCRIPT_DIR/.last_violation_count"
    rm -f "$SCRIPT_DIR/.last_regression_count"
    
    # Clean old log files (keep last 10)
    find "$SCRIPT_DIR" -name "performance-suite-*.log" -type f | sort -r | tail -n +11 | xargs rm -f 2>/dev/null || true
    
    log_success "Cleanup completed"
}

show_help() {
    cat << EOF
Performance Suite Runner

Usage: $0 [options]

Options:
  -e, --environment ENV     Target environment (development|staging|production)
  -s, --scenarios LIST      Comma-separated test scenarios (baseline,load,stress)
  -b, --save-baseline       Save results as new baseline
  -q, --quiet              Run in quiet mode
  --skip-budgets           Skip budget validation
  --no-report              Skip report generation
  --upload-metrics         Upload metrics to monitoring system
  -h, --help               Show this help message

Examples:
  $0                                    # Run all scenarios with default settings
  $0 -e staging -s baseline,load        # Run specific scenarios in staging
  $0 -b -e production                   # Run all scenarios and save baseline
  $0 -q --skip-budgets                  # Run quietly without budget validation

Environment Variables:
  NODE_ENV                 Target environment
  SAVE_BASELINE           Save results as baseline (true/false)
  TEST_SCENARIOS          Comma-separated scenarios to run
  SKIP_BUDGETS           Skip budget validation (true/false)
  QUIET_MODE             Run in quiet mode (true/false)
  GENERATE_REPORT        Generate consolidated report (true/false)
  UPLOAD_METRICS         Upload metrics to monitoring (true/false)

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -s|--scenarios)
            TEST_SCENARIOS="$2"
            shift 2
            ;;
        -b|--save-baseline)
            SAVE_BASELINE="true"
            shift
            ;;
        -q|--quiet)
            QUIET_MODE="true"
            shift
            ;;
        --skip-budgets)
            SKIP_BUDGETS="true"
            shift
            ;;
        --no-report)
            GENERATE_REPORT="false"
            shift
            ;;
        --upload-metrics)
            UPLOAD_METRICS="true"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
main() {
    START_TIME=$(date +%s)
    
    # Initialize log file
    echo "Performance Suite Runner - $(date)" > "$LOG_FILE"
    echo "Environment: $ENVIRONMENT" >> "$LOG_FILE"
    echo "Scenarios: $TEST_SCENARIOS" >> "$LOG_FILE"
    echo "Save Baseline: $SAVE_BASELINE" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    
    print_banner
    
    # Setup and validation
    check_prerequisites
    setup_environment
    check_target_availability
    
    # Run tests
    local test_count=0
    local failed_tests=0
    
    IFS=',' read -ra SCENARIOS <<< "$TEST_SCENARIOS"
    for scenario in "${SCENARIOS[@]}"; do
        scenario=$(echo "$scenario" | xargs)  # Trim whitespace
        if [ -n "$scenario" ]; then
            test_count=$((test_count + 1))
            if ! run_performance_test "$scenario"; then
                failed_tests=$((failed_tests + 1))
            fi
        fi
    done
    
    # Parse results and generate reports
    if parse_test_results; then
        generate_consolidated_report
    fi
    
    # Upload metrics if requested
    upload_metrics_to_prometheus
    
    # Determine overall status
    local overall_status="PASS"
    local violation_count=0
    local regression_count=0
    
    if [ -f "$SCRIPT_DIR/.last_overall_status" ]; then
        overall_status=$(cat "$SCRIPT_DIR/.last_overall_status")
    fi
    if [ -f "$SCRIPT_DIR/.last_violation_count" ]; then
        violation_count=$(cat "$SCRIPT_DIR/.last_violation_count")
    fi
    if [ -f "$SCRIPT_DIR/.last_regression_count" ]; then
        regression_count=$(cat "$SCRIPT_DIR/.last_regression_count")
    fi
    
    if [ $failed_tests -gt 0 ] || [ "$overall_status" = "FAIL" ]; then
        overall_status="FAIL"
    fi
    
    # Cleanup
    cleanup
    
    # Print summary
    print_summary "$overall_status" "$test_count" "$violation_count" "$regression_count"
    
    # Exit with appropriate code
    if [ "$overall_status" = "FAIL" ]; then
        exit 1
    else
        exit 0
    fi
}

# Run main function
main "$@"
#!/bin/bash
# Pre-commit hook to enforce test pyramid and coverage requirements

set -e

echo "🔍 Running pre-commit test gates..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall success
OVERALL_SUCCESS=true

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "success" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [ "$status" = "warning" ]; then
        echo -e "${YELLOW}⚠️  $message${NC}"
    else
        echo -e "${RED}❌ $message${NC}"
        OVERALL_SUCCESS=false
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required tools
echo "🔧 Checking required tools..."

if ! command_exists python3; then
    print_status "error" "Python 3 is required but not installed"
    exit 1
fi

if ! command_exists npm; then
    print_status "warning" "npm not found, skipping frontend tests"
fi

# Get list of changed files
CHANGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)
PYTHON_FILES=$(echo "$CHANGED_FILES" | grep -E '\.py$' || true)
TS_FILES=$(echo "$CHANGED_FILES" | grep -E '\.(ts|tsx|js|jsx)$' || true)
TEST_FILES=$(echo "$CHANGED_FILES" | grep -E 'test_.*\.py$|.*\.spec\.(ts|js)$|.*\.test\.(ts|js)$' || true)

echo "📁 Changed files analysis:"
echo "  Python files: $(echo "$PYTHON_FILES" | wc -l | tr -d ' ')"
echo "  TypeScript/JS files: $(echo "$TS_FILES" | wc -l | tr -d ' ')"
echo "  Test files: $(echo "$TEST_FILES" | wc -l | tr -d ' ')"

# Check if tests are required for changed files
REQUIRES_TESTS=false

if [ -n "$PYTHON_FILES" ]; then
    # Check if any Python files are in critical paths
    CRITICAL_PATHS="apps/backend/models apps/backend/services apps/backend/api apps/backend/routers"
    for path in $CRITICAL_PATHS; do
        if echo "$PYTHON_FILES" | grep -q "^$path/"; then
            REQUIRES_TESTS=true
            break
        fi
    done
fi

if [ -n "$TS_FILES" ]; then
    # Check if any TS files are in critical frontend paths
    CRITICAL_FRONTEND_PATHS="apps/frontend/src/components apps/frontend/src/services apps/frontend/src/utils"
    for path in $CRITICAL_FRONTEND_PATHS; do
        if echo "$TS_FILES" | grep -q "^$path/"; then
            REQUIRES_TESTS=true
            break
        fi
    done
fi

# Validate test pyramid structure
echo "\n🔺 Validating test pyramid structure..."

if [ -f "scripts/validate_test_pyramid.py" ]; then
    if python3 scripts/validate_test_pyramid.py > /tmp/test_pyramid_output 2>&1; then
        print_status "success" "Test pyramid structure is valid"
    else
        print_status "error" "Test pyramid validation failed"
        echo "Validation output:"
        cat /tmp/test_pyramid_output
        OVERALL_SUCCESS=false
    fi
else
    print_status "warning" "Test pyramid validation script not found"
fi

# Run backend tests if Python files changed
if [ -n "$PYTHON_FILES" ] && [ -d "apps/backend" ]; then
    echo "\n🧪 Running backend tests..."

    cd apps/backend

    # Run unit tests
    if python3 -m pytest tests/unit/ -v --tb=short > /tmp/backend_unit_output 2>&1; then
        print_status "success" "Backend unit tests passed"
    else
        print_status "error" "Backend unit tests failed"
        echo "Unit test output:"
        tail -20 /tmp/backend_unit_output
        OVERALL_SUCCESS=false
    fi

    # Run integration tests if they exist
    if [ -d "tests/integration" ]; then
        if python3 -m pytest tests/integration/ -v --tb=short > /tmp/backend_integration_output 2>&1; then
            print_status "success" "Backend integration tests passed"
        else
            print_status "error" "Backend integration tests failed"
            echo "Integration test output:"
            tail -20 /tmp/backend_integration_output
            OVERALL_SUCCESS=false
        fi
    fi

    # Check coverage for critical changes
    if [ "$REQUIRES_TESTS" = true ]; then
        echo "\n📊 Checking test coverage for critical changes..."

        if python3 -m pytest --cov=. --cov-report=term --cov-fail-under=80 > /tmp/coverage_output 2>&1; then
            print_status "success" "Coverage threshold met (80%+)"
        else
            print_status "error" "Coverage below threshold (80%)"
            echo "Coverage output:"
            grep -E "TOTAL|FAILED" /tmp/coverage_output || true
            OVERALL_SUCCESS=false
        fi

        # Check HIPAA compliance tests if HIPAA-related files changed
        HIPAA_PATHS="models/patient models/appointment services/auth services/encryption"
        HIPAA_CHANGED=false

        for path in $HIPAA_PATHS; do
            if echo "$PYTHON_FILES" | grep -q "apps/backend/$path"; then
                HIPAA_CHANGED=true
                break
            fi
        done

        if [ "$HIPAA_CHANGED" = true ]; then
            echo "\n🏥 Running HIPAA compliance tests..."

            if python3 -m pytest -m hipaa --cov=. --cov-report=term --cov-fail-under=100 > /tmp/hipaa_output 2>&1; then
                print_status "success" "HIPAA compliance tests passed (100% coverage)"
            else
                print_status "error" "HIPAA compliance tests failed or coverage below 100%"
                echo "HIPAA test output:"
                tail -20 /tmp/hipaa_output
                OVERALL_SUCCESS=false
            fi
        fi
    fi

    cd - > /dev/null
fi

# Run frontend tests if TS/JS files changed
if [ -n "$TS_FILES" ] && [ -d "apps/frontend" ] && command_exists npm; then
    echo "\n🎨 Running frontend tests..."

    cd apps/frontend

    # Check if dependencies are installed
    if [ ! -d "node_modules" ]; then
        print_status "warning" "Frontend dependencies not installed, skipping tests"
    else
        if npm test -- --run > /tmp/frontend_test_output 2>&1; then
            print_status "success" "Frontend tests passed"
        else
            print_status "error" "Frontend tests failed"
            echo "Frontend test output:"
            tail -20 /tmp/frontend_test_output
            OVERALL_SUCCESS=false
        fi

        # Check frontend coverage if critical files changed
        if [ "$REQUIRES_TESTS" = true ]; then
            if npm run test:coverage > /tmp/frontend_coverage_output 2>&1; then
                print_status "success" "Frontend coverage check passed"
            else
                print_status "warning" "Frontend coverage check failed or not configured"
                # Don't fail the commit for frontend coverage issues
            fi
        fi
    fi

    cd - > /dev/null
fi

# Check for test file requirements
if [ "$REQUIRES_TESTS" = true ] && [ -z "$TEST_FILES" ]; then
    print_status "error" "Critical code changes detected but no test files modified"
    echo "  Consider adding or updating tests for your changes"
    echo "  Critical paths that require tests:"
    echo "    - Backend: models/, services/, api/, routers/"
    echo "    - Frontend: components/, services/, utils/"
    OVERALL_SUCCESS=false
fi

# Security checks
echo "\n🔒 Running security checks..."

# Check for potential secrets in code
SECRET_PATTERNS="password|secret|key|token|api_key|private_key"
if echo "$CHANGED_FILES" | xargs grep -l -i -E "$SECRET_PATTERNS" 2>/dev/null | grep -v test; then
    print_status "warning" "Potential secrets detected in non-test files"
    echo "  Please review and ensure no actual secrets are committed"
    echo "  Use environment variables or secure vaults for secrets"
fi

# Check for PHI in logs or error messages
PHI_PATTERNS="ssn|social.security|patient.name|medical.record|diagnosis"
if echo "$PYTHON_FILES" | xargs grep -l -i -E "$PHI_PATTERNS" 2>/dev/null; then
    print_status "warning" "Potential PHI detected in code"
    echo "  Please ensure no PHI is logged or exposed in error messages"
fi

# Lint checks
echo "\n🧹 Running lint checks..."

if [ -n "$PYTHON_FILES" ] && command_exists flake8; then
    if echo "$PYTHON_FILES" | xargs flake8 > /tmp/flake8_output 2>&1; then
        print_status "success" "Python lint checks passed"
    else
        print_status "error" "Python lint checks failed"
        echo "Lint output:"
        cat /tmp/flake8_output
        OVERALL_SUCCESS=false
    fi
fi

# Final summary
echo "\n" + "=" * 60
if [ "$OVERALL_SUCCESS" = true ]; then
    print_status "success" "All pre-commit checks passed! 🎉"
    echo "=" * 60
    exit 0
else
    print_status "error" "Some pre-commit checks failed! 💥"
    echo "=" * 60
    echo "\nTo bypass these checks (not recommended), use:"
    echo "  git commit --no-verify"
    echo "\nTo fix issues:"
    echo "  1. Address failing tests and coverage"
    echo "  2. Add tests for critical code changes"
    echo "  3. Fix lint errors"
    echo "  4. Review security warnings"
    exit 1
fi

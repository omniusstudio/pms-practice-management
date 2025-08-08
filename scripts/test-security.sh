#!/bin/bash

# Security Testing Script for HIPAA-compliant PMS
# Tests TLS configuration, certificate validation, and security headers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
HOST="localhost"
PORT="8000"
HTTPS_PORT="8443"
TEST_TIMEOUT="10"

echo -e "${BLUE}=== HIPAA PMS Security Test Suite ===${NC}"
echo -e "Testing security configuration for ${HOST}:${PORT}"
echo ""

# Function to print test results
print_result() {
    local test_name="$1"
    local result="$2"
    local details="$3"

    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}✓ ${test_name}${NC}"
    elif [ "$result" = "FAIL" ]; then
        echo -e "${RED}✗ ${test_name}${NC}"
        if [ -n "$details" ]; then
            echo -e "  ${RED}Details: $details${NC}"
        fi
    elif [ "$result" = "WARN" ]; then
        echo -e "${YELLOW}⚠ ${test_name}${NC}"
        if [ -n "$details" ]; then
            echo -e "  ${YELLOW}Details: $details${NC}"
        fi
    else
        echo -e "${BLUE}ℹ ${test_name}${NC}"
        if [ -n "$details" ]; then
            echo -e "  ${BLUE}Details: $details${NC}"
        fi
    fi
}

# Test 1: Check if application is running
echo -e "${BLUE}1. Application Health Check${NC}"
if curl -s --connect-timeout $TEST_TIMEOUT "http://${HOST}:${PORT}/health" > /dev/null; then
    print_result "Application is running" "PASS"
else
    print_result "Application is not responding" "FAIL" "Make sure the application is running on port ${PORT}"
    exit 1
fi
echo ""

# Test 2: Security Headers Check
echo -e "${BLUE}2. Security Headers Test${NC}"
HEADERS=$(curl -s -I "http://${HOST}:${PORT}/health" 2>/dev/null || echo "")

if echo "$HEADERS" | grep -i "strict-transport-security" > /dev/null; then
    HSTS_VALUE=$(echo "$HEADERS" | grep -i "strict-transport-security" | cut -d':' -f2 | tr -d ' \r')
    print_result "HSTS Header Present" "PASS" "Value: $HSTS_VALUE"
else
    print_result "HSTS Header Missing" "FAIL" "Strict-Transport-Security header not found"
fi

if echo "$HEADERS" | grep -i "x-content-type-options" > /dev/null; then
    print_result "X-Content-Type-Options Header" "PASS"
else
    print_result "X-Content-Type-Options Header Missing" "WARN"
fi

if echo "$HEADERS" | grep -i "x-frame-options" > /dev/null; then
    print_result "X-Frame-Options Header" "PASS"
else
    print_result "X-Frame-Options Header Missing" "WARN"
fi

if echo "$HEADERS" | grep -i "x-xss-protection" > /dev/null; then
    print_result "X-XSS-Protection Header" "PASS"
else
    print_result "X-XSS-Protection Header Missing" "WARN"
fi

if echo "$HEADERS" | grep -i "content-security-policy" > /dev/null; then
    print_result "Content-Security-Policy Header" "PASS"
else
    print_result "Content-Security-Policy Header Missing" "WARN"
fi
echo ""

# Test 3: Cookie Security
echo -e "${BLUE}3. Cookie Security Test${NC}"
COOKIE_RESPONSE=$(curl -s -c /tmp/test_cookies.txt "http://${HOST}:${PORT}/health" 2>/dev/null || echo "")

if [ -f "/tmp/test_cookies.txt" ] && [ -s "/tmp/test_cookies.txt" ]; then
    if grep -i "secure" /tmp/test_cookies.txt > /dev/null; then
        print_result "Secure Cookie Flag" "PASS"
    else
        print_result "Secure Cookie Flag Missing" "WARN" "Cookies should have Secure flag in production"
    fi

    if grep -i "httponly" /tmp/test_cookies.txt > /dev/null; then
        print_result "HttpOnly Cookie Flag" "PASS"
    else
        print_result "HttpOnly Cookie Flag Missing" "WARN"
    fi

    rm -f /tmp/test_cookies.txt
else
    print_result "No cookies set" "INFO" "Application may not set cookies on health endpoint"
fi
echo ""

# Test 4: TLS Configuration (if HTTPS is available)
echo -e "${BLUE}4. TLS Configuration Test${NC}"
if command -v openssl > /dev/null; then
    # Test if HTTPS endpoint is available
    if timeout $TEST_TIMEOUT openssl s_client -connect "${HOST}:${HTTPS_PORT}" -verify_return_error < /dev/null > /dev/null 2>&1; then
        print_result "HTTPS Endpoint Available" "PASS" "Port ${HTTPS_PORT}"

        # Test TLS 1.2
        if timeout $TEST_TIMEOUT openssl s_client -connect "${HOST}:${HTTPS_PORT}" -tls1_2 < /dev/null > /dev/null 2>&1; then
            print_result "TLS 1.2 Support" "PASS"
        else
            print_result "TLS 1.2 Support" "FAIL" "TLS 1.2 should be supported"
        fi

        # Test TLS 1.3 (optional)
        if timeout $TEST_TIMEOUT openssl s_client -connect "${HOST}:${HTTPS_PORT}" -tls1_3 < /dev/null > /dev/null 2>&1; then
            print_result "TLS 1.3 Support" "PASS" "Modern TLS version supported"
        else
            print_result "TLS 1.3 Support" "INFO" "TLS 1.3 not available (optional)"
        fi

        # Test weak TLS versions (should fail)
        if timeout $TEST_TIMEOUT openssl s_client -connect "${HOST}:${HTTPS_PORT}" -tls1_1 < /dev/null > /dev/null 2>&1; then
            print_result "TLS 1.1 Rejected" "FAIL" "TLS 1.1 should be disabled"
        else
            print_result "TLS 1.1 Rejected" "PASS" "Weak TLS version properly rejected"
        fi

        if timeout $TEST_TIMEOUT openssl s_client -connect "${HOST}:${HTTPS_PORT}" -tls1 < /dev/null > /dev/null 2>&1; then
            print_result "TLS 1.0 Rejected" "FAIL" "TLS 1.0 should be disabled"
        else
            print_result "TLS 1.0 Rejected" "PASS" "Weak TLS version properly rejected"
        fi
    else
        print_result "HTTPS Endpoint" "WARN" "HTTPS not available on port ${HTTPS_PORT} (development mode)"
    fi
else
    print_result "OpenSSL not available" "WARN" "Cannot test TLS configuration"
fi
echo ""

# Test 5: Database Encryption (if available)
echo -e "${BLUE}5. Database Encryption Test${NC}"
if [ -f "apps/backend/tests/test_security_features.py" ]; then
    cd apps/backend
    if python -c "from services.database_encryption_service import get_database_encryption_service; print('Database encryption service available')" 2>/dev/null; then
        print_result "Database Encryption Service" "PASS" "Service is importable"
    else
        print_result "Database Encryption Service" "FAIL" "Service import failed"
    fi
    cd - > /dev/null
else
    print_result "Database Encryption Test" "WARN" "Test files not found"
fi
echo ""

# Test 6: Environment Configuration
echo -e "${BLUE}6. Environment Configuration Test${NC}"
if [ -f ".env" ] || [ -f "apps/backend/.env" ]; then
    ENV_FILE=".env"
    [ -f "apps/backend/.env" ] && ENV_FILE="apps/backend/.env"

    if grep -q "TLS_MIN_VERSION" "$ENV_FILE" 2>/dev/null; then
        TLS_VERSION=$(grep "TLS_MIN_VERSION" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"\r')
        if [ "$TLS_VERSION" = "TLSv1.2" ] || [ "$TLS_VERSION" = "TLSv1.3" ]; then
            print_result "TLS Minimum Version" "PASS" "Set to $TLS_VERSION"
        else
            print_result "TLS Minimum Version" "WARN" "Set to $TLS_VERSION (should be TLSv1.2 or TLSv1.3)"
        fi
    else
        print_result "TLS Configuration" "INFO" "Using default TLS settings"
    fi

    if grep -q "COOKIE_SECURE" "$ENV_FILE" 2>/dev/null; then
        COOKIE_SECURE=$(grep "COOKIE_SECURE" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"\r')
        if [ "$COOKIE_SECURE" = "true" ]; then
            print_result "Secure Cookies Configuration" "PASS"
        else
            print_result "Secure Cookies Configuration" "WARN" "Should be set to true in production"
        fi
    else
        print_result "Cookie Security Configuration" "INFO" "Using default cookie settings"
    fi
else
    print_result "Environment File" "WARN" "No .env file found"
fi
echo ""

# Test 7: Python Security Tests
echo -e "${BLUE}7. Python Security Tests${NC}"
if [ -f "apps/backend/tests/test_security_features.py" ]; then
    cd apps/backend
    if python -m pytest tests/test_security_features.py::TestSecurityConfig::test_security_config_defaults -v > /dev/null 2>&1; then
        print_result "Security Configuration Tests" "PASS"
    else
        print_result "Security Configuration Tests" "FAIL" "Some tests failed"
    fi
    cd - > /dev/null
else
    print_result "Python Security Tests" "WARN" "Test file not found"
fi
echo ""

# Test 8: Certificate Validation (if certificates exist)
echo -e "${BLUE}8. Certificate Validation${NC}"
CERT_PATHS=(
    "/etc/ssl/certs/pms.crt"
    "./certs/server.crt"
    "./ssl/certificate.pem"
    "apps/backend/ssl/cert.pem"
)

CERT_FOUND=false
for cert_path in "${CERT_PATHS[@]}"; do
    if [ -f "$cert_path" ]; then
        CERT_FOUND=true
        if openssl x509 -in "$cert_path" -noout -checkend 2592000 2>/dev/null; then
            EXPIRY=$(openssl x509 -in "$cert_path" -noout -enddate 2>/dev/null | cut -d'=' -f2)
            print_result "Certificate Validity" "PASS" "Expires: $EXPIRY"
        else
            print_result "Certificate Validity" "WARN" "Certificate expires within 30 days or is invalid"
        fi
        break
    fi
done

if [ "$CERT_FOUND" = false ]; then
    print_result "SSL Certificate" "INFO" "No certificates found in standard locations"
fi
echo ""

# Summary
echo -e "${BLUE}=== Security Test Summary ===${NC}"
echo "Test completed for ${HOST}:${PORT}"
echo ""
echo -e "${GREEN}✓ PASS${NC} - Security feature is properly configured"
echo -e "${YELLOW}⚠ WARN${NC} - Security feature needs attention"
echo -e "${RED}✗ FAIL${NC} - Security feature is not properly configured"
echo -e "${BLUE}ℹ INFO${NC} - Informational message"
echo ""
echo "For detailed security configuration, see docs/ENCRYPTION_SECURITY_GUIDE.md"
echo "To run comprehensive Python tests: cd apps/backend && python -m pytest tests/test_security_features.py -v"

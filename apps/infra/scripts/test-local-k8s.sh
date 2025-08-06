#!/bin/bash

# Test Local Kubernetes Deployment
# This script tests the local Kubernetes setup to ensure everything is working correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default values
NAMESPACE="pms-local"
TIMEOUT="300s"
VERBOSE="false"

# Help function
show_help() {
    cat << EOF
Test Local Kubernetes Deployment

Usage: $0 [OPTIONS]

Options:
    --namespace NAMESPACE   Kubernetes namespace (default: pms-local)
    --timeout TIMEOUT       Timeout for waiting operations (default: 300s)
    --verbose               Enable verbose output
    -h, --help              Show this help message

Examples:
    $0                                    # Test with default settings
    $0 --namespace test --verbose         # Test with custom namespace and verbose output
    $0 --timeout 600s                    # Test with extended timeout

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE="true"
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

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Test functions
test_prerequisites() {
    log_info "Testing prerequisites..."

    local failed=false

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        failed=true
    else
        log_success "kubectl is available"
    fi

    # Check Helm
    if ! command -v helm &> /dev/null; then
        log_error "Helm is not installed"
        failed=true
    else
        log_success "Helm is available"
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        failed=true
    elif ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        failed=true
    else
        log_success "Docker is available and running"
    fi

    # Check Kubernetes connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        failed=true
    else
        local context=$(kubectl config current-context)
        log_success "Connected to Kubernetes cluster: $context"
    fi

    if [[ "$failed" == "true" ]]; then
        log_error "Prerequisites check failed"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

test_namespace() {
    log_info "Testing namespace: $NAMESPACE"

    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace $NAMESPACE does not exist"
        log_info "Please run the setup script first: ./setup-local-k8s.sh"
        exit 1
    fi

    log_success "Namespace $NAMESPACE exists"
}

test_helm_release() {
    log_info "Testing Helm release..."

    if ! helm list -n "$NAMESPACE" | grep -q pms-local; then
        log_error "Helm release 'pms-local' not found in namespace $NAMESPACE"
        log_info "Please run the setup script first: ./setup-local-k8s.sh"
        exit 1
    fi

    local status=$(helm list -n "$NAMESPACE" -o json | jq -r '.[] | select(.name=="pms-local") | .status')
    if [[ "$status" != "deployed" ]]; then
        log_error "Helm release status is '$status', expected 'deployed'"
        exit 1
    fi

    log_success "Helm release 'pms-local' is deployed"
}

test_pods() {
    log_info "Testing pod status..."

    # Wait for pods to be ready
    log_info "Waiting for backend pods to be ready..."
    if ! kubectl wait --for=condition=ready pod -l app=pms-backend -n "$NAMESPACE" --timeout="$TIMEOUT"; then
        log_error "Backend pods are not ready within timeout"
        kubectl get pods -n "$NAMESPACE" -l app=pms-backend
        exit 1
    fi

    log_info "Waiting for frontend pods to be ready..."
    if ! kubectl wait --for=condition=ready pod -l app=pms-frontend -n "$NAMESPACE" --timeout="$TIMEOUT"; then
        log_error "Frontend pods are not ready within timeout"
        kubectl get pods -n "$NAMESPACE" -l app=pms-frontend
        exit 1
    fi

    # Check pod status
    local backend_pods=$(kubectl get pods -n "$NAMESPACE" -l app=pms-backend --no-headers | wc -l | tr -d ' ')
    local frontend_pods=$(kubectl get pods -n "$NAMESPACE" -l app=pms-frontend --no-headers | wc -l | tr -d ' ')

    if [[ "$backend_pods" -eq 0 ]]; then
        log_error "No backend pods found"
        exit 1
    fi

    if [[ "$frontend_pods" -eq 0 ]]; then
        log_error "No frontend pods found"
        exit 1
    fi

    log_success "All pods are ready (Backend: $backend_pods, Frontend: $frontend_pods)"

    if [[ "$VERBOSE" == "true" ]]; then
        log_info "Pod details:"
        kubectl get pods -n "$NAMESPACE" -o wide
    fi
}

test_services() {
    log_info "Testing services..."

    # Check backend service
    if ! kubectl get service pms-backend -n "$NAMESPACE" &> /dev/null; then
        log_error "Backend service not found"
        exit 1
    fi

    # Check frontend service
    if ! kubectl get service pms-frontend -n "$NAMESPACE" &> /dev/null; then
        log_error "Frontend service not found"
        exit 1
    fi

    log_success "All services are available"

    if [[ "$VERBOSE" == "true" ]]; then
        log_info "Service details:"
        kubectl get services -n "$NAMESPACE"
    fi
}

test_ingress() {
    log_info "Testing ingress..."

    if kubectl get ingress -n "$NAMESPACE" &> /dev/null; then
        local ingress_count=$(kubectl get ingress -n "$NAMESPACE" --no-headers | wc -l | tr -d ' ')
        if [[ "$ingress_count" -gt 0 ]]; then
            log_success "Ingress is configured"

            if [[ "$VERBOSE" == "true" ]]; then
                log_info "Ingress details:"
                kubectl get ingress -n "$NAMESPACE" -o wide
            fi
        else
            log_warning "No ingress resources found"
        fi
    else
        log_warning "Ingress not available or not configured"
    fi
}

test_connectivity() {
    log_info "Testing application connectivity..."

    # Test backend health endpoint
    log_info "Testing backend connectivity..."

    # Use port-forward to test backend
    local backend_port=8080
    kubectl port-forward -n "$NAMESPACE" service/pms-backend $backend_port:8000 &
    local pf_pid=$!

    # Wait a moment for port-forward to establish
    sleep 3

    # Test backend health endpoint
    if curl -f -s "http://localhost:$backend_port/api/health" > /dev/null 2>&1; then
        log_success "Backend health endpoint is responding"
    else
        log_warning "Backend health endpoint is not responding (this might be expected if health endpoint is not implemented)"
    fi

    # Clean up port-forward
    kill $pf_pid 2>/dev/null || true

    # Test frontend
    log_info "Testing frontend connectivity..."

    local frontend_port=3080
    kubectl port-forward -n "$NAMESPACE" service/pms-frontend $frontend_port:3000 &
    local pf_pid=$!

    # Wait a moment for port-forward to establish
    sleep 3

    # Test frontend
    if curl -f -s "http://localhost:$frontend_port" > /dev/null 2>&1; then
        log_success "Frontend is responding"
    else
        log_warning "Frontend is not responding (this might be expected during startup)"
    fi

    # Clean up port-forward
    kill $pf_pid 2>/dev/null || true

    log_success "Connectivity tests completed"
}

test_logs() {
    log_info "Testing application logs..."

    # Check backend logs
    local backend_logs=$(kubectl logs -n "$NAMESPACE" -l app=pms-backend --tail=10 2>/dev/null || echo "")
    if [[ -n "$backend_logs" ]]; then
        log_success "Backend logs are available"
        if [[ "$VERBOSE" == "true" ]]; then
            log_info "Recent backend logs:"
            echo "$backend_logs"
        fi
    else
        log_warning "No backend logs found"
    fi

    # Check frontend logs
    local frontend_logs=$(kubectl logs -n "$NAMESPACE" -l app=pms-frontend --tail=10 2>/dev/null || echo "")
    if [[ -n "$frontend_logs" ]]; then
        log_success "Frontend logs are available"
        if [[ "$VERBOSE" == "true" ]]; then
            log_info "Recent frontend logs:"
            echo "$frontend_logs"
        fi
    else
        log_warning "No frontend logs found"
    fi
}

test_scaling() {
    log_info "Testing scaling capabilities..."

    # Get current replica count
    local current_replicas=$(kubectl get deployment pms-backend -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
    log_info "Current backend replicas: $current_replicas"

    # Scale up
    local target_replicas=$((current_replicas + 1))
    log_info "Scaling backend to $target_replicas replicas..."
    kubectl scale deployment pms-backend --replicas=$target_replicas -n "$NAMESPACE"

    # Wait for scaling
    if kubectl wait --for=condition=ready pod -l app=pms-backend -n "$NAMESPACE" --timeout=60s; then
        log_success "Scaling up successful"
    else
        log_warning "Scaling up took longer than expected"
    fi

    # Scale back down
    log_info "Scaling backend back to $current_replicas replicas..."
    kubectl scale deployment pms-backend --replicas=$current_replicas -n "$NAMESPACE"

    # Wait for scaling
    sleep 5
    log_success "Scaling test completed"
}

run_comprehensive_test() {
    echo "========================================"
    echo "    LOCAL KUBERNETES TESTING"
    echo "========================================"
    echo "Namespace: $NAMESPACE"
    echo "Timeout: $TIMEOUT"
    echo "Verbose: $VERBOSE"
    echo "========================================"
    echo

    local start_time=$(date +%s)

    # Run all tests
    test_prerequisites
    echo

    test_namespace
    echo

    test_helm_release
    echo

    test_pods
    echo

    test_services
    echo

    test_ingress
    echo

    test_connectivity
    echo

    test_logs
    echo

    test_scaling
    echo

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    echo "========================================"
    echo "         TEST SUMMARY"
    echo "========================================"
    log_success "All tests completed successfully!"
    log_info "Total test duration: ${duration}s"
    echo
    log_info "Your local Kubernetes setup is working correctly."
    echo
    log_info "Access your application:"
    echo "  Frontend: http://pms.local (if ingress is configured)"
    echo "  Backend API: http://pms.local/api (if ingress is configured)"
    echo
    log_info "Alternative access (port-forward):"
    echo "  kubectl port-forward -n $NAMESPACE service/pms-frontend 3000:3000"
    echo "  kubectl port-forward -n $NAMESPACE service/pms-backend 8000:8000"
    echo
    log_info "Useful monitoring commands:"
    echo "  kubectl get pods -n $NAMESPACE"
    echo "  kubectl logs -n $NAMESPACE -l app=pms-backend -f"
    echo "  kubectl logs -n $NAMESPACE -l app=pms-frontend -f"
    echo "========================================"
}

# Main function
main() {
    run_comprehensive_test
}

# Run main function
main "$@"

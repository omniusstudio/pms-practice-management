#!/bin/bash

# Kubernetes Rollback Script for Mental Health PMS
# Usage: ./rollback-k8s.sh <environment> [revision]

set -euo pipefail

ENVIRONMENT=${1:-staging}
REVISION=${2:-}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Configuration
NAMESPACE="pms"
HEALTH_CHECK_TIMEOUT=300
HEALTH_CHECK_INTERVAL=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} ✅ $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} ⚠️  $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} ❌ $1"
}

# Validate inputs
if [[ -z "$ENVIRONMENT" ]]; then
    log_error "Usage: $0 <environment> [revision]"
    exit 1
fi

if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    log_error "Environment must be development, staging, or production"
    exit 1
fi

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi

    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    # Check namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace ${NAMESPACE} does not exist"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Show rollout history
show_history() {
    log "Showing rollout history..."
    echo
    echo "Backend deployment history:"
    kubectl rollout history deployment/pms-backend -n ${NAMESPACE}
    echo
    echo "Frontend deployment history:"
    kubectl rollout history deployment/pms-frontend -n ${NAMESPACE}
    echo
}

# Confirm rollback
confirm_rollback() {
    if [[ -n "$REVISION" ]]; then
        log_warning "Rolling back to revision ${REVISION}"
    else
        log_warning "Rolling back to previous revision"
    fi

    read -p "Are you sure you want to proceed with the rollback? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Rollback cancelled"
        exit 0
    fi
}

# Perform rollback
perform_rollback() {
    log "Performing rollback..."

    local deployments=("pms-backend" "pms-frontend")

    for deployment in "${deployments[@]}"; do
        log "Rolling back deployment ${deployment}..."

        if [[ -n "$REVISION" ]]; then
            kubectl rollout undo deployment/${deployment} --to-revision=${REVISION} -n ${NAMESPACE}
        else
            kubectl rollout undo deployment/${deployment} -n ${NAMESPACE}
        fi

        log_success "Initiated rollback for ${deployment}"
    done
}

# Wait for rollback to complete
wait_for_rollback() {
    log "Waiting for rollback to complete..."

    local deployments=("pms-backend" "pms-frontend")

    for deployment in "${deployments[@]}"; do
        log "Waiting for deployment ${deployment} rollback..."

        if kubectl rollout status deployment/${deployment} -n ${NAMESPACE} --timeout=600s; then
            log_success "Rollback completed for ${deployment}"
        else
            log_error "Rollback failed for ${deployment}"
            kubectl describe deployment ${deployment} -n ${NAMESPACE}
            kubectl logs -l app=${deployment} -n ${NAMESPACE} --tail=50
            exit 1
        fi
    done
}

# Health check after rollback
health_check() {
    log "Performing health checks after rollback..."

    # Wait a bit for pods to be ready
    sleep 30

    # Check backend health
    local backend_pod=$(kubectl get pods -l app=pms-backend -n ${NAMESPACE} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    if [[ -n "$backend_pod" ]]; then
        if kubectl exec ${backend_pod} -n ${NAMESPACE} -- curl -f http://localhost:8000/health &> /dev/null; then
            log_success "Backend health check passed"
        else
            log_warning "Backend health check failed, but rollback completed"
        fi
    else
        log_warning "No backend pods found for health check"
    fi

    # Check frontend health
    local frontend_pod=$(kubectl get pods -l app=pms-frontend -n ${NAMESPACE} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    if [[ -n "$frontend_pod" ]]; then
        if kubectl exec ${frontend_pod} -n ${NAMESPACE} -- curl -f http://localhost:80/ &> /dev/null; then
            log_success "Frontend health check passed"
        else
            log_warning "Frontend health check failed, but rollback completed"
        fi
    else
        log_warning "No frontend pods found for health check"
    fi
}

# Show status after rollback
show_status() {
    log "Post-rollback Status:"
    echo
    kubectl get pods -n ${NAMESPACE}
    echo
    kubectl get deployments -n ${NAMESPACE}
    echo
    log_success "Rollback completed!"
}

# Create rollback report
create_report() {
    local report_file="rollback_report_$(date +%Y%m%d_%H%M%S).txt"

    {
        echo "Kubernetes Rollback Report"
        echo "========================="
        echo "Environment: ${ENVIRONMENT}"
        echo "Namespace: ${NAMESPACE}"
        echo "Timestamp: $(date)"
        echo "Revision: ${REVISION:-previous}"
        echo
        echo "Deployment Status:"
        kubectl get deployments -n ${NAMESPACE}
        echo
        echo "Pod Status:"
        kubectl get pods -n ${NAMESPACE}
        echo
        echo "Recent Events:"
        kubectl get events -n ${NAMESPACE} --sort-by='.lastTimestamp' | tail -20
    } > "$report_file"

    log_success "Rollback report saved to ${report_file}"
}

# Main execution
main() {
    log "Starting Kubernetes rollback for ${ENVIRONMENT} environment"

    check_prerequisites
    show_history
    confirm_rollback
    perform_rollback
    wait_for_rollback
    health_check
    show_status
    create_report

    log_success "Rollback completed successfully!"
}

# Execute main function
main "$@"

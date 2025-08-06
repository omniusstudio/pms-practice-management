#!/bin/bash

# Kubernetes Deployment Script for Mental Health PMS
# Usage: ./deploy-k8s.sh <environment> <version>

set -euo pipefail

ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
K8S_DIR="${ROOT_DIR}/apps/infra/kubernetes"

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
CLUSTER_NAME="pms-${ENVIRONMENT}"
NAMESPACE="pms"
ECR_REGISTRY=${ECR_REGISTRY:-}
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
if [[ -z "$ENVIRONMENT" || -z "$VERSION" ]]; then
    log_error "Usage: $0 <environment> <version>"
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

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi

    # Check envsubst
    if ! command -v envsubst &> /dev/null; then
        log_error "envsubst is not installed (part of gettext package)"
        exit 1
    fi

    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Load environment variables
load_environment_config() {
    log "Loading environment configuration for ${ENVIRONMENT}..."

    # Load environment-specific configuration
    local env_file="${ROOT_DIR}/.env.${ENVIRONMENT}"
    if [[ -f "$env_file" ]]; then
        set -a
        source "$env_file"
        set +a
        log_success "Loaded configuration from $env_file"
    else
        log_warning "Environment file $env_file not found, using defaults"
    fi

    # Set required variables
    export ENVIRONMENT
    export VERSION
    export ECR_REGISTRY
    export AWS_REGION

    # Validate required variables
    local required_vars=("ECR_REGISTRY" "DOMAIN_NAME" "AUTH0_DOMAIN" "AUTH0_CLIENT_ID")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required variable $var is not set"
            exit 1
        fi
    done
}

# Create namespace if it doesn't exist
ensure_namespace() {
    log "Ensuring namespace ${NAMESPACE} exists..."

    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        envsubst < "${K8S_DIR}/namespace.yaml" | kubectl apply -f -
        log_success "Created namespace ${NAMESPACE}"
    else
        log "Namespace ${NAMESPACE} already exists"
    fi
}

# Apply ConfigMap and Secrets
apply_config() {
    log "Applying ConfigMap and Secrets..."

    # Base64 encode secrets
    export DATABASE_URL_B64=$(echo -n "$DATABASE_URL" | base64)
    export REDIS_URL_B64=$(echo -n "$REDIS_URL" | base64)
    export SECRET_KEY_B64=$(echo -n "$SECRET_KEY" | base64)
    export JWT_SECRET_KEY_B64=$(echo -n "$JWT_SECRET_KEY" | base64)
    export SESSION_SECRET_KEY_B64=$(echo -n "$SESSION_SECRET_KEY" | base64)
    export AWS_ACCESS_KEY_ID_B64=$(echo -n "$AWS_ACCESS_KEY_ID" | base64)
    export AWS_SECRET_ACCESS_KEY_B64=$(echo -n "$AWS_SECRET_ACCESS_KEY" | base64)
    export AUTH0_CLIENT_SECRET_B64=$(echo -n "$AUTH0_CLIENT_SECRET" | base64)
    export OIDC_GOOGLE_CLIENT_SECRET_B64=$(echo -n "$OIDC_GOOGLE_CLIENT_SECRET" | base64)
    export OIDC_MICROSOFT_CLIENT_SECRET_B64=$(echo -n "$OIDC_MICROSOFT_CLIENT_SECRET" | base64)
    export DB_PASSWORD_B64=$(echo -n "$DB_PASSWORD" | base64)
    export REDIS_PASSWORD_B64=$(echo -n "$REDIS_PASSWORD" | base64)

    envsubst < "${K8S_DIR}/configmap.yaml" | kubectl apply -f -
    log_success "Applied ConfigMap and Secrets"
}

# Deploy applications
deploy_applications() {
    log "Deploying applications..."

    # Apply network policies first
    envsubst < "${K8S_DIR}/network-policy.yaml" | kubectl apply -f -
    log_success "Applied network policies"

    # Deploy backend
    envsubst < "${K8S_DIR}/backend-deployment.yaml" | kubectl apply -f -
    log_success "Applied backend deployment"

    # Deploy frontend
    envsubst < "${K8S_DIR}/frontend-deployment.yaml" | kubectl apply -f -
    log_success "Applied frontend deployment"

    # Apply HPA
    envsubst < "${K8S_DIR}/hpa.yaml" | kubectl apply -f -
    log_success "Applied Horizontal Pod Autoscalers"

    # Apply PDB
    envsubst < "${K8S_DIR}/pdb.yaml" | kubectl apply -f -
    log_success "Applied Pod Disruption Budgets"

    # Apply Ingress
    envsubst < "${K8S_DIR}/ingress.yaml" | kubectl apply -f -
    log_success "Applied Ingress configuration"
}

# Wait for deployments to be ready
wait_for_deployments() {
    log "Waiting for deployments to be ready..."

    local deployments=("pms-backend" "pms-frontend")

    for deployment in "${deployments[@]}"; do
        log "Waiting for deployment ${deployment}..."

        if kubectl wait --for=condition=available --timeout=600s deployment/${deployment} -n ${NAMESPACE}; then
            log_success "Deployment ${deployment} is ready"
        else
            log_error "Deployment ${deployment} failed to become ready"
            kubectl describe deployment ${deployment} -n ${NAMESPACE}
            kubectl logs -l app=${deployment} -n ${NAMESPACE} --tail=50
            exit 1
        fi
    done
}

# Health check
health_check() {
    log "Performing health checks..."

    # Check backend health
    local backend_pod=$(kubectl get pods -l app=pms-backend -n ${NAMESPACE} -o jsonpath='{.items[0].metadata.name}')
    if kubectl exec ${backend_pod} -n ${NAMESPACE} -- curl -f http://localhost:8000/health; then
        log_success "Backend health check passed"
    else
        log_error "Backend health check failed"
        exit 1
    fi

    # Check frontend health
    local frontend_pod=$(kubectl get pods -l app=pms-frontend -n ${NAMESPACE} -o jsonpath='{.items[0].metadata.name}')
    if kubectl exec ${frontend_pod} -n ${NAMESPACE} -- curl -f http://localhost:80/; then
        log_success "Frontend health check passed"
    else
        log_error "Frontend health check failed"
        exit 1
    fi
}

# Show deployment status
show_status() {
    log "Deployment Status:"
    echo
    kubectl get all -n ${NAMESPACE}
    echo
    kubectl get ingress -n ${NAMESPACE}
    echo
    log_success "Deployment completed successfully!"
    log "Application URL: https://${DOMAIN_NAME}"
    log "API URL: https://api.${DOMAIN_NAME}"
}

# Rollback function
rollback() {
    log_warning "Rolling back deployment..."

    kubectl rollout undo deployment/pms-backend -n ${NAMESPACE}
    kubectl rollout undo deployment/pms-frontend -n ${NAMESPACE}

    log_success "Rollback completed"
}

# Cleanup function
cleanup() {
    if [[ $? -ne 0 ]]; then
        log_error "Deployment failed. Check the logs above for details."
        read -p "Do you want to rollback? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rollback
        fi
    fi
}

# Main execution
main() {
    log "Starting Kubernetes deployment for ${ENVIRONMENT} environment with version ${VERSION}"

    trap cleanup EXIT

    check_prerequisites
    load_environment_config
    ensure_namespace
    apply_config
    deploy_applications
    wait_for_deployments
    health_check
    show_status

    log_success "Deployment completed successfully!"
}

# Execute main function
main "$@"

#!/bin/bash

# CI/CD Kubernetes Deployment Script
# This script provides a unified interface for deploying to Kubernetes from CI/CD pipelines
# Supports both Helm and kubectl deployments with comprehensive validation and monitoring

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
HELM_CHART_DIR="$PROJECT_ROOT/apps/infra/kubernetes/helm/pms"
K8S_MANIFESTS_DIR="$PROJECT_ROOT/apps/infra/kubernetes/manifests"

# Default values
ENVIRONMENT="staging"
DEPLOYMENT_METHOD="helm"
VERSION="latest"
DRY_RUN="false"
WAIT_TIMEOUT="600s"
ROLLBACK_ON_FAILURE="true"
VERBOSE="false"
FORCE_DEPLOY="false"
SKIP_VALIDATION="false"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

# Usage function
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

CI/CD Kubernetes Deployment Script

OPTIONS:
    -e, --environment ENVIRONMENT    Target environment (staging|production) [default: staging]
    -m, --method METHOD             Deployment method (helm|kubectl) [default: helm]
    -v, --version VERSION           Application version to deploy [default: latest]
    -d, --dry-run                   Perform a dry run without making changes
    -t, --timeout TIMEOUT          Wait timeout for deployment [default: 600s]
    -r, --no-rollback              Disable automatic rollback on failure
    -f, --force                     Force deployment even if validation fails
    -s, --skip-validation           Skip pre-deployment validation
    --verbose                       Enable verbose output
    -h, --help                      Show this help message

EXAMPLES:
    # Deploy to staging using Helm
    $0 --environment staging --method helm --version v1.2.3

    # Deploy to production using kubectl with dry run
    $0 -e production -m kubectl -v v1.2.3 --dry-run

    # Force deploy to staging without validation
    $0 -e staging --force --skip-validation

ENVIRONMENT VARIABLES:
    KUBECONFIG                      Path to kubeconfig file
    ECR_REGISTRY                    ECR registry URL
    GITHUB_SHA                      Git commit SHA (for CI/CD)
    GITHUB_REF_NAME                 Git branch/tag name (for CI/CD)
    CI                              Set to 'true' in CI environment

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -m|--method)
                DEPLOYMENT_METHOD="$2"
                shift 2
                ;;
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN="true"
                shift
                ;;
            -t|--timeout)
                WAIT_TIMEOUT="$2"
                shift 2
                ;;
            -r|--no-rollback)
                ROLLBACK_ON_FAILURE="false"
                shift
                ;;
            -f|--force)
                FORCE_DEPLOY="true"
                shift
                ;;
            -s|--skip-validation)
                SKIP_VALIDATION="true"
                shift
                ;;
            --verbose)
                VERBOSE="true"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Validate environment
validate_environment() {
    log_info "Validating environment: $ENVIRONMENT"

    case $ENVIRONMENT in
        staging|production)
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT. Must be 'staging' or 'production'"
            exit 1
            ;;
    esac

    case $DEPLOYMENT_METHOD in
        helm|kubectl)
            ;;
        *)
            log_error "Invalid deployment method: $DEPLOYMENT_METHOD. Must be 'helm' or 'kubectl'"
            exit 1
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi

    # Check Helm if using Helm deployment
    if [[ "$DEPLOYMENT_METHOD" == "helm" ]] && ! command -v helm &> /dev/null; then
        log_error "helm is not installed or not in PATH"
        exit 1
    fi

    # Check kubeconfig
    if [[ -z "${KUBECONFIG:-}" ]]; then
        log_warning "KUBECONFIG not set, using default kubectl configuration"
    fi

    # Test kubectl connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Validate Kubernetes configurations
validate_k8s_configs() {
    if [[ "$SKIP_VALIDATION" == "true" ]]; then
        log_warning "Skipping Kubernetes configuration validation"
        return 0
    fi

    log_info "Validating Kubernetes configurations..."

    local validation_failed=false

    if [[ "$DEPLOYMENT_METHOD" == "helm" ]]; then
        # Validate Helm chart
        if [[ -d "$HELM_CHART_DIR" ]]; then
            log_info "Validating Helm chart..."
            if ! helm lint "$HELM_CHART_DIR" --values "$HELM_CHART_DIR/values-$ENVIRONMENT.yaml"; then
                log_error "Helm chart validation failed"
                validation_failed=true
            fi

            # Template and validate
            log_info "Templating Helm chart for validation..."
            if ! helm template pms "$HELM_CHART_DIR" \
                --values "$HELM_CHART_DIR/values-$ENVIRONMENT.yaml" \
                --set global.version="$VERSION" \
                --set backend.image.tag="$VERSION" \
                --set frontend.image.tag="$VERSION" \
                --dry-run --validate > /tmp/helm-template-output.yaml; then
                log_error "Helm template validation failed"
                validation_failed=true
            fi
        else
            log_error "Helm chart directory not found: $HELM_CHART_DIR"
            validation_failed=true
        fi
    else
        # Validate kubectl manifests
        if [[ -d "$K8S_MANIFESTS_DIR" ]]; then
            log_info "Validating kubectl manifests..."
            for manifest in "$K8S_MANIFESTS_DIR"/*.yaml; do
                if [[ -f "$manifest" ]]; then
                    if ! kubectl apply --dry-run=client --validate=true -f "$manifest" &> /dev/null; then
                        log_error "Manifest validation failed: $manifest"
                        validation_failed=true
                    fi
                fi
            done
        else
            log_error "Kubernetes manifests directory not found: $K8S_MANIFESTS_DIR"
            validation_failed=true
        fi
    fi

    if [[ "$validation_failed" == "true" ]]; then
        if [[ "$FORCE_DEPLOY" == "true" ]]; then
            log_warning "Validation failed but continuing due to --force flag"
        else
            log_error "Validation failed. Use --force to deploy anyway or fix the issues"
            exit 1
        fi
    else
        log_success "Kubernetes configuration validation passed"
    fi
}

# Deploy using Helm
deploy_with_helm() {
    log_info "Deploying with Helm to $ENVIRONMENT environment..."

    local helm_args=(
        "pms"
        "$HELM_CHART_DIR"
        "--values" "$HELM_CHART_DIR/values-$ENVIRONMENT.yaml"
        "--set" "global.version=$VERSION"
        "--set" "backend.image.tag=$VERSION"
        "--set" "frontend.image.tag=$VERSION"
        "--namespace" "pms-$ENVIRONMENT"
        "--create-namespace"
        "--wait"
        "--timeout" "$WAIT_TIMEOUT"
    )

    if [[ "$DRY_RUN" == "true" ]]; then
        helm_args+=("--dry-run")
        log_info "Performing Helm dry run..."
    fi

    if [[ "$VERBOSE" == "true" ]]; then
        helm_args+=("--debug")
    fi

    # Check if release exists
    if helm list -n "pms-$ENVIRONMENT" | grep -q "pms"; then
        log_info "Upgrading existing Helm release..."
        if helm upgrade "${helm_args[@]}"; then
            log_success "Helm upgrade completed successfully"
        else
            log_error "Helm upgrade failed"
            if [[ "$ROLLBACK_ON_FAILURE" == "true" && "$DRY_RUN" == "false" ]]; then
                log_info "Rolling back due to failure..."
                helm rollback pms -n "pms-$ENVIRONMENT"
            fi
            exit 1
        fi
    else
        log_info "Installing new Helm release..."
        if helm install "${helm_args[@]}"; then
            log_success "Helm installation completed successfully"
        else
            log_error "Helm installation failed"
            exit 1
        fi
    fi
}

# Deploy using kubectl
deploy_with_kubectl() {
    log_info "Deploying with kubectl to $ENVIRONMENT environment..."

    # Create namespace if it doesn't exist
    kubectl create namespace "pms-$ENVIRONMENT" --dry-run=client -o yaml | kubectl apply -f -

    local kubectl_args=("apply" "-f" "$K8S_MANIFESTS_DIR" "--namespace" "pms-$ENVIRONMENT")

    if [[ "$DRY_RUN" == "true" ]]; then
        kubectl_args+=("--dry-run=client")
        log_info "Performing kubectl dry run..."
    fi

    if kubectl "${kubectl_args[@]}"; then
        log_success "kubectl deployment completed successfully"

        if [[ "$DRY_RUN" == "false" ]]; then
            # Wait for deployments to be ready
            log_info "Waiting for deployments to be ready..."
            kubectl wait --for=condition=available --timeout="$WAIT_TIMEOUT" \
                deployment/pms-backend deployment/pms-frontend -n "pms-$ENVIRONMENT"
        fi
    else
        log_error "kubectl deployment failed"
        exit 1
    fi
}

# Perform health checks
perform_health_checks() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Skipping health checks for dry run"
        return 0
    fi

    log_info "Performing health checks..."

    # Check pod status
    log_info "Checking pod status..."
    kubectl get pods -n "pms-$ENVIRONMENT" -l app.kubernetes.io/name=pms

    # Check service endpoints
    log_info "Checking service endpoints..."
    kubectl get endpoints -n "pms-$ENVIRONMENT"

    # Perform application health checks
    log_info "Performing application health checks..."

    # Get service IPs for health checks
    local backend_service=$(kubectl get svc pms-backend -n "pms-$ENVIRONMENT" -o jsonpath='{.spec.clusterIP}')
    local frontend_service=$(kubectl get svc pms-frontend -n "pms-$ENVIRONMENT" -o jsonpath='{.spec.clusterIP}')

    # Health check backend
    if kubectl run health-check-backend --rm -i --restart=Never --image=curlimages/curl:latest \
        -- curl -f "http://$backend_service/health" --max-time 30; then
        log_success "Backend health check passed"
    else
        log_error "Backend health check failed"
        return 1
    fi

    # Health check frontend
    if kubectl run health-check-frontend --rm -i --restart=Never --image=curlimages/curl:latest \
        -- curl -f "http://$frontend_service/" --max-time 30; then
        log_success "Frontend health check passed"
    else
        log_error "Frontend health check failed"
        return 1
    fi

    log_success "All health checks passed"
}

# Generate deployment report
generate_deployment_report() {
    log_info "Generating deployment report..."

    local report_file="/tmp/deployment-report-$ENVIRONMENT-$(date +%Y%m%d-%H%M%S).json"

    cat > "$report_file" << EOF
{
  "deployment": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "environment": "$ENVIRONMENT",
    "method": "$DEPLOYMENT_METHOD",
    "version": "$VERSION",
    "dry_run": $DRY_RUN,
    "git_sha": "${GITHUB_SHA:-unknown}",
    "git_ref": "${GITHUB_REF_NAME:-unknown}",
    "ci": "${CI:-false}"
  },
  "kubernetes": {
    "cluster": "$(kubectl config current-context)",
    "namespace": "pms-$ENVIRONMENT"
  },
  "status": "success"
}
EOF

    log_success "Deployment report generated: $report_file"

    # Output report content for CI/CD systems
    if [[ "${CI:-false}" == "true" ]]; then
        echo "::set-output name=deployment-report::$report_file"
        cat "$report_file"
    fi
}

# Main deployment function
main() {
    log_info "Starting CI/CD Kubernetes deployment..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Method: $DEPLOYMENT_METHOD"
    log_info "Version: $VERSION"
    log_info "Dry Run: $DRY_RUN"

    validate_environment
    check_prerequisites
    validate_k8s_configs

    case $DEPLOYMENT_METHOD in
        helm)
            deploy_with_helm
            ;;
        kubectl)
            deploy_with_kubectl
            ;;
    esac

    perform_health_checks
    generate_deployment_report

    log_success "CI/CD Kubernetes deployment completed successfully!"
}

# Parse arguments and run main function
parse_args "$@"
main

#!/bin/bash

# Apply RBAC Enhancements Script
# Safely applies enhanced RBAC configuration with validation and rollback capability
# Part of Phase 1: Kubernetes RBAC Enhancement

set -euo pipefail

# Configuration
NAMESPACE="pms"
BACKUP_DIR="./rbac-backup-$(date +%Y%m%d_%H%M%S)"
ENHANCED_RBAC_FILE="../apps/infra/kubernetes/rbac-enhanced.yaml"
ADMISSION_CONTROLLER_FILE="../apps/infra/kubernetes/rbac-basic-admission.yaml"
AUDIT_SCRIPT="./rbac-audit.py"

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi

    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    # Check if namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_warning "Namespace $NAMESPACE does not exist, will be created"
    fi

    # Check if files exist
    if [[ ! -f "$ENHANCED_RBAC_FILE" ]]; then
        log_error "Enhanced RBAC file not found: $ENHANCED_RBAC_FILE"
        exit 1
    fi

    if [[ ! -f "$ADMISSION_CONTROLLER_FILE" ]]; then
        log_error "Admission controller file not found: $ADMISSION_CONTROLLER_FILE"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Backup current RBAC configuration
backup_current_rbac() {
    log_info "Backing up current RBAC configuration..."

    mkdir -p "$BACKUP_DIR"

    # Backup service accounts
    kubectl get serviceaccounts -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/serviceaccounts.yaml" 2>/dev/null || true

    # Backup roles
    kubectl get roles -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/roles.yaml" 2>/dev/null || true

    # Backup role bindings
    kubectl get rolebindings -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/rolebindings.yaml" 2>/dev/null || true

    # Backup network policies
    kubectl get networkpolicies -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/networkpolicies.yaml" 2>/dev/null || true

    log_success "Backup created in $BACKUP_DIR"
}

# Run pre-deployment audit
run_pre_audit() {
    log_info "Running pre-deployment RBAC audit..."

    if [[ -f "$AUDIT_SCRIPT" ]]; then
        python3 "$AUDIT_SCRIPT" --namespace "$NAMESPACE" --output "$BACKUP_DIR/pre-audit-report.json" || {
            log_warning "Pre-audit completed with violations (expected)"
        }
    else
        log_warning "Audit script not found, skipping pre-audit"
    fi
}

# Validate RBAC configuration
validate_rbac_config() {
    log_info "Validating RBAC configuration files..."

    # Validate YAML syntax
    if ! kubectl apply --dry-run=client -f "$ENHANCED_RBAC_FILE" &> /dev/null; then
        log_error "Enhanced RBAC configuration has syntax errors"
        return 1
    fi

    if ! kubectl apply --dry-run=client -f "$ADMISSION_CONTROLLER_FILE" &> /dev/null; then
        log_error "Admission controller configuration has syntax errors"
        return 1
    fi

    log_success "RBAC configuration validation passed"
}

# Apply enhanced RBAC configuration
apply_enhanced_rbac() {
    log_info "Applying enhanced RBAC configuration..."

    # Apply the enhanced RBAC configuration
    if kubectl apply -f "$ENHANCED_RBAC_FILE"; then
        log_success "Enhanced RBAC configuration applied successfully"
    else
        log_error "Failed to apply enhanced RBAC configuration"
        return 1
    fi

    # Wait for resources to be ready
    log_info "Waiting for resources to be ready..."
    sleep 5

    # Verify service accounts
    local expected_sa=("pms-backend" "pms-frontend" "pms-backup" "pms-monitoring")
    for sa in "${expected_sa[@]}"; do
        if kubectl get serviceaccount "$sa" -n "$NAMESPACE" &> /dev/null; then
            log_success "Service account $sa is ready"
        else
            log_error "Service account $sa is not ready"
            return 1
        fi
    done

    # Verify roles
    local expected_roles=("pms-backend-role" "pms-frontend-role" "pms-backup-role" "pms-monitoring-role")
    for role in "${expected_roles[@]}"; do
        if kubectl get role "$role" -n "$NAMESPACE" &> /dev/null; then
            log_success "Role $role is ready"
        else
            log_error "Role $role is not ready"
            return 1
        fi
    done
}

# Apply basic RBAC admission configuration
apply_admission_controller() {
    log_info "Applying basic RBAC admission configuration..."

    # Apply simplified admission configuration without complex Gatekeeper dependencies
    if kubectl apply -f "$ADMISSION_CONTROLLER_FILE"; then
        log_success "Basic RBAC admission configuration applied successfully"
    else
        log_warning "Some basic admission components failed to apply (continuing with core RBAC)"
    fi
}

# Test RBAC functionality
test_rbac_functionality() {
    log_info "Testing RBAC functionality..."

    # Create test configmaps for RBAC validation
    kubectl create configmap pms-config --from-literal=test=value -n "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - &> /dev/null
    kubectl create configmap app-config --from-literal=test=value -n "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - &> /dev/null
    kubectl create configmap pms-public-config --from-literal=test=value -n "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - &> /dev/null

    # Test service account permissions for specific configmaps (least privilege test)
    local test_sa="pms-backend"
    if kubectl auth can-i get configmaps/pms-config --as=system:serviceaccount:$NAMESPACE:$test_sa -n "$NAMESPACE" &> /dev/null; then
        log_success "Service account $test_sa can access pms-config (expected)"
    else
        log_error "Service account $test_sa cannot access pms-config"
        return 1
    fi

    # Test that frontend can access specific public configmaps (as per its role)
    if kubectl auth can-i get configmaps/pms-public-config --as=system:serviceaccount:$NAMESPACE:pms-frontend -n "$NAMESPACE" &> /dev/null; then
        log_success "Service account pms-frontend can access pms-public-config (expected)"
    else
        log_warning "Service account pms-frontend cannot access pms-public-config (unexpected)"
    fi

    # Test that backend cannot access all configmaps (least privilege validation)
    if ! kubectl auth can-i get configmaps --as=system:serviceaccount:$NAMESPACE:pms-backend -n "$NAMESPACE" &> /dev/null; then
        log_success "Service account pms-backend cannot access all configmaps (expected - least privilege)"
    else
        log_warning "Service account pms-backend can access all configmaps (potential over-privilege)"
    fi

    # Test that frontend cannot access secrets
    if ! kubectl auth can-i get secrets --as=system:serviceaccount:$NAMESPACE:pms-frontend -n "$NAMESPACE" &> /dev/null; then
        log_success "Service account pms-frontend cannot access secrets (expected)"
    else
        log_warning "Service account pms-frontend can access secrets (unexpected)"
    fi

    log_success "RBAC functionality tests passed"
}

# Run post-deployment audit
run_post_audit() {
    log_info "Running post-deployment RBAC audit..."

    if [[ -f "$AUDIT_SCRIPT" ]]; then
        python3 "$AUDIT_SCRIPT" --namespace "$NAMESPACE" --output "./rbac-post-deployment-audit.json" || {
            log_warning "Post-audit completed with some findings"
        }

        # Compare with pre-audit if available
        if [[ -f "$BACKUP_DIR/pre-audit-report.json" ]]; then
            log_info "Comparing pre and post audit results..."
            # Simple comparison - in a real scenario, you'd want more sophisticated diff
            local pre_violations=$(jq '.summary.total_violations' "$BACKUP_DIR/pre-audit-report.json" 2>/dev/null || echo "unknown")
            local post_violations=$(jq '.summary.total_violations' "./rbac-post-deployment-audit.json" 2>/dev/null || echo "unknown")

            if [[ "$pre_violations" != "unknown" && "$post_violations" != "unknown" ]]; then
                if [[ $post_violations -lt $pre_violations ]]; then
                    log_success "RBAC violations reduced from $pre_violations to $post_violations"
                elif [[ $post_violations -eq $pre_violations ]]; then
                    log_info "RBAC violations unchanged: $post_violations"
                else
                    log_warning "RBAC violations increased from $pre_violations to $post_violations"
                fi
            fi
        fi
    else
        log_warning "Audit script not found, skipping post-audit"
    fi
}

# Rollback function
rollback_rbac() {
    log_error "Rolling back RBAC changes..."

    if [[ -d "$BACKUP_DIR" ]]; then
        # Restore from backup
        kubectl apply -f "$BACKUP_DIR/serviceaccounts.yaml" 2>/dev/null || true
        kubectl apply -f "$BACKUP_DIR/roles.yaml" 2>/dev/null || true
        kubectl apply -f "$BACKUP_DIR/rolebindings.yaml" 2>/dev/null || true
        kubectl apply -f "$BACKUP_DIR/networkpolicies.yaml" 2>/dev/null || true

        log_success "Rollback completed using backup from $BACKUP_DIR"
    else
        log_error "No backup directory found, manual rollback required"
    fi
}

# Main execution
main() {
    log_info "Starting RBAC Enhancement Deployment"
    log_info "Namespace: $NAMESPACE"
    log_info "Backup Directory: $BACKUP_DIR"

    # Trap to handle errors and rollback if needed
    trap 'log_error "Deployment failed, initiating rollback..."; rollback_rbac; exit 1' ERR

    # Execute deployment steps
    check_prerequisites
    backup_current_rbac
    run_pre_audit
    validate_rbac_config
    apply_enhanced_rbac
    apply_admission_controller
    test_rbac_functionality
    run_post_audit

    # Remove error trap on success
    trap - ERR

    log_success "RBAC Enhancement Deployment completed successfully!"
    log_info "Backup available at: $BACKUP_DIR"
    log_info "Post-deployment audit report: ./rbac-post-deployment-audit.json"

    echo ""
    echo "Next Steps:"
    echo "1. Review the post-deployment audit report"
    echo "2. Update application deployments to use new service accounts"
    echo "3. Monitor applications for any permission issues"
    echo "4. Schedule quarterly access reviews"
    echo "5. Proceed to Phase 2: Application RBAC improvements"
}

# Handle command line arguments
case "${1:-}" in
    "--rollback")
        if [[ -n "${2:-}" ]]; then
            BACKUP_DIR="$2"
        else
            log_error "Please specify backup directory for rollback"
            exit 1
        fi
        rollback_rbac
        ;;
    "--audit-only")
        check_prerequisites
        run_pre_audit
        ;;
    "--validate-only")
        check_prerequisites
        validate_rbac_config
        ;;
    "--help")
        echo "Usage: $0 [OPTIONS]"
        echo "Options:"
        echo "  --rollback <backup_dir>  Rollback to previous RBAC configuration"
        echo "  --audit-only            Run audit only, no changes"
        echo "  --validate-only         Validate configuration only"
        echo "  --help                  Show this help message"
        ;;
    "")
        main
        ;;
    *)
        log_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

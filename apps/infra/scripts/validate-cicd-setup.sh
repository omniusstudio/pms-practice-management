#!/bin/bash

# CI/CD Setup Validation Script
# This script validates that all CI/CD components are properly configured for Kubernetes deployment

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
    ((PASSED++))
}

log_warning() {
    echo -e "${YELLOW}[⚠ WARN]${NC} $1"
    ((WARNINGS++))
}

log_error() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
    ((FAILED++))
}

# Validation functions
validate_file_exists() {
    local file_path="$1"
    local description="$2"
    
    if [[ -f "$file_path" ]]; then
        log_success "$description exists: $file_path"
    else
        log_error "$description missing: $file_path"
    fi
}

validate_directory_exists() {
    local dir_path="$1"
    local description="$2"
    
    if [[ -d "$dir_path" ]]; then
        log_success "$description exists: $dir_path"
    else
        log_error "$description missing: $dir_path"
    fi
}

validate_executable() {
    local file_path="$1"
    local description="$2"
    
    if [[ -x "$file_path" ]]; then
        log_success "$description is executable: $file_path"
    else
        log_error "$description is not executable: $file_path"
    fi
}

validate_yaml_syntax() {
    local file_path="$1"
    local description="$2"
    
    if command -v yamllint &> /dev/null; then
        if yamllint "$file_path" &> /dev/null; then
            log_success "$description has valid YAML syntax: $file_path"
        else
            log_warning "$description has YAML syntax issues (may be due to Helm templating): $file_path"
        fi
    else
        log_warning "yamllint not available, skipping YAML validation for: $file_path"
    fi
}

validate_helm_chart() {
    local chart_path="$1"
    
    if command -v helm &> /dev/null; then
        if helm lint "$chart_path" &> /dev/null; then
            log_success "Helm chart validation passed: $chart_path"
        else
            log_error "Helm chart validation failed: $chart_path"
        fi
    else
        log_warning "Helm not available, skipping chart validation"
    fi
}

validate_github_workflows() {
    local workflows_dir="$PROJECT_ROOT/.github/workflows"
    
    log_info "Validating GitHub Actions workflows..."
    
    # Check main workflows
    validate_file_exists "$workflows_dir/ci.yml" "CI workflow"
    validate_file_exists "$workflows_dir/cd.yml" "CD workflow"
    validate_file_exists "$workflows_dir/k8s-deploy.yml" "Kubernetes deployment workflow"
    
    # Validate workflow syntax
    if command -v yamllint &> /dev/null; then
        for workflow in "$workflows_dir"/*.yml "$workflows_dir"/*.yaml; do
            if [[ -f "$workflow" ]]; then
                validate_yaml_syntax "$workflow" "GitHub workflow $(basename "$workflow")"
            fi
        done
    fi
}

validate_kubernetes_configs() {
    local k8s_dir="$PROJECT_ROOT/apps/infra/kubernetes"
    
    log_info "Validating Kubernetes configurations..."
    
    # Check main directories
    validate_directory_exists "$k8s_dir" "Kubernetes directory"
    validate_directory_exists "$k8s_dir/manifests" "Kubernetes manifests directory"
    validate_directory_exists "$k8s_dir/helm" "Helm charts directory"
    
    # Check documentation
    validate_file_exists "$k8s_dir/README.md" "Kubernetes README"
    validate_file_exists "$k8s_dir/CICD-INTEGRATION.md" "CI/CD integration documentation"
    
    # Check Helm chart structure
    local helm_chart="$k8s_dir/helm/pms"
    if [[ -d "$helm_chart" ]]; then
        validate_file_exists "$helm_chart/Chart.yaml" "Helm Chart.yaml"
        validate_file_exists "$helm_chart/values.yaml" "Helm values.yaml"
        validate_file_exists "$helm_chart/values-staging.yaml" "Helm staging values"
        validate_file_exists "$helm_chart/values-production.yaml" "Helm production values"
        
        # Check templates
        local templates_dir="$helm_chart/templates"
        validate_directory_exists "$templates_dir" "Helm templates directory"
        validate_file_exists "$templates_dir/_helpers.tpl" "Helm helpers template"
        validate_file_exists "$templates_dir/backend-deployment.yaml" "Backend deployment template"
        validate_file_exists "$templates_dir/configmap.yaml" "ConfigMap template"
        
        # Validate Helm chart
        validate_helm_chart "$helm_chart"
    fi
    
    # Check manifest files
    local manifests_dir="$k8s_dir/manifests"
    if [[ -d "$manifests_dir" ]]; then
        for manifest in "$manifests_dir"/*.yaml; do
            if [[ -f "$manifest" ]]; then
                validate_yaml_syntax "$manifest" "Kubernetes manifest $(basename "$manifest")"
            fi
        done
    fi
}

validate_deployment_scripts() {
    local scripts_dir="$PROJECT_ROOT/apps/infra/scripts"
    
    log_info "Validating deployment scripts..."
    
    # Check script files
    validate_file_exists "$scripts_dir/deploy-k8s.sh" "Kubernetes deployment script"
    validate_file_exists "$scripts_dir/rollback-k8s.sh" "Kubernetes rollback script"
    validate_file_exists "$scripts_dir/cicd-k8s-deploy.sh" "CI/CD deployment script"
    validate_file_exists "$scripts_dir/validate-cicd-setup.sh" "CI/CD validation script"
    
    # Check script permissions
    validate_executable "$scripts_dir/deploy-k8s.sh" "Kubernetes deployment script"
    validate_executable "$scripts_dir/rollback-k8s.sh" "Kubernetes rollback script"
    validate_executable "$scripts_dir/cicd-k8s-deploy.sh" "CI/CD deployment script"
    validate_executable "$scripts_dir/validate-cicd-setup.sh" "CI/CD validation script"
}

validate_prerequisites() {
    log_info "Validating prerequisites..."
    
    # Check required tools
    local tools=("kubectl" "docker" "git")
    local optional_tools=("helm" "yamllint")
    
    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            log_success "Required tool available: $tool"
        else
            log_error "Required tool missing: $tool"
        fi
    done
    
    for tool in "${optional_tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            log_success "Optional tool available: $tool"
        else
            log_warning "Optional tool missing: $tool (recommended for full functionality)"
        fi
    done
}

validate_environment_variables() {
    log_info "Validating environment variables..."
    
    # Check common environment variables
    local env_vars=("HOME" "USER" "PATH")
    local optional_env_vars=("KUBECONFIG" "ECR_REGISTRY" "AWS_REGION")
    
    for var in "${env_vars[@]}"; do
        if [[ -n "${!var:-}" ]]; then
            log_success "Environment variable set: $var"
        else
            log_error "Environment variable missing: $var"
        fi
    done
    
    for var in "${optional_env_vars[@]}"; do
        if [[ -n "${!var:-}" ]]; then
            log_success "Optional environment variable set: $var"
        else
            log_warning "Optional environment variable not set: $var (may be required for deployment)"
        fi
    done
}

validate_docker_setup() {
    log_info "Validating Docker setup..."
    
    if command -v docker &> /dev/null; then
        if docker info &> /dev/null; then
            log_success "Docker daemon is running and accessible"
        else
            log_error "Docker daemon is not running or not accessible"
        fi
        
        # Check Docker version
        local docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
        log_info "Docker version: $docker_version"
    else
        log_error "Docker is not installed"
    fi
}

validate_kubernetes_connectivity() {
    log_info "Validating Kubernetes connectivity..."
    
    if command -v kubectl &> /dev/null; then
        if kubectl cluster-info &> /dev/null; then
            log_success "Kubernetes cluster is accessible"
            
            # Get cluster info
            local context=$(kubectl config current-context 2>/dev/null || echo "unknown")
            log_info "Current Kubernetes context: $context"
            
            # Check permissions
            if kubectl auth can-i create deployments &> /dev/null; then
                log_success "Have permissions to create deployments"
            else
                log_warning "May not have permissions to create deployments"
            fi
        else
            log_warning "Kubernetes cluster is not accessible (this is OK if not connected to cluster)"
        fi
    fi
}

generate_summary() {
    echo
    echo "=========================================="
    echo "         VALIDATION SUMMARY"
    echo "=========================================="
    echo -e "${GREEN}Passed:${NC}   $PASSED"
    echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
    echo -e "${RED}Failed:${NC}   $FAILED"
    echo "=========================================="
    
    if [[ $FAILED -eq 0 ]]; then
        echo -e "${GREEN}✓ CI/CD setup validation completed successfully!${NC}"
        if [[ $WARNINGS -gt 0 ]]; then
            echo -e "${YELLOW}⚠ Please review the warnings above.${NC}"
        fi
        return 0
    else
        echo -e "${RED}✗ CI/CD setup validation failed!${NC}"
        echo -e "${RED}Please fix the failed checks before proceeding.${NC}"
        return 1
    fi
}

# Main validation function
main() {
    echo "=========================================="
    echo "    CI/CD SETUP VALIDATION"
    echo "=========================================="
    echo "Project Root: $PROJECT_ROOT"
    echo "Validation Time: $(date)"
    echo "=========================================="
    echo
    
    validate_prerequisites
    echo
    
    validate_environment_variables
    echo
    
    validate_docker_setup
    echo
    
    validate_kubernetes_connectivity
    echo
    
    validate_github_workflows
    echo
    
    validate_kubernetes_configs
    echo
    
    validate_deployment_scripts
    echo
    
    generate_summary
}

# Run main function
main "$@"
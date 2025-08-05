#!/bin/bash

# One-Click Rollback Script for Mental Health PMS
# Usage: ./rollback.sh <environment> [version]

set -euo pipefail

ENVIRONMENT=${1:-}
TARGET_VERSION=${2:-}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
CLUSTER_NAME="pms-${ENVIRONMENT}"
SERVICE_BACKEND="pms-backend-${ENVIRONMENT}"
SERVICE_FRONTEND="pms-frontend-${ENVIRONMENT}"

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

# Show usage
show_usage() {
    echo "Usage: $0 <environment> [version]"
    echo ""
    echo "Arguments:"
    echo "  environment    Target environment (staging|production)"
    echo "  version        Specific version to rollback to (optional)"
    echo ""
    echo "Examples:"
    echo "  $0 staging                    # Rollback to previous version"
    echo "  $0 production v20240101-abc123 # Rollback to specific version"
    echo ""
    echo "Available versions:"
    list_available_versions
}

# List available versions
list_available_versions() {
    if [[ -n "$ENVIRONMENT" ]]; then
        log "Available versions for ${ENVIRONMENT}:"
        
        # Get deployment history from SSM
        aws ssm get-parameters-by-path \
            --path "/pms/${ENVIRONMENT}/deployments/" \
            --recursive \
            --region "$AWS_REGION" \
            --query 'Parameters[*].[Name,Value]' \
            --output table 2>/dev/null || echo "No deployment history found"
        
        # Get current version
        local current_version
        current_version=$(aws ssm get-parameter \
            --name "/pms/${ENVIRONMENT}/current-version" \
            --query "Parameter.Value" \
            --output text 2>/dev/null || echo "unknown")
        echo "Current version: ${current_version}"
        
        # Get previous version
        local previous_version
        previous_version=$(aws ssm get-parameter \
            --name "/pms/${ENVIRONMENT}/previous-version" \
            --query "Parameter.Value" \
            --output text 2>/dev/null || echo "unknown")
        echo "Previous version: ${previous_version}"
    fi
}

# Validate inputs
validate_inputs() {
    if [[ -z "$ENVIRONMENT" ]]; then
        log_error "Environment is required"
        show_usage
        exit 1
    fi
    
    if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
        log_error "Environment must be 'staging' or 'production'"
        exit 1
    fi
}

# Get rollback target version
get_rollback_version() {
    if [[ -n "$TARGET_VERSION" ]]; then
        log "Using specified version: ${TARGET_VERSION}"
        echo "$TARGET_VERSION"
    else
        # Get previous version from SSM
        local previous_version
        previous_version=$(aws ssm get-parameter \
            --name "/pms/${ENVIRONMENT}/previous-version" \
            --query "Parameter.Value" \
            --output text 2>/dev/null || echo "")
        
        if [[ -z "$previous_version" || "$previous_version" == "None" ]]; then
            log_error "No previous version found for rollback"
            log "Available options:"
            list_available_versions
            exit 1
        fi
        
        log "Using previous version: ${previous_version}"
        echo "$previous_version"
    fi
}

# Confirm rollback
confirm_rollback() {
    local rollback_version=$1
    local current_version
    
    current_version=$(aws ssm get-parameter \
        --name "/pms/${ENVIRONMENT}/current-version" \
        --query "Parameter.Value" \
        --output text 2>/dev/null || echo "unknown")
    
    echo ""
    log_warning "🚨 ROLLBACK CONFIRMATION 🚨"
    echo "Environment: ${ENVIRONMENT}"
    echo "Current version: ${current_version}"
    echo "Rollback to version: ${rollback_version}"
    echo ""
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log_warning "This is a PRODUCTION rollback!"
        echo ""
    fi
    
    read -p "Are you sure you want to proceed? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log "Rollback cancelled by user"
        exit 0
    fi
}

# Perform rollback using GitHub Actions
perform_rollback() {
    local rollback_version=$1
    
    log "Initiating rollback via GitHub Actions..."
    
    # Trigger GitHub Actions workflow for rollback
    if command -v gh &> /dev/null; then
        log "Using GitHub CLI to trigger rollback workflow"
        
        gh workflow run cd.yml \
            --field environment="$ENVIRONMENT" \
            --field rollback=true \
            --field version="$rollback_version"
        
        if [[ $? -eq 0 ]]; then
            log_success "Rollback workflow triggered successfully"
            log "Monitor the rollback progress at: https://github.com/your-org/pms/actions"
            
            # Wait for workflow to start
            sleep 10
            
            # Show recent workflow runs
            log "Recent workflow runs:"
            gh run list --workflow=cd.yml --limit=5
        else
            log_error "Failed to trigger rollback workflow"
            exit 1
        fi
    else
        log_warning "GitHub CLI not found. Manual rollback required."
        log "Please trigger the rollback manually:"
        echo "1. Go to: https://github.com/your-org/pms/actions/workflows/cd.yml"
        echo "2. Click 'Run workflow'"
        echo "3. Select environment: ${ENVIRONMENT}"
        echo "4. Check 'rollback' option"
        echo "5. Click 'Run workflow'"
    fi
}

# Monitor rollback progress
monitor_rollback() {
    local rollback_version=$1
    
    log "Monitoring rollback progress..."
    
    # Wait for deployment to complete
    local max_wait=1800  # 30 minutes
    local wait_interval=30
    local elapsed=0
    
    while [[ $elapsed -lt $max_wait ]]; do
        # Check current deployed version
        local deployed_version
        deployed_version=$(curl -s "https://${ENVIRONMENT}.pms.example.com/healthz" | jq -r '.version' 2>/dev/null || echo "unknown")
        
        if [[ "$deployed_version" == "$rollback_version" ]]; then
            log_success "Rollback completed successfully!"
            log_success "Deployed version: ${deployed_version}"
            return 0
        fi
        
        log "Waiting for rollback to complete... (${elapsed}s/${max_wait}s)"
        log "Current deployed version: ${deployed_version}"
        log "Target version: ${rollback_version}"
        
        sleep $wait_interval
        elapsed=$((elapsed + wait_interval))
    done
    
    log_error "Rollback monitoring timed out after ${max_wait} seconds"
    log_error "Please check the deployment status manually"
    return 1
}

# Verify rollback
verify_rollback() {
    local rollback_version=$1
    
    log "Verifying rollback..."
    
    # Health check
    local health_url="https://${ENVIRONMENT}.pms.example.com/healthz"
    
    if curl -f -s "$health_url" > /dev/null; then
        local response
        response=$(curl -s "$health_url")
        local deployed_version
        deployed_version=$(echo "$response" | jq -r '.version' 2>/dev/null || echo "unknown")
        
        if [[ "$deployed_version" == "$rollback_version" ]]; then
            log_success "✅ Rollback verification successful!"
            log_success "Environment: ${ENVIRONMENT}"
            log_success "Version: ${deployed_version}"
            log_success "Health status: $(echo "$response" | jq -r '.status' 2>/dev/null || echo "unknown")"
            return 0
        else
            log_error "Version mismatch: expected ${rollback_version}, got ${deployed_version}"
            return 1
        fi
    else
        log_error "Health check failed for ${health_url}"
        return 1
    fi
}

# Main rollback function
main() {
    log "🔄 Starting rollback process for ${ENVIRONMENT}"
    
    # Get rollback version
    local rollback_version
    rollback_version=$(get_rollback_version)
    
    # Confirm rollback
    confirm_rollback "$rollback_version"
    
    # Perform rollback
    perform_rollback "$rollback_version"
    
    # Monitor rollback (optional)
    if [[ "${MONITOR_ROLLBACK:-true}" == "true" ]]; then
        monitor_rollback "$rollback_version"
        verify_rollback "$rollback_version"
    else
        log "Rollback initiated. Monitor progress manually."
    fi
    
    log_success "🎉 Rollback process completed!"
}

# Handle script arguments
case "${1:-}" in
    -h|--help)
        show_usage
        exit 0
        ;;
    -l|--list)
        if [[ -n "${2:-}" ]]; then
            ENVIRONMENT="$2"
            list_available_versions
        else
            echo "Please specify environment: $0 --list <environment>"
        fi
        exit 0
        ;;
    "")
        log_error "Environment is required"
        show_usage
        exit 1
        ;;
    *)
        validate_inputs
        main
        ;;
esac
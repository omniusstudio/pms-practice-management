#!/bin/bash

# Feature Flag Management Script
# Automates common feature flag operations for the PMS system

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="pms"
CONFIGMAP_NAME="feature-flags-config"
DEPLOYMENT_NAME="pms-backend"
FEATURE_FLAGS_FILE="apps/backend/config/feature_flags.json"
KUBECTL_AVAILABLE=false

# Functions
print_usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  status                          - Show current feature flag status"
    echo "  enable <flag_name> [env]        - Enable a feature flag (default: production)"
    echo "  disable <flag_name> [env]       - Disable a feature flag (default: production)"
    echo "  rollout <flag_name> <percent>   - Set rollout percentage (0-100)"
    echo "  list                            - List all available feature flags"
    echo "  validate                        - Validate feature flag configuration"
    echo "  backup                          - Backup current feature flag configuration"
    echo "  restore <backup_file>           - Restore feature flag configuration from backup"
    echo "  audit                           - Show recent feature flag changes"
    echo ""
    echo "Options:"
    echo "  -e, --environment <env>         - Target environment (development, production)"
    echo "  -n, --namespace <namespace>     - Kubernetes namespace (default: pms)"
    echo "  -d, --dry-run                   - Show what would be done without executing"
    echo "  -v, --verbose                   - Verbose output"
    echo "  -h, --help                      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 enable telehealth_appointments_enabled"
    echo "  $0 disable patient_management_enabled production"
    echo "  $0 rollout new_feature 25"
    echo "  $0 status"
}

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
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

check_prerequisites() {
    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        log_error "jq is not installed. Please install jq first."
        exit 1
    fi

    # Check if kubectl is installed (optional for local development)
    if command -v kubectl &> /dev/null; then
        # Check if we can access the Kubernetes cluster
        if kubectl cluster-info &> /dev/null; then
            # Check if namespace exists
            if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
                log_warning "Namespace '$NAMESPACE' does not exist. Using local file mode."
                KUBECTL_AVAILABLE=false
            else
                KUBECTL_AVAILABLE=true
            fi
        else
            log_warning "Cannot access Kubernetes cluster. Using local file mode."
            KUBECTL_AVAILABLE=false
        fi
    else
        log_warning "kubectl not installed. Using local file mode."
        KUBECTL_AVAILABLE=false
    fi
}

get_current_config() {
    local env="${1:-production}"

    if [ "$KUBECTL_AVAILABLE" = "true" ] && kubectl get configmap -n "$NAMESPACE" "$CONFIGMAP_NAME" &> /dev/null; then
        kubectl get configmap -n "$NAMESPACE" "$CONFIGMAP_NAME" -o jsonpath='{.data.feature_flags\.json}' | jq -r ".${env}"
    else
        if [ "$KUBECTL_AVAILABLE" = "false" ]; then
            log_info "Using local file mode" >&2
        else
            log_warning "ConfigMap not found, using local file..." >&2
        fi

        if [ -f "$FEATURE_FLAGS_FILE" ]; then
            jq -r ".${env}" "$FEATURE_FLAGS_FILE"
        else
            log_error "Local feature flags file not found: $FEATURE_FLAGS_FILE" >&2
            exit 1
        fi
    fi
}

update_feature_flag() {
    local flag_name="$1"
    local flag_value="$2"
    local env="${3:-production}"
    local dry_run="${4:-false}"

    log_info "Updating feature flag '$flag_name' to '$flag_value' in environment '$env'"

    # Get current configuration
    local current_config
    current_config=$(kubectl get configmap -n "$NAMESPACE" "$CONFIGMAP_NAME" -o jsonpath='{.data.feature_flags\.json}')

    # Update the configuration
    local updated_config
    updated_config=$(echo "$current_config" | jq ".${env}.${flag_name} = ${flag_value}")

    if [ "$dry_run" = "true" ]; then
        log_info "[DRY RUN] Would update configuration to:"
        echo "$updated_config" | jq .
        return 0
    fi

    # Create audit log entry
    create_audit_entry "feature_flag_toggled" "$flag_name" "$env" "$flag_value"

    # Update ConfigMap
    kubectl patch configmap -n "$NAMESPACE" "$CONFIGMAP_NAME" --type merge -p "{
        \"data\": {
            \"feature_flags.json\": $(echo "$updated_config" | jq -c . | jq -R .)
        }
    }"

    log_success "Feature flag updated successfully"

    # Restart deployment to pick up new configuration
    log_info "Restarting deployment to apply changes..."
    kubectl rollout restart deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE"
    kubectl rollout status deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE" --timeout=300s

    log_success "Deployment restarted successfully"
}

create_audit_entry() {
    local event_type="$1"
    local flag_name="$2"
    local environment="$3"
    local new_value="$4"

    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    local audit_entry
    audit_entry=$(jq -n \
        --arg timestamp "$timestamp" \
        --arg event_type "$event_type" \
        --arg user "$(whoami)" \
        --arg flag_name "$flag_name" \
        --arg environment "$environment" \
        --arg new_value "$new_value" \
        '{
            timestamp: $timestamp,
            event_type: $event_type,
            user: $user,
            feature_flag: $flag_name,
            new_state: ($new_value | fromjson),
            environment: $environment,
            source: "manage-feature-flags.sh"
        }')

    # Log to audit file (create if doesn't exist)
    local audit_file="logs/feature-flag-audit.jsonl"
    mkdir -p "$(dirname "$audit_file")"
    echo "$audit_entry" >> "$audit_file"

    log_info "Audit entry created: $audit_file"
}

show_status() {
    local env="${1:-production}"

    log_info "Current feature flag status for environment: $env"
    echo ""

    local config
    config=$(get_current_config "$env")

    if [ "$config" = "null" ] || [ -z "$config" ]; then
        log_warning "No configuration found for environment '$env'"
        return 1
    fi

    echo "$config" | jq -r 'to_entries[] | "\(.key): \(.value)"' | while read -r line; do
        local flag_name flag_value
        flag_name=$(echo "$line" | cut -d: -f1)
        flag_value=$(echo "$line" | cut -d: -f2 | xargs)

        if [ "$flag_value" = "true" ]; then
            echo -e "  ${GREEN}✓${NC} $flag_name: ${GREEN}enabled${NC}"
        else
            echo -e "  ${RED}✗${NC} $flag_name: ${RED}disabled${NC}"
        fi
    done
}

list_flags() {
    log_info "Available feature flags:"
    echo ""

    if [ -f "$FEATURE_FLAGS_FILE" ]; then
        jq -r '.production | keys[]' "$FEATURE_FLAGS_FILE" | sort | while read -r flag; do
            echo "  - $flag"
        done
    else
        log_error "Feature flags file not found: $FEATURE_FLAGS_FILE"
        exit 1
    fi
}

validate_config() {
    log_info "Validating feature flag configuration..."

    local errors=0

    # Check if file exists and is valid JSON
    if [ ! -f "$FEATURE_FLAGS_FILE" ]; then
        log_error "Feature flags file not found: $FEATURE_FLAGS_FILE"
        ((errors++))
    elif ! jq . "$FEATURE_FLAGS_FILE" > /dev/null 2>&1; then
        log_error "Invalid JSON in feature flags file: $FEATURE_FLAGS_FILE"
        ((errors++))
    else
        log_success "Feature flags file is valid JSON"

        # Check if required environments exist
        local envs=("development" "production")
        for env in "${envs[@]}"; do
            if ! jq -e ".${env}" "$FEATURE_FLAGS_FILE" > /dev/null 2>&1; then
                log_error "Missing environment configuration: $env"
                ((errors++))
            else
                log_success "Environment '$env' configuration found"
            fi
        done

        # Check if all flags are boolean values
        jq -r '.production | to_entries[] | select(.value != true and .value != false) | .key' "$FEATURE_FLAGS_FILE" | while read -r flag; do
            if [ -n "$flag" ]; then
                log_error "Non-boolean value for flag: $flag"
                ((errors++))
            fi
        done
    fi

    # Check ConfigMap in Kubernetes
    if kubectl get configmap -n "$NAMESPACE" "$CONFIGMAP_NAME" &> /dev/null; then
        log_success "ConfigMap '$CONFIGMAP_NAME' exists in namespace '$NAMESPACE'"

        local cm_config
        cm_config=$(kubectl get configmap -n "$NAMESPACE" "$CONFIGMAP_NAME" -o jsonpath='{.data.feature_flags\.json}')

        if echo "$cm_config" | jq . > /dev/null 2>&1; then
            log_success "ConfigMap contains valid JSON"
        else
            log_error "ConfigMap contains invalid JSON"
            ((errors++))
        fi
    else
        log_warning "ConfigMap '$CONFIGMAP_NAME' not found in namespace '$NAMESPACE'"
    fi

    if [ $errors -eq 0 ]; then
        log_success "Configuration validation passed"
        return 0
    else
        log_error "Configuration validation failed with $errors errors"
        return 1
    fi
}

backup_config() {
    local timestamp
    timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="backups/feature-flags-backup-${timestamp}.json"

    mkdir -p "$(dirname "$backup_file")"

    if [ "$KUBECTL_AVAILABLE" = "true" ] && kubectl get configmap -n "$NAMESPACE" "$CONFIGMAP_NAME" &> /dev/null; then
        kubectl get configmap -n "$NAMESPACE" "$CONFIGMAP_NAME" -o jsonpath='{.data.feature_flags\.json}' > "$backup_file"
        log_success "Configuration backed up to: $backup_file"
    else
        if [ "$KUBECTL_AVAILABLE" = "false" ]; then
            log_info "Using local file mode for backup" >&2
        else
            log_warning "ConfigMap not found, backing up local file..." >&2
        fi

        if [ -f "$FEATURE_FLAGS_FILE" ]; then
            cp "$FEATURE_FLAGS_FILE" "$backup_file"
            log_success "Local configuration backed up to: $backup_file"
        else
            log_error "Local feature flags file not found: $FEATURE_FLAGS_FILE" >&2
            exit 1
        fi
    fi
}

show_audit() {
    local audit_file="logs/feature-flag-audit.jsonl"

    if [ ! -f "$audit_file" ]; then
        log_warning "No audit log found: $audit_file"
        return 0
    fi

    log_info "Recent feature flag changes (last 10):"
    echo ""

    tail -n 10 "$audit_file" | while read -r line; do
        local timestamp user flag_name environment new_state
        timestamp=$(echo "$line" | jq -r '.timestamp')
        user=$(echo "$line" | jq -r '.user')
        flag_name=$(echo "$line" | jq -r '.feature_flag')
        environment=$(echo "$line" | jq -r '.environment')
        new_state=$(echo "$line" | jq -r '.new_state')

        local state_color
        if [ "$new_state" = "true" ]; then
            state_color="${GREEN}enabled${NC}"
        else
            state_color="${RED}disabled${NC}"
        fi

        echo -e "  $timestamp - $user: $flag_name ($environment) → $state_color"
    done
}

# Parse command line arguments
COMMAND=""
FLAG_NAME=""
FLAG_VALUE=""
ENVIRONMENT="production"
DRY_RUN="false"
VERBOSE="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        status|enable|disable|rollout|list|validate|backup|restore|audit)
            COMMAND="$1"
            shift
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN="true"
            shift
            ;;
        -v|--verbose)
            VERBOSE="true"
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            if [ -z "$FLAG_NAME" ]; then
                FLAG_NAME="$1"
            elif [ -z "$FLAG_VALUE" ]; then
                FLAG_VALUE="$1"
            else
                log_error "Unknown argument: $1"
                print_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate command
if [ -z "$COMMAND" ]; then
    log_error "No command specified"
    print_usage
    exit 1
fi

# Enable verbose mode if requested
if [ "$VERBOSE" = "true" ]; then
    set -x
fi

# Check prerequisites
check_prerequisites

# Execute command
case $COMMAND in
    status)
        show_status "$ENVIRONMENT"
        ;;
    enable)
        if [ -z "$FLAG_NAME" ]; then
            log_error "Flag name is required for enable command"
            exit 1
        fi
        update_feature_flag "$FLAG_NAME" "true" "$ENVIRONMENT" "$DRY_RUN"
        ;;
    disable)
        if [ -z "$FLAG_NAME" ]; then
            log_error "Flag name is required for disable command"
            exit 1
        fi
        update_feature_flag "$FLAG_NAME" "false" "$ENVIRONMENT" "$DRY_RUN"
        ;;
    rollout)
        if [ -z "$FLAG_NAME" ] || [ -z "$FLAG_VALUE" ]; then
            log_error "Flag name and percentage are required for rollout command"
            exit 1
        fi
        # For now, treat rollout as enable/disable based on percentage
        if [ "$FLAG_VALUE" -gt 0 ]; then
            update_feature_flag "$FLAG_NAME" "true" "$ENVIRONMENT" "$DRY_RUN"
        else
            update_feature_flag "$FLAG_NAME" "false" "$ENVIRONMENT" "$DRY_RUN"
        fi
        ;;
    list)
        list_flags
        ;;
    validate)
        validate_config
        ;;
    backup)
        backup_config
        ;;
    audit)
        show_audit
        ;;
    *)
        log_error "Unknown command: $COMMAND"
        print_usage
        exit 1
        ;;
esac

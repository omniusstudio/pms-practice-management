#!/bin/bash

# Event Bus + ETL Infrastructure Deployment Script
# Mental Health Practice Management System

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="mental-health-pms"
TERRAFORM_DIR="$(dirname "$0")/../terraform"
REQUIRED_TOOLS=("terraform" "aws" "jq")

# Functions
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

check_prerequisites() {
    log_info "Checking prerequisites..."

    for tool in "${REQUIRED_TOOLS[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is not installed or not in PATH"
            exit 1
        fi
    done

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or invalid"
        exit 1
    fi

    log_success "All prerequisites met"
}

validate_environment() {
    local env="$1"
    if [[ ! "$env" =~ ^(dev|staging|prod)$ ]]; then
        log_error "Invalid environment: $env. Must be dev, staging, or prod"
        exit 1
    fi
}

generate_redis_token() {
    # Generate a secure Redis auth token
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

deploy_infrastructure() {
    local environment="$1"
    local redis_token="$2"

    log_info "Deploying infrastructure for environment: $environment"

    cd "$TERRAFORM_DIR"

    # Initialize Terraform
    log_info "Initializing Terraform..."
    terraform init

    # Create terraform.tfvars if it doesn't exist
    if [[ ! -f "terraform.tfvars" ]]; then
        log_info "Creating terraform.tfvars..."
        cat > terraform.tfvars <<EOF
environment = "$environment"
project_name = "$PROJECT_NAME"
aws_region = "us-east-1"
redis_auth_token = "$redis_token"
EOF
    fi

    # Plan deployment
    log_info "Planning Terraform deployment..."
    terraform plan -var="environment=$environment" -var="redis_auth_token=$redis_token"

    # Ask for confirmation
    read -p "Do you want to proceed with the deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warning "Deployment cancelled"
        exit 0
    fi

    # Apply infrastructure
    log_info "Applying Terraform configuration..."
    terraform apply -auto-approve -var="environment=$environment" -var="redis_auth_token=$redis_token"

    # Get outputs
    log_info "Retrieving infrastructure outputs..."
    local redis_endpoint
    local s3_bucket
    local vpc_id

    redis_endpoint=$(terraform output -raw redis_endpoint 2>/dev/null || echo "N/A")
    s3_bucket=$(terraform output -raw s3_bucket_name 2>/dev/null || echo "N/A")
    vpc_id=$(terraform output -raw vpc_id 2>/dev/null || echo "N/A")

    log_success "Infrastructure deployed successfully!"

    # Create environment configuration file
    create_env_config "$environment" "$redis_endpoint" "$s3_bucket" "$redis_token"
}

create_env_config() {
    local environment="$1"
    local redis_endpoint="$2"
    local s3_bucket="$3"
    local redis_token="$4"

    local config_file="../../backend/.env.$environment"

    log_info "Creating environment configuration: $config_file"

    cat > "$config_file" <<EOF
# Event Bus + ETL Configuration for $environment
# Generated on $(date)

# Environment
ENVIRONMENT=$environment

# Redis Configuration
REDIS_URL=redis://:$redis_token@$redis_endpoint:6379
REDIS_AUTH_TOKEN=$redis_token

# AWS Configuration
AWS_REGION=us-east-1
S3_BUCKET=$s3_bucket

# ETL Configuration
ETL_BATCH_SIZE=1000
ETL_BATCH_INTERVAL=300
ETL_MAX_RETRIES=3

# Event Bus Configuration
EVENT_BUS_CONSUMER_GROUP=pms-consumers
EVENT_BUS_CONSUMER_NAME=pms-consumer-1
EVENT_BUS_MAX_EVENTS=100

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security
PHI_SCRUBBING_ENABLED=true
AUDIT_LOGGING_ENABLED=true
EOF

    log_success "Environment configuration created: $config_file"
}

test_deployment() {
    local environment="$1"

    log_info "Testing deployment for environment: $environment"

    # Test Redis connectivity
    log_info "Testing Redis connectivity..."
    local redis_endpoint
    redis_endpoint=$(cd "$TERRAFORM_DIR" && terraform output -raw redis_endpoint 2>/dev/null)

    if [[ "$redis_endpoint" != "N/A" ]] && [[ -n "$redis_endpoint" ]]; then
        if timeout 5 bash -c "</dev/tcp/$redis_endpoint/6379"; then
            log_success "Redis connectivity test passed"
        else
            log_warning "Redis connectivity test failed (this is expected if Redis is in a private subnet)"
        fi
    fi

    # Test S3 bucket access
    log_info "Testing S3 bucket access..."
    local s3_bucket
    s3_bucket=$(cd "$TERRAFORM_DIR" && terraform output -raw s3_bucket_name 2>/dev/null)

    if [[ "$s3_bucket" != "N/A" ]] && [[ -n "$s3_bucket" ]]; then
        if aws s3 ls "s3://$s3_bucket" &> /dev/null; then
            log_success "S3 bucket access test passed"
        else
            log_error "S3 bucket access test failed"
        fi
    fi

    log_success "Deployment testing completed"
}

cleanup_infrastructure() {
    local environment="$1"

    log_warning "This will destroy all infrastructure for environment: $environment"
    read -p "Are you sure you want to proceed? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cleanup cancelled"
        exit 0
    fi

    cd "$TERRAFORM_DIR"

    log_info "Destroying infrastructure..."
    terraform destroy -auto-approve -var="environment=$environment"

    log_success "Infrastructure destroyed"
}

show_usage() {
    echo "Usage: $0 [COMMAND] [ENVIRONMENT]"
    echo ""
    echo "Commands:"
    echo "  deploy    Deploy infrastructure"
    echo "  test      Test deployed infrastructure"
    echo "  cleanup   Destroy infrastructure"
    echo "  help      Show this help message"
    echo ""
    echo "Environments:"
    echo "  dev       Development environment"
    echo "  staging   Staging environment"
    echo "  prod      Production environment"
    echo ""
    echo "Examples:"
    echo "  $0 deploy dev"
    echo "  $0 test staging"
    echo "  $0 cleanup dev"
}

# Main script
main() {
    local command="$1"
    local environment="$2"

    if [[ $# -eq 0 ]] || [[ "$command" == "help" ]]; then
        show_usage
        exit 0
    fi

    if [[ -z "$environment" ]]; then
        log_error "Environment is required"
        show_usage
        exit 1
    fi

    validate_environment "$environment"
    check_prerequisites

    case "$command" in
        "deploy")
            local redis_token
            redis_token=$(generate_redis_token)
            deploy_infrastructure "$environment" "$redis_token"
            test_deployment "$environment"
            ;;
        "test")
            test_deployment "$environment"
            ;;
        "cleanup")
            cleanup_infrastructure "$environment"
            ;;
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"

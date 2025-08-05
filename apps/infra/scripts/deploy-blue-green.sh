#!/bin/bash

# Blue/Green Deployment Script for Mental Health PMS
# Usage: ./deploy-blue-green.sh <environment> <version>

set -euo pipefail

ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
CLUSTER_NAME="pms-${ENVIRONMENT}"
SERVICE_BACKEND="pms-backend-${ENVIRONMENT}"
SERVICE_FRONTEND="pms-frontend-${ENVIRONMENT}"
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

if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
    log_error "Environment must be 'staging' or 'production'"
    exit 1
fi

log "Starting blue/green deployment for ${ENVIRONMENT} environment"
log "Version: ${VERSION}"
log "Cluster: ${CLUSTER_NAME}"

# Function to check if ECS service exists
check_service_exists() {
    local service_name=$1
    aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$service_name" \
        --region "$AWS_REGION" \
        --query 'services[0].status' \
        --output text 2>/dev/null | grep -q "ACTIVE"
}

# Function to get current task definition
get_current_task_definition() {
    local service_name=$1
    aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$service_name" \
        --region "$AWS_REGION" \
        --query 'services[0].taskDefinition' \
        --output text 2>/dev/null || echo "none"
}

# Function to create new task definition
create_task_definition() {
    local service_type=$1  # backend or frontend
    local image_uri="${ECR_REGISTRY}/pms-${service_type}:${VERSION}"
    
    log "Creating task definition for ${service_type}"
    
    # Generate task definition JSON
    cat > "/tmp/taskdef-${service_type}.json" << EOF
{
    "family": "pms-${service_type}-${ENVIRONMENT}",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "512",
    "memory": "1024",
    "executionRoleArn": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/ecsTaskExecutionRole",
    "taskRoleArn": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/pms-task-role-${ENVIRONMENT}",
    "containerDefinitions": [
        {
            "name": "pms-${service_type}",
            "image": "${image_uri}",
            "essential": true,
            "portMappings": [
                {
                    "containerPort": $([ "$service_type" = "backend" ] && echo "8000" || echo "3000"),
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {
                    "name": "ENVIRONMENT",
                    "value": "${ENVIRONMENT}"
                },
                {
                    "name": "VERSION",
                    "value": "${VERSION}"
                }
            ],
            "secrets": [
                {
                    "name": "DATABASE_URL",
                    "valueFrom": "/pms/${ENVIRONMENT}/database-url"
                },
                {
                    "name": "REDIS_URL",
                    "valueFrom": "/pms/${ENVIRONMENT}/redis-url"
                }
            ],
            "healthCheck": {
                "command": [
                    "CMD-SHELL",
                    "curl -f http://localhost:$([ "$service_type" = "backend" ] && echo "8000" || echo "3000")/$([ "$service_type" = "backend" ] && echo "healthz" || echo "health") || exit 1"
                ],
                "interval": 30,
                "timeout": 5,
                "retries": 3,
                "startPeriod": 60
            },
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/pms-${service_type}-${ENVIRONMENT}",
                    "awslogs-region": "${AWS_REGION}",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ]
}
EOF

    # Register task definition
    aws ecs register-task-definition \
        --cli-input-json "file:///tmp/taskdef-${service_type}.json" \
        --region "$AWS_REGION" \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text
}

# Function to update ECS service
update_service() {
    local service_name=$1
    local task_definition_arn=$2
    
    log "Updating service ${service_name} with new task definition"
    
    aws ecs update-service \
        --cluster "$CLUSTER_NAME" \
        --service "$service_name" \
        --task-definition "$task_definition_arn" \
        --region "$AWS_REGION" \
        --query 'service.serviceName' \
        --output text
}

# Function to wait for service stability
wait_for_service_stability() {
    local service_name=$1
    
    log "Waiting for service ${service_name} to reach stable state..."
    
    aws ecs wait services-stable \
        --cluster "$CLUSTER_NAME" \
        --services "$service_name" \
        --region "$AWS_REGION"
    
    if [ $? -eq 0 ]; then
        log_success "Service ${service_name} is stable"
    else
        log_error "Service ${service_name} failed to reach stable state"
        return 1
    fi
}

# Function to perform health check
perform_health_check() {
    local service_type=$1
    local health_endpoint
    
    if [ "$service_type" = "backend" ]; then
        health_endpoint="https://${ENVIRONMENT}.pms.example.com/healthz"
    else
        health_endpoint="https://${ENVIRONMENT}.pms.example.com/health"
    fi
    
    log "Performing health check for ${service_type}: ${health_endpoint}"
    
    local attempts=0
    local max_attempts=$((HEALTH_CHECK_TIMEOUT / HEALTH_CHECK_INTERVAL))
    
    while [ $attempts -lt $max_attempts ]; do
        if curl -f -s "$health_endpoint" > /dev/null 2>&1; then
            log_success "Health check passed for ${service_type}"
            return 0
        fi
        
        attempts=$((attempts + 1))
        log "Health check attempt ${attempts}/${max_attempts} failed, retrying in ${HEALTH_CHECK_INTERVAL}s..."
        sleep $HEALTH_CHECK_INTERVAL
    done
    
    log_error "Health check failed for ${service_type} after ${max_attempts} attempts"
    return 1
}

# Function to rollback service
rollback_service() {
    local service_name=$1
    local previous_task_def=$2
    
    if [ "$previous_task_def" != "none" ]; then
        log_warning "Rolling back ${service_name} to previous task definition"
        update_service "$service_name" "$previous_task_def"
        wait_for_service_stability "$service_name"
    else
        log_error "No previous task definition found for rollback"
    fi
}

# Main deployment logic
main() {
    log "Starting blue/green deployment process"
    
    # Store current task definitions for rollback
    local backend_current_taskdef
    local frontend_current_taskdef
    
    if check_service_exists "$SERVICE_BACKEND"; then
        backend_current_taskdef=$(get_current_task_definition "$SERVICE_BACKEND")
        log "Current backend task definition: ${backend_current_taskdef}"
    else
        backend_current_taskdef="none"
        log_warning "Backend service does not exist, will create new service"
    fi
    
    if check_service_exists "$SERVICE_FRONTEND"; then
        frontend_current_taskdef=$(get_current_task_definition "$SERVICE_FRONTEND")
        log "Current frontend task definition: ${frontend_current_taskdef}"
    else
        frontend_current_taskdef="none"
        log_warning "Frontend service does not exist, will create new service"
    fi
    
    # Create new task definitions
    log "Creating new task definitions..."
    local backend_new_taskdef
    local frontend_new_taskdef
    
    backend_new_taskdef=$(create_task_definition "backend")
    if [ $? -ne 0 ]; then
        log_error "Failed to create backend task definition"
        exit 1
    fi
    log_success "Created backend task definition: ${backend_new_taskdef}"
    
    frontend_new_taskdef=$(create_task_definition "frontend")
    if [ $? -ne 0 ]; then
        log_error "Failed to create frontend task definition"
        exit 1
    fi
    log_success "Created frontend task definition: ${frontend_new_taskdef}"
    
    # Deploy backend service
    log "Deploying backend service..."
    if ! update_service "$SERVICE_BACKEND" "$backend_new_taskdef"; then
        log_error "Failed to update backend service"
        exit 1
    fi
    
    if ! wait_for_service_stability "$SERVICE_BACKEND"; then
        log_error "Backend service failed to stabilize, rolling back..."
        rollback_service "$SERVICE_BACKEND" "$backend_current_taskdef"
        exit 1
    fi
    
    # Health check backend
    if ! perform_health_check "backend"; then
        log_error "Backend health check failed, rolling back..."
        rollback_service "$SERVICE_BACKEND" "$backend_current_taskdef"
        exit 1
    fi
    
    # Deploy frontend service
    log "Deploying frontend service..."
    if ! update_service "$SERVICE_FRONTEND" "$frontend_new_taskdef"; then
        log_error "Failed to update frontend service"
        rollback_service "$SERVICE_BACKEND" "$backend_current_taskdef"
        exit 1
    fi
    
    if ! wait_for_service_stability "$SERVICE_FRONTEND"; then
        log_error "Frontend service failed to stabilize, rolling back..."
        rollback_service "$SERVICE_FRONTEND" "$frontend_current_taskdef"
        rollback_service "$SERVICE_BACKEND" "$backend_current_taskdef"
        exit 1
    fi
    
    # Health check frontend
    if ! perform_health_check "frontend"; then
        log_error "Frontend health check failed, rolling back..."
        rollback_service "$SERVICE_FRONTEND" "$frontend_current_taskdef"
        rollback_service "$SERVICE_BACKEND" "$backend_current_taskdef"
        exit 1
    fi
    
    # Final verification
    log "Performing final system health check..."
    sleep 30  # Allow services to fully initialize
    
    if perform_health_check "backend" && perform_health_check "frontend"; then
        log_success "🎉 Blue/green deployment completed successfully!"
        log_success "Environment: ${ENVIRONMENT}"
        log_success "Version: ${VERSION}"
        log_success "Backend Task Definition: ${backend_new_taskdef}"
        log_success "Frontend Task Definition: ${frontend_new_taskdef}"
        
        # Store deployment metadata
        aws ssm put-parameter \
            --name "/pms/${ENVIRONMENT}/deployment-metadata" \
            --value "{\"version\":\"${VERSION}\",\"deployedAt\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"backendTaskDef\":\"${backend_new_taskdef}\",\"frontendTaskDef\":\"${frontend_new_taskdef}\"}" \
            --overwrite \
            --region "$AWS_REGION"
        
        return 0
    else
        log_error "Final health check failed, rolling back entire deployment..."
        rollback_service "$SERVICE_FRONTEND" "$frontend_current_taskdef"
        rollback_service "$SERVICE_BACKEND" "$backend_current_taskdef"
        exit 1
    fi
}

# Cleanup function
cleanup() {
    log "Cleaning up temporary files..."
    rm -f /tmp/taskdef-*.json
}

# Set trap for cleanup
trap cleanup EXIT

# Run main deployment
main "$@"
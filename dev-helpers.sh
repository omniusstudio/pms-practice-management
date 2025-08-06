#!/bin/bash

# Development Helper Scripts
# Collection of useful commands for local development

NAMESPACE="pms"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to show current status
status() {
    print_header "Current Deployment Status"
    echo "Pods:"
    kubectl get pods -n $NAMESPACE
    echo "\nServices:"
    kubectl get services -n $NAMESPACE
    echo "\nDeployments:"
    kubectl get deployments -n $NAMESPACE
}

# Function to watch logs
logs() {
    local component=${1:-backend}
    print_header "Watching $component logs"
    kubectl logs -f deployment/pms-$component -n $NAMESPACE
}

# Function to shell into a pod
shell() {
    local component=${1:-backend}
    print_header "Opening shell in $component pod"
    kubectl exec -it deployment/pms-$component -n $NAMESPACE -- /bin/bash
}

# Function to port-forward services
forward() {
    local component=${1:-backend}
    local port=${2:-8000}

    case $component in
        "backend")
            print_header "Port-forwarding backend to localhost:$port"
            kubectl port-forward -n $NAMESPACE service/pms-backend $port:8000
            ;;
        "frontend")
            print_header "Port-forwarding frontend to localhost:$port"
            kubectl port-forward -n $NAMESPACE service/pms-frontend $port:80
            ;;
        "postgres")
            print_header "Port-forwarding postgres to localhost:$port"
            kubectl port-forward -n $NAMESPACE service/postgres $port:5432
            ;;
        "redis")
            print_header "Port-forwarding redis to localhost:$port"
            kubectl port-forward -n $NAMESPACE service/redis $port:6379
            ;;
        *)
            print_error "Unknown component: $component"
            echo "Available: backend, frontend, postgres, redis"
            ;;
    esac
}

# Function to restart deployments
restart() {
    local component=${1:-all}

    case $component in
        "backend")
            print_header "Restarting backend"
            kubectl rollout restart deployment/pms-backend -n $NAMESPACE
            kubectl rollout status deployment/pms-backend -n $NAMESPACE
            ;;
        "frontend")
            print_header "Restarting frontend"
            kubectl rollout restart deployment/pms-frontend -n $NAMESPACE
            kubectl rollout status deployment/pms-frontend -n $NAMESPACE
            ;;
        "all")
            print_header "Restarting all deployments"
            kubectl rollout restart deployment/pms-backend -n $NAMESPACE
            kubectl rollout restart deployment/pms-frontend -n $NAMESPACE
            kubectl rollout restart deployment/postgres -n $NAMESPACE
            kubectl rollout restart deployment/redis -n $NAMESPACE
            ;;
        *)
            print_error "Unknown component: $component"
            echo "Available: backend, frontend, all"
            ;;
    esac
}

# Function to clean up and redeploy
clean() {
    print_header "Cleaning up and redeploying"
    print_warning "This will delete all pods and redeploy from k8s-simple.yaml"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete pods --all -n $NAMESPACE
        sleep 5
        kubectl apply -f k8s-simple.yaml
        print_success "Clean redeploy completed"
    else
        print_warning "Clean operation cancelled"
    fi
}

# Function to run development tests
test() {
    print_header "Running Development Tests"

    echo "Testing frontend accessibility..."
    if curl -s -f http://localhost:80 > /dev/null; then
        print_success "Frontend is accessible"
    else
        print_error "Frontend is not accessible"
    fi

    echo "\nTesting backend via port-forward..."
    kubectl port-forward -n $NAMESPACE service/pms-backend 8001:8000 &
    PF_PID=$!
    sleep 3

    if curl -s -f http://localhost:8001/health > /dev/null 2>&1; then
        print_success "Backend API is responding"
    elif curl -s -f http://localhost:8001/ > /dev/null 2>&1; then
        print_success "Backend is responding (no /health endpoint)"
    else
        print_error "Backend is not responding"
    fi

    kill $PF_PID 2>/dev/null || true

    echo "\nChecking pod health..."
    kubectl get pods -n $NAMESPACE | grep -E "(Running|Ready)" && print_success "All pods are healthy" || print_error "Some pods are not healthy"
}

# Function to show help
help() {
    print_header "Development Helper Commands"
    echo "Usage: ./dev-helpers.sh <command> [options]"
    echo ""
    echo "Commands:"
    echo "  status                    - Show current deployment status"
    echo "  logs [component]          - Watch logs (default: backend)"
    echo "  shell [component]         - Open shell in pod (default: backend)"
    echo "  forward <component> [port] - Port-forward service (backend|frontend|postgres|redis)"
    echo "  restart [component]       - Restart deployment (backend|frontend|all)"
    echo "  clean                     - Clean up and redeploy everything"
    echo "  test                      - Run development tests"
    echo "  help                      - Show this help"
    echo ""
    echo "Examples:"
    echo "  ./dev-helpers.sh status"
    echo "  ./dev-helpers.sh logs frontend"
    echo "  ./dev-helpers.sh forward backend 8000"
    echo "  ./dev-helpers.sh restart all"
}

# Main command dispatcher
case ${1:-help} in
    "status")
        status
        ;;
    "logs")
        logs $2
        ;;
    "shell")
        shell $2
        ;;
    "forward")
        forward $2 $3
        ;;
    "restart")
        restart $2
        ;;
    "clean")
        clean
        ;;
    "test")
        test
        ;;
    "help")
        help
        ;;
    *)
        print_error "Unknown command: $1"
        help
        exit 1
        ;;
esac

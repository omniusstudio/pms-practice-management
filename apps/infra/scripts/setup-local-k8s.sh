#!/bin/bash

# Setup Local Kubernetes Testing Environment
# This script helps set up a local Kubernetes environment for testing the PMS application

set -e

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

# Default values
CLUSTER_TYPE=""
CLUSTER_NAME="pms-local"
NAMESPACE="pms-local"
SKIP_BUILD="false"
SKIP_DEPLOY="false"
CLEANUP="false"

# Help function
show_help() {
    cat << EOF
Setup Local Kubernetes Testing Environment

Usage: $0 [OPTIONS]

Options:
    -t, --type TYPE         Kubernetes type: docker-desktop, minikube, or kind
    -n, --name NAME         Cluster name (default: pms-local)
    --namespace NAMESPACE   Kubernetes namespace (default: pms-local)
    --skip-build           Skip building Docker images
    --skip-deploy          Skip deployment after setup
    --cleanup              Clean up existing resources
    -h, --help             Show this help message

Examples:
    $0 --type minikube                    # Setup with minikube
    $0 --type kind --name test-cluster    # Setup with kind using custom name
    $0 --type docker-desktop --skip-build # Setup with Docker Desktop, skip build
    $0 --cleanup                          # Clean up existing resources

Supported Kubernetes Types:
    docker-desktop  - Docker Desktop Kubernetes (recommended for macOS)
    minikube       - Minikube (lightweight, multiple drivers)
    kind           - Kind (Kubernetes in Docker, great for CI/CD)

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            CLUSTER_TYPE="$2"
            shift 2
            ;;
        -n|--name)
            CLUSTER_NAME="$2"
            shift 2
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD="true"
            shift
            ;;
        --skip-deploy)
            SKIP_DEPLOY="true"
            shift
            ;;
        --cleanup)
            CLEANUP="true"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
log_info "Project root: $PROJECT_ROOT"

# Cleanup function
cleanup_resources() {
    log_info "Cleaning up existing resources..."

    # Remove Helm release if exists
    if helm list -n "$NAMESPACE" | grep -q pms-local; then
        log_info "Removing Helm release..."
        helm uninstall pms-local -n "$NAMESPACE" || true
    fi

    # Remove namespace
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Removing namespace $NAMESPACE..."
        kubectl delete namespace "$NAMESPACE" --timeout=60s || true
    fi

    # Remove from /etc/hosts
    if grep -q "pms.local" /etc/hosts; then
        log_info "Removing pms.local from /etc/hosts..."
        sudo sed -i '' '/pms.local/d' /etc/hosts || true
    fi

    # Stop port-forwards
    pkill -f "kubectl port-forward" || true

    log_success "Cleanup completed"
}

# Interactive cluster type selection
select_cluster_type() {
    if [[ -n "$CLUSTER_TYPE" ]]; then
        return
    fi

    echo
    log_info "Select your preferred local Kubernetes option:"
    echo "1) Docker Desktop Kubernetes (recommended for macOS)"
    echo "2) Minikube (lightweight, multiple drivers)"
    echo "3) Kind (Kubernetes in Docker, great for CI/CD)"
    echo

    while true; do
        read -p "Enter your choice (1-3): " choice
        case $choice in
            1)
                CLUSTER_TYPE="docker-desktop"
                break
                ;;
            2)
                CLUSTER_TYPE="minikube"
                break
                ;;
            3)
                CLUSTER_TYPE="kind"
                break
                ;;
            *)
                log_error "Invalid choice. Please enter 1, 2, or 3."
                ;;
        esac
    done
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi

    # Check Helm
    if ! command -v helm &> /dev/null; then
        log_error "Helm is not installed. Please install Helm first."
        exit 1
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Setup Docker Desktop Kubernetes
setup_docker_desktop() {
    log_info "Setting up Docker Desktop Kubernetes..."

    # Check if Kubernetes is enabled
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Kubernetes is not enabled in Docker Desktop."
        log_info "Please enable Kubernetes in Docker Desktop:"
        log_info "1. Open Docker Desktop"
        log_info "2. Go to Settings → Kubernetes"
        log_info "3. Check 'Enable Kubernetes'"
        log_info "4. Click 'Apply & Restart'"
        exit 1
    fi

    # Install NGINX Ingress Controller
    log_info "Installing NGINX Ingress Controller..."
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml

    # Wait for ingress controller
    log_info "Waiting for ingress controller to be ready..."
    kubectl wait --namespace ingress-nginx \
        --for=condition=ready pod \
        --selector=app.kubernetes.io/component=controller \
        --timeout=120s

    # Install metrics server
    log_info "Installing metrics server..."
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

    # Patch metrics server for local development
    kubectl patch deployment metrics-server -n kube-system --type='json' \
        -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'

    log_success "Docker Desktop Kubernetes setup completed"
}

# Setup Minikube
setup_minikube() {
    log_info "Setting up Minikube..."

    # Check if minikube is installed
    if ! command -v minikube &> /dev/null; then
        log_error "Minikube is not installed. Installing..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install minikube
        else
            log_error "Please install minikube manually for your OS"
            exit 1
        fi
    fi

    # Start minikube if not running
    if ! minikube status &> /dev/null; then
        log_info "Starting Minikube..."
        minikube start --driver=docker --cpus=4 --memory=8192 --profile="$CLUSTER_NAME"
    else
        log_info "Minikube is already running"
    fi

    # Set kubectl context
    kubectl config use-context "$CLUSTER_NAME"

    # Enable add-ons
    log_info "Enabling Minikube add-ons..."
    minikube addons enable ingress --profile="$CLUSTER_NAME"
    minikube addons enable metrics-server --profile="$CLUSTER_NAME"

    log_success "Minikube setup completed"
}

# Setup Kind
setup_kind() {
    log_info "Setting up Kind..."

    # Check if kind is installed
    if ! command -v kind &> /dev/null; then
        log_error "Kind is not installed. Installing..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install kind
        else
            log_error "Please install kind manually for your OS"
            exit 1
        fi
    fi

    # Create cluster configuration
    local kind_config="/tmp/kind-config-$CLUSTER_NAME.yaml"
    cat > "$kind_config" << EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
- role: worker
- role: worker
EOF

    # Create cluster if it doesn't exist
    if ! kind get clusters | grep -q "$CLUSTER_NAME"; then
        log_info "Creating Kind cluster..."
        kind create cluster --config "$kind_config" --name "$CLUSTER_NAME"
    else
        log_info "Kind cluster already exists"
    fi

    # Set kubectl context
    kubectl config use-context "kind-$CLUSTER_NAME"

    # Install ingress controller
    log_info "Installing NGINX Ingress Controller..."
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

    # Wait for ingress controller
    kubectl wait --namespace ingress-nginx \
        --for=condition=ready pod \
        --selector=app.kubernetes.io/component=controller \
        --timeout=90s

    # Clean up config file
    rm -f "$kind_config"

    log_success "Kind setup completed"
}

# Build Docker images
build_images() {
    if [[ "$SKIP_BUILD" == "true" ]]; then
        log_info "Skipping Docker image build"
        return
    fi

    log_info "Building Docker images..."

    cd "$PROJECT_ROOT"

    # Build backend image
    log_info "Building backend image..."
    docker build -t pms-backend:local-test ./apps/backend

    # Build frontend image
    log_info "Building frontend image..."
    docker build -t pms-frontend:local-test ./apps/frontend

    # Load images into cluster
    case $CLUSTER_TYPE in
        minikube)
            log_info "Loading images into Minikube..."
            minikube image load pms-backend:local-test --profile="$CLUSTER_NAME"
            minikube image load pms-frontend:local-test --profile="$CLUSTER_NAME"
            ;;
        kind)
            log_info "Loading images into Kind..."
            kind load docker-image pms-backend:local-test --name "$CLUSTER_NAME"
            kind load docker-image pms-frontend:local-test --name "$CLUSTER_NAME"
            ;;
        docker-desktop)
            log_info "Images available in Docker Desktop"
            ;;
    esac

    log_success "Docker images built and loaded"
}

# Create local values file
create_local_values() {
    local values_file="$PROJECT_ROOT/apps/infra/kubernetes/helm/pms/values-local.yaml"

    log_info "Creating local Helm values file..."

    cat > "$values_file" << 'EOF'
global:
  environment: local
  version: local-test
  registry: ""
  pullPolicy: Never  # Use local images

app:
  environment: local
  domain: pms.local

backend:
  image:
    repository: pms-backend
    tag: local-test
  replicas: 1
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi

frontend:
  image:
    repository: pms-frontend
    tag: local-test
  replicas: 1
  resources:
    requests:
      cpu: 50m
      memory: 128Mi
    limits:
      cpu: 200m
      memory: 256Mi

ingress:
  enabled: false  # Disable ingress dependency since it's installed by setup script
  className: nginx
  host: pms.local
  tls:
    enabled: false  # Disable TLS for local testing

# Service Account configuration
serviceAccount:
  create: true
  annotations: {}
  name: ""

# Use local database
configMap:
  data:
    DATABASE_URL: "postgresql://postgres:postgres@postgresql:5432/pms_local"
    REDIS_URL: "redis://redis:6379"
    ENVIRONMENT: "local"
    DEBUG: "true"

# Disable external dependencies for local testing
dependencies:
  postgresql:
    enabled: true
  redis:
    enabled: true
    auth:
      enabled: false

# Disable monitoring for local testing
monitoring:
  enabled: false

# Disable backup for local testing
backup:
  enabled: false

# Disable cert-manager for local testing
certManager:
  enabled: false
EOF

    log_success "Local values file created: $values_file"
}

# Deploy application
deploy_application() {
    if [[ "$SKIP_DEPLOY" == "true" ]]; then
        log_info "Skipping application deployment"
        return
    fi

    log_info "Deploying application to local cluster..."

    # Create namespace
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

    # Deploy with Helm
    cd "$PROJECT_ROOT/apps/infra/kubernetes/helm"

    helm upgrade --install pms-local pms/ \
        --namespace "$NAMESPACE" \
        --values pms/values-local.yaml \
        --wait \
        --timeout=10m

    log_success "Application deployed successfully"
}

# Configure local access
configure_access() {
    log_info "Configuring local access..."

    # Add to /etc/hosts
    if ! grep -q "pms.local" /etc/hosts; then
        echo "127.0.0.1 pms.local" | sudo tee -a /etc/hosts
        log_success "Added pms.local to /etc/hosts"
    fi

    # For minikube, update with minikube IP
    if [[ "$CLUSTER_TYPE" == "minikube" ]]; then
        local minikube_ip
        minikube_ip=$(minikube ip --profile="$CLUSTER_NAME")
        if ! grep -q "$minikube_ip pms.local" /etc/hosts; then
            sudo sed -i '' '/pms.local/d' /etc/hosts
            echo "$minikube_ip pms.local" | sudo tee -a /etc/hosts
            log_success "Updated /etc/hosts with Minikube IP: $minikube_ip"
        fi
    fi
}

# Run health checks
run_health_checks() {
    log_info "Running health checks..."

    # Wait for pods to be ready
    log_info "Waiting for pods to be ready..."
    kubectl wait --for=condition=ready pod -l app=pms-backend -n "$NAMESPACE" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=pms-frontend -n "$NAMESPACE" --timeout=300s

    # Check pod status
    log_info "Pod status:"
    kubectl get pods -n "$NAMESPACE"

    # Check services
    log_info "Service status:"
    kubectl get services -n "$NAMESPACE"

    # Check ingress
    log_info "Ingress status:"
    kubectl get ingress -n "$NAMESPACE"

    log_success "Health checks completed"
}

# Show access information
show_access_info() {
    echo
    log_success "Local Kubernetes setup completed successfully!"
    echo
    log_info "Access Information:"
    echo "  Frontend: http://pms.local"
    echo "  Backend API: http://pms.local/api"
    echo
    log_info "Alternative access (port-forward):"
    echo "  kubectl port-forward -n $NAMESPACE service/pms-frontend 3000:3000"
    echo "  kubectl port-forward -n $NAMESPACE service/pms-backend 8000:8000"
    echo
    log_info "Useful commands:"
    echo "  kubectl get pods -n $NAMESPACE"
    echo "  kubectl logs -n $NAMESPACE -l app=pms-backend"
    echo "  kubectl logs -n $NAMESPACE -l app=pms-frontend"
    echo
    log_info "To clean up:"
    echo "  $0 --cleanup"
    echo
}

# Main function
main() {
    echo "========================================"
    echo "    LOCAL KUBERNETES SETUP"
    echo "========================================"
    echo

    # Handle cleanup
    if [[ "$CLEANUP" == "true" ]]; then
        cleanup_resources
        exit 0
    fi

    # Check prerequisites
    check_prerequisites

    # Select cluster type if not provided
    select_cluster_type

    log_info "Setting up local Kubernetes with: $CLUSTER_TYPE"

    # Setup cluster based on type
    case $CLUSTER_TYPE in
        docker-desktop)
            setup_docker_desktop
            ;;
        minikube)
            setup_minikube
            ;;
        kind)
            setup_kind
            ;;
        *)
            log_error "Invalid cluster type: $CLUSTER_TYPE"
            exit 1
            ;;
    esac

    # Build images
    build_images

    # Create local values
    create_local_values

    # Deploy application
    deploy_application

    # Configure access
    configure_access

    # Run health checks
    run_health_checks

    # Show access information
    show_access_info
}

# Run main function
main "$@"

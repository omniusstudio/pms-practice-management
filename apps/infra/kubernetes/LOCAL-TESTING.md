# Local Kubernetes Testing Guide

This guide provides comprehensive instructions for testing the Mental Health PMS Kubernetes setup locally using various local Kubernetes solutions.

## Overview

Local Kubernetes testing allows you to:
- Test Kubernetes configurations before deploying to staging/production
- Develop and debug Kubernetes manifests locally
- Validate Helm charts and deployment scripts
- Test CI/CD pipeline components locally
- Experiment with different configurations safely

## Local Kubernetes Options

### 1. Docker Desktop Kubernetes (Recommended for macOS)

**Pros:**
- Easy setup and integration with Docker
- Good performance on macOS
- Built-in load balancer support
- Integrated with Docker ecosystem

**Cons:**
- Resource intensive
- Limited to single-node cluster

#### Setup Instructions

1. **Enable Kubernetes in Docker Desktop:**
   ```bash
   # Open Docker Desktop → Settings → Kubernetes → Enable Kubernetes
   # Wait for Kubernetes to start (green indicator)
   ```

2. **Verify Installation:**
   ```bash
   kubectl cluster-info
   kubectl get nodes
   ```

3. **Install Required Components:**
   ```bash
   # Install NGINX Ingress Controller
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
   
   # Wait for ingress controller to be ready
   kubectl wait --namespace ingress-nginx \
     --for=condition=ready pod \
     --selector=app.kubernetes.io/component=controller \
     --timeout=120s
   
   # Install metrics server (for HPA)
   kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
   
   # Patch metrics server for local development
   kubectl patch deployment metrics-server -n kube-system --type='json' \
     -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'
   ```

### 2. Minikube

**Pros:**
- Lightweight and fast startup
- Multiple driver options (Docker, VirtualBox, etc.)
- Add-on ecosystem
- Multi-node cluster support

**Cons:**
- Additional tool to manage
- Separate from Docker Desktop

#### Setup Instructions

1. **Install Minikube:**
   ```bash
   # macOS
   brew install minikube
   
   # Or download directly
   curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-darwin-amd64
   sudo install minikube-darwin-amd64 /usr/local/bin/minikube
   ```

2. **Start Minikube:**
   ```bash
   # Start with Docker driver (recommended)
   minikube start --driver=docker --cpus=4 --memory=8192
   
   # Or with more resources for testing
   minikube start --driver=docker --cpus=6 --memory=12288 --disk-size=50g
   ```

3. **Enable Required Add-ons:**
   ```bash
   # Enable ingress
   minikube addons enable ingress
   
   # Enable metrics server
   minikube addons enable metrics-server
   
   # Enable dashboard (optional)
   minikube addons enable dashboard
   ```

4. **Configure kubectl:**
   ```bash
   # Set kubectl context to minikube
   kubectl config use-context minikube
   
   # Verify connection
   kubectl cluster-info
   ```

### 3. Kind (Kubernetes in Docker)

**Pros:**
- Very lightweight
- Fast cluster creation/deletion
- Multi-node cluster support
- Great for CI/CD testing

**Cons:**
- Less integrated ecosystem
- Requires more manual configuration

#### Setup Instructions

1. **Install Kind:**
   ```bash
   # macOS
   brew install kind
   
   # Or download directly
   curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-darwin-amd64
   chmod +x ./kind
   sudo mv ./kind /usr/local/bin/kind
   ```

2. **Create Cluster Configuration:**
   ```bash
   # Create kind-config.yaml
   cat > kind-config.yaml << EOF
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
   ```

3. **Create Cluster:**
   ```bash
   # Create cluster with configuration
   kind create cluster --config kind-config.yaml --name pms-local
   
   # Set kubectl context
   kubectl cluster-info --context kind-pms-local
   ```

4. **Install Ingress Controller:**
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
   
   # Wait for ingress controller
   kubectl wait --namespace ingress-nginx \
     --for=condition=ready pod \
     --selector=app.kubernetes.io/component=controller \
     --timeout=90s
   ```

## Local Testing Setup

### 1. Prepare Local Environment

```bash
# Navigate to the project directory
cd "/Volumes/external storage /PMS"

# Set up local environment variables
export ECR_REGISTRY="local-registry"
export VERSION="local-test"
export DOMAIN_NAME="pms.local"
export ENVIRONMENT="local"

# Create local namespace
kubectl create namespace pms-local
```

### 2. Build Local Images

```bash
# Build backend image
docker build -t pms-backend:local-test ./apps/backend

# Build frontend image
docker build -t pms-frontend:local-test ./apps/frontend

# For minikube, load images into minikube
if command -v minikube &> /dev/null && minikube status &> /dev/null; then
    minikube image load pms-backend:local-test
    minikube image load pms-frontend:local-test
fi

# For kind, load images into kind
if command -v kind &> /dev/null; then
    kind load docker-image pms-backend:local-test --name pms-local
    kind load docker-image pms-frontend:local-test --name pms-local
fi
```

### 3. Create Local Values File

Create a local Helm values file for testing:

```bash
# Create local values file
cat > apps/infra/kubernetes/helm/pms/values-local.yaml << 'EOF'
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
  enabled: true
  className: nginx
  host: pms.local
  tls:
    enabled: false  # Disable TLS for local testing

# Use local database
configMap:
  data:
    DATABASE_URL: "sqlite:///app/local.db"
    REDIS_URL: "redis://redis:6379"
    ENVIRONMENT: "local"
    DEBUG: "true"

# Disable external dependencies for local testing
dependencies:
  postgresql:
    enabled: false
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
EOF
```

### 4. Deploy to Local Cluster

#### Option A: Using Helm (Recommended)

```bash
# Navigate to Helm chart directory
cd apps/infra/kubernetes/helm

# Install/upgrade with local values
helm upgrade --install pms-local pms/ \
  --namespace pms-local \
  --create-namespace \
  --values pms/values-local.yaml \
  --wait \
  --timeout=10m

# Check deployment status
kubectl get pods -n pms-local
kubectl get services -n pms-local
kubectl get ingress -n pms-local
```

#### Option B: Using kubectl with Modified Manifests

```bash
# Create local manifests directory
mkdir -p apps/infra/kubernetes/local-manifests

# Copy and modify manifests for local testing
cp apps/infra/kubernetes/manifests/* apps/infra/kubernetes/local-manifests/

# Update image references in local manifests
sed -i '' 's|your-account.dkr.ecr.us-west-2.amazonaws.com/pms-backend:.*|pms-backend:local-test|g' apps/infra/kubernetes/local-manifests/*
sed -i '' 's|your-account.dkr.ecr.us-west-2.amazonaws.com/pms-frontend:.*|pms-frontend:local-test|g' apps/infra/kubernetes/local-manifests/*
sed -i '' 's|imagePullPolicy: Always|imagePullPolicy: Never|g' apps/infra/kubernetes/local-manifests/*

# Deploy to local cluster
kubectl apply -f apps/infra/kubernetes/local-manifests/ -n pms-local
```

### 5. Configure Local Access

```bash
# Add pms.local to /etc/hosts
echo "127.0.0.1 pms.local" | sudo tee -a /etc/hosts

# For minikube, get the IP and update hosts
if command -v minikube &> /dev/null && minikube status &> /dev/null; then
    MINIKUBE_IP=$(minikube ip)
    echo "$MINIKUBE_IP pms.local" | sudo tee -a /etc/hosts
fi

# Port forward for direct access (alternative to ingress)
kubectl port-forward -n pms-local service/pms-frontend 3000:3000 &
kubectl port-forward -n pms-local service/pms-backend 8000:8000 &
```

## Testing and Validation

### 1. Basic Health Checks

```bash
# Check all pods are running
kubectl get pods -n pms-local

# Check services
kubectl get services -n pms-local

# Check ingress
kubectl get ingress -n pms-local

# Check logs
kubectl logs -n pms-local -l app=pms-backend --tail=50
kubectl logs -n pms-local -l app=pms-frontend --tail=50
```

### 2. Application Testing

```bash
# Test backend API
curl http://pms.local/api/health
# Or with port-forward
curl http://localhost:8000/api/health

# Test frontend
curl http://pms.local
# Or with port-forward
curl http://localhost:3000

# Test database connectivity
kubectl exec -n pms-local -it deployment/pms-backend -- python -c "from database import engine; print('Database connection successful')"
```

### 3. Validate Deployment Scripts

```bash
# Test the deployment script with dry-run
cd apps/infra/scripts
./cicd-k8s-deploy.sh --environment local --method helm --version local-test --dry-run

# Test validation script
./validate-cicd-setup.sh
```

### 4. Test Scaling and Updates

```bash
# Test horizontal scaling
kubectl scale deployment pms-backend --replicas=3 -n pms-local
kubectl get pods -n pms-local -w

# Test rolling update
kubectl set image deployment/pms-backend pms-backend=pms-backend:local-test-v2 -n pms-local
kubectl rollout status deployment/pms-backend -n pms-local

# Test rollback
kubectl rollout undo deployment/pms-backend -n pms-local
```

## Troubleshooting

### Common Issues

1. **Images not found:**
   ```bash
   # For minikube
   minikube image load pms-backend:local-test
   
   # For kind
   kind load docker-image pms-backend:local-test --name pms-local
   
   # Check if images are available
   kubectl describe pod <pod-name> -n pms-local
   ```

2. **Ingress not working:**
   ```bash
   # Check ingress controller
   kubectl get pods -n ingress-nginx
   
   # Check ingress configuration
   kubectl describe ingress -n pms-local
   
   # Use port-forward as alternative
   kubectl port-forward -n pms-local service/pms-frontend 3000:3000
   ```

3. **Database connection issues:**
   ```bash
   # Check if using SQLite for local testing
   kubectl exec -n pms-local -it deployment/pms-backend -- env | grep DATABASE_URL
   
   # Check pod logs
   kubectl logs -n pms-local deployment/pms-backend
   ```

4. **Resource constraints:**
   ```bash
   # Check resource usage
   kubectl top nodes
   kubectl top pods -n pms-local
   
   # Reduce resource requests in values-local.yaml
   ```

### Debug Commands

```bash
# Get comprehensive cluster info
kubectl cluster-info dump --namespace pms-local

# Check events
kubectl get events -n pms-local --sort-by='.lastTimestamp'

# Describe problematic resources
kubectl describe pod <pod-name> -n pms-local
kubectl describe service <service-name> -n pms-local

# Access pod shell for debugging
kubectl exec -n pms-local -it deployment/pms-backend -- /bin/bash
```

## Cleanup

### Remove Local Deployment

```bash
# Using Helm
helm uninstall pms-local -n pms-local

# Using kubectl
kubectl delete namespace pms-local

# Remove from /etc/hosts
sudo sed -i '' '/pms.local/d' /etc/hosts

# Stop port-forwards
pkill -f "kubectl port-forward"
```

### Remove Local Cluster

```bash
# Docker Desktop - disable in settings

# Minikube
minikube stop
minikube delete

# Kind
kind delete cluster --name pms-local
```

## Best Practices for Local Testing

1. **Use Resource Limits**: Set appropriate CPU/memory limits for local testing
2. **Disable External Dependencies**: Use local databases and disable external services
3. **Use Local Images**: Build and use local images to avoid registry dependencies
4. **Test Incrementally**: Test individual components before full deployment
5. **Monitor Resources**: Keep an eye on local system resources
6. **Clean Up Regularly**: Remove unused resources to free up space
7. **Version Control**: Keep local configuration files in version control
8. **Document Changes**: Document any local-specific modifications

## Integration with CI/CD

You can integrate local testing into your development workflow:

```bash
# Create a local testing script
cat > scripts/test-local-k8s.sh << 'EOF'
#!/bin/bash
set -e

echo "Starting local Kubernetes testing..."

# Build images
docker build -t pms-backend:local-test ./apps/backend
docker build -t pms-frontend:local-test ./apps/frontend

# Load images into cluster
if command -v minikube &> /dev/null && minikube status &> /dev/null; then
    minikube image load pms-backend:local-test
    minikube image load pms-frontend:local-test
fi

# Deploy with Helm
helm upgrade --install pms-local apps/infra/kubernetes/helm/pms/ \
  --namespace pms-local \
  --create-namespace \
  --values apps/infra/kubernetes/helm/pms/values-local.yaml \
  --wait

# Run tests
kubectl wait --for=condition=ready pod -l app=pms-backend -n pms-local --timeout=300s
kubectl wait --for=condition=ready pod -l app=pms-frontend -n pms-local --timeout=300s

# Health checks
curl -f http://localhost:8000/api/health || (kubectl port-forward -n pms-local service/pms-backend 8000:8000 &)
sleep 5
curl -f http://localhost:8000/api/health

echo "Local Kubernetes testing completed successfully!"
EOF

chmod +x scripts/test-local-k8s.sh
```

This comprehensive guide should help you set up and test your Kubernetes configuration locally before deploying to staging or production environments.
#!/bin/bash

# Local Development Loop: Update, Build, Redeploy
# Usage: ./dev-loop.sh [backend|frontend|all]

set -e

COMPONENT=${1:-all}
NAMESPACE="pms"

echo "🚀 Starting Local Dev Loop for: $COMPONENT"
echo "================================================"

# Function to build and redeploy backend
build_backend() {
    echo "📦 Building backend image..."
    docker build -t pms-backend:latest ./apps/backend
    
    echo "🔄 Restarting backend deployment..."
    kubectl rollout restart deployment/pms-backend -n $NAMESPACE
    
    echo "⏳ Waiting for backend rollout to complete..."
    kubectl rollout status deployment/pms-backend -n $NAMESPACE --timeout=120s
}

# Function to build and redeploy frontend
build_frontend() {
    echo "📦 Building frontend image..."
    docker build -t pms-frontend:latest ./apps/frontend
    
    echo "🔄 Restarting frontend deployment..."
    kubectl rollout restart deployment/pms-frontend -n $NAMESPACE
    
    echo "⏳ Waiting for frontend rollout to complete..."
    kubectl rollout status deployment/pms-frontend -n $NAMESPACE --timeout=120s
}

# Function to check deployment status
check_status() {
    echo "\n📊 Current Deployment Status:"
    kubectl get pods -n $NAMESPACE -o wide
    
    echo "\n🌐 Services:"
    kubectl get services -n $NAMESPACE
    
    echo "\n✅ Application URLs:"
    echo "   Frontend: http://localhost:80"
    echo "   Backend API: kubectl port-forward -n pms service/pms-backend 8000:8000"
}

# Function to run quick tests
run_tests() {
    echo "\n🧪 Running quick health checks..."
    
    # Test frontend
    echo "Testing frontend..."
    if curl -s -f http://localhost:80 > /dev/null; then
        echo "✅ Frontend is responding"
    else
        echo "❌ Frontend is not responding"
    fi
    
    # Test backend via port-forward (non-blocking)
    echo "Testing backend (via port-forward)..."
    kubectl port-forward -n $NAMESPACE service/pms-backend 8001:8000 &
    PF_PID=$!
    sleep 3
    
    if curl -s -f http://localhost:8001/health > /dev/null 2>&1; then
        echo "✅ Backend API is responding"
    else
        echo "❌ Backend API is not responding"
    fi
    
    # Clean up port-forward
    kill $PF_PID 2>/dev/null || true
}

# Main execution logic
case $COMPONENT in
    "backend")
        build_backend
        ;;
    "frontend")
        build_frontend
        ;;
    "all")
        build_backend
        build_frontend
        ;;
    *)
        echo "❌ Invalid component: $COMPONENT"
        echo "Usage: $0 [backend|frontend|all]"
        exit 1
        ;;
esac

check_status
run_tests

echo "\n🎉 Dev loop completed successfully!"
echo "\n💡 Quick commands:"
echo "   Watch logs: kubectl logs -f deployment/pms-backend -n pms"
echo "   Shell into pod: kubectl exec -it deployment/pms-backend -n pms -- /bin/bash"
echo "   Delete all pods: kubectl delete pods --all -n pms"
echo "   Full redeploy: kubectl apply -f k8s-simple.yaml"
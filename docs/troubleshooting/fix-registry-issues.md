# Fix for Kubernetes Registry Issues with Docker Desktop

## Problem
The Kubernetes pods are failing to pull images from the local registry (10.96.234.11:5000) with ImagePullBackOff errors. The issue is that Docker Desktop's Kubernetes cluster is trying to use HTTPS for the registry connection, but the local registry is HTTP-only.

## Root Cause
The error message shows: "unexpected status from HEAD request to http://registry-mirror:1273/v2/pms-backend/manifests/latest?ns=10.96.234.11%3A5000: 500 Internal Server Error"

This indicates that:
1. Docker Desktop is using a registry mirror
2. The cluster IP (10.96.234.11:5000) is not configured as an insecure registry
3. Kubernetes is trying to access the registry via HTTPS by default

## Solutions

### Solution 1: Configure Docker Desktop for Insecure Registry (Recommended)

1. **Open Docker Desktop Settings:**
   - Click on Docker Desktop icon in system tray
   - Go to Settings → Docker Engine

2. **Add insecure registry configuration:**
   ```json
   {
     "builder": {
       "gc": {
         "defaultKeepStorage": "20GB",
         "enabled": true
       }
     },
     "experimental": false,
     "insecure-registries": [
       "localhost:30500",
       "10.96.234.11:5000",
       "127.0.0.1:30500"
     ]
   }
   ```

3. **Apply and Restart Docker Desktop**

4. **Restart Kubernetes:**
   - Go to Settings → Kubernetes
   - Click "Reset Kubernetes Cluster"
   - Wait for Kubernetes to restart

### Solution 2: Use localhost:30500 in Deployments

Modify the deployment files to use `localhost:30500` instead of `10.96.234.11:5000`:

1. **Update backend-deployment.yaml:**
   ```yaml
   image: localhost:30500/pms-backend:latest
   ```

2. **Update frontend-deployment.yaml:**
   ```yaml
   image: localhost:30500/pms-frontend:latest
   ```

3. **Update Helm values:**
   - In `values-local.yaml` and `values-local-registry.yaml`
   - Change registry from `10.96.234.11:5000` to `localhost:30500`

### Solution 3: Apply Registry Configuration DaemonSet

The existing `registry-config-daemonset.yaml` should configure containerd for insecure registry access:

```bash
# Apply the daemonset
kubectl apply -f apps/infra/kubernetes/registry-config-daemonset.yaml

# Wait for it to run on all nodes
kubectl get pods -n kube-system -l name=registry-config

# Check logs
kubectl logs -n kube-system -l name=registry-config
```

## Quick Fix Commands

```bash
# 1. Delete failing pods to trigger restart
kubectl delete pods -n pms --all
kubectl delete pods -n pms-local --all

# 2. Apply registry configuration
kubectl apply -f apps/infra/kubernetes/registry-config-daemonset.yaml

# 3. Wait for registry config to apply
kubectl wait --for=condition=ready pod -l name=registry-config -n kube-system --timeout=300s

# 4. Restart deployments
kubectl rollout restart deployment -n pms
kubectl rollout restart deployment -n pms-local

# 5. Check pod status
kubectl get pods -n pms
kubectl get pods -n pms-local
```

## Verification Steps

1. **Test registry access from host:**
   ```bash
   curl http://localhost:30500/v2/
   curl http://localhost:30500/v2/_catalog
   ```

2. **Test registry access from within cluster:**
   ```bash
   kubectl run test-pod --image=alpine --rm -it -- sh
   # Inside the pod:
   wget -qO- http://10.96.234.11:5000/v2/
   ```

3. **Check pod events:**
   ```bash
   kubectl describe pod <pod-name> -n pms
   ```

4. **Check image pull status:**
   ```bash
   kubectl get events -n pms --sort-by='.lastTimestamp'
   ```

## Alternative: Use Local Images

If registry issues persist, you can load images directly into Docker Desktop:

```bash
# Build images locally
docker build -t pms-backend:latest ./apps/backend
docker build -t pms-frontend:latest ./apps/frontend

# Update deployments to use local images without registry
# Change image references to:
# - pms-backend:latest
# - pms-frontend:latest
# And set imagePullPolicy: Never
```

## Prevention

To prevent this issue in the future:

1. Always configure insecure registries in Docker Desktop settings
2. Use consistent registry addresses across all configurations
3. Test registry connectivity before deploying applications
4. Consider using Docker Desktop's built-in registry features

## Troubleshooting

If issues persist:

1. **Check Docker Desktop logs:**
   - Docker Desktop → Troubleshoot → Get support

2. **Reset Kubernetes cluster:**
   - Docker Desktop → Settings → Kubernetes → Reset Kubernetes Cluster

3. **Verify network connectivity:**
   ```bash
   kubectl run network-test --image=alpine --rm -it -- sh
   # Test connectivity to registry
   ```

4. **Check containerd configuration:**
   ```bash
   kubectl exec -n kube-system <registry-config-pod> -- cat /host/etc/containerd/certs.d/10.96.234.11:5000/hosts.toml
   ```
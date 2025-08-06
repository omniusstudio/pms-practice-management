# Kubernetes Infrastructure for Mental Health PMS

This directory contains Kubernetes configurations and Helm charts for deploying the Mental Health Practice Management System (PMS) on Kubernetes clusters.

## Overview

The PMS application has been transitioned from AWS ECS to a Kubernetes-based infrastructure, providing:

- **Scalability**: Horizontal Pod Autoscaling (HPA) for automatic scaling
- **High Availability**: Pod Disruption Budgets and multi-replica deployments
- **Security**: Network policies, RBAC, and security contexts
- **HIPAA Compliance**: Encrypted communications and secure configurations
- **Blue/Green Deployments**: Zero-downtime deployment strategy
- **Monitoring Ready**: Structured for observability and monitoring

## Directory Structure

```
kubernetes/
├── README.md                    # This file
├── backend-deployment.yaml      # Backend service deployment
├── frontend-deployment.yaml     # Frontend service deployment
├── namespace.yaml              # Namespace and RBAC configuration
├── configmap.yaml              # Application configuration
├── ingress.yaml                # Ingress and TLS configuration
├── hpa.yaml                    # Horizontal Pod Autoscaler
├── network-policy.yaml         # Network security policies
├── pdb.yaml                    # Pod Disruption Budgets
└── helm/                       # Helm chart for advanced deployments
    └── pms/
        ├── Chart.yaml
        ├── values.yaml
        └── templates/
            ├── _helpers.tpl
            ├── backend-deployment.yaml
            └── configmap.yaml
```

## Prerequisites

### Required Tools

1. **kubectl** - Kubernetes command-line tool
   ```bash
   # macOS
   brew install kubectl
   
   # Linux
   curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
   ```

2. **Helm** (for Helm deployments)
   ```bash
   # macOS
   brew install helm
   
   # Linux
   curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
   ```

3. **AWS CLI** (for ECR access)
   ```bash
   # macOS
   brew install awscli
   
   # Linux
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   ```

### Cluster Requirements

- Kubernetes 1.24+
- NGINX Ingress Controller
- cert-manager (for TLS certificates)
- Metrics Server (for HPA)
- Container runtime with security context support

## Quick Start

### 1. Deploy with Raw Kubernetes Manifests

```bash
# Navigate to the kubernetes directory
cd apps/infra/kubernetes

# Set environment variables
export ECR_REGISTRY="your-account.dkr.ecr.us-west-2.amazonaws.com"
export VERSION="1.0.0"
export DOMAIN_NAME="pms.example.com"

# Deploy using the deployment script
../scripts/deploy-k8s.sh staging
```

### 2. Deploy with Helm

```bash
# Navigate to the Helm chart directory
cd apps/infra/kubernetes/helm

# Install dependencies
helm dependency update pms/

# Deploy to staging
helm install pms-staging pms/ \
  --namespace pms \
  --create-namespace \
  --values pms/values.yaml \
  --set app.environment=staging \
  --set app.domain=staging.pms.example.com

# Deploy to production
helm install pms-prod pms/ \
  --namespace pms-prod \
  --create-namespace \
  --values pms/values-prod.yaml \
  --set app.environment=production \
  --set app.domain=pms.example.com
```

## Configuration

### Environment Variables

The following environment variables need to be configured:

#### Required for Deployment Scripts
- `ECR_REGISTRY`: Your ECR registry URL
- `VERSION`: Application version/tag
- `DOMAIN_NAME`: Your domain name
- `AWS_REGION`: AWS region (default: us-west-2)

#### Application Configuration (ConfigMap)
- `AUTH0_DOMAIN`: Auth0 tenant domain
- `AUTH0_AUDIENCE`: Auth0 API audience
- `DATABASE_HOST`: PostgreSQL host
- `REDIS_HOST`: Redis host
- `AWS_S3_BUCKET`: S3 bucket for documents

#### Secrets (base64 encoded)
- `DATABASE_USER`: Database username
- `DATABASE_PASSWORD`: Database password
- `SECRET_KEY`: Application secret key
- `AUTH0_CLIENT_ID`: Auth0 client ID
- `AUTH0_CLIENT_SECRET`: Auth0 client secret
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key

### Customizing Configurations

1. **Update ConfigMap**: Edit `configmap.yaml` or Helm values
2. **Update Secrets**: Use base64 encoded values in secrets
3. **Scaling**: Modify replica counts in deployments or HPA settings
4. **Resources**: Adjust CPU/memory requests and limits
5. **Ingress**: Configure domain names and TLS certificates

## Deployment Strategies

### Blue/Green Deployment

The deployment script supports blue/green deployments:

```bash
# Deploy new version
./deploy-k8s.sh production 2.0.0

# Rollback if needed
./rollback-k8s.sh production
```

### Rolling Updates

Kubernetes deployments use rolling updates by default:
- `maxUnavailable: 1`
- `maxSurge: 1`

### Canary Deployments

For canary deployments, use Helm with multiple releases:

```bash
# Deploy canary version (10% traffic)
helm install pms-canary pms/ \
  --set replicaCount=1 \
  --set image.tag=2.0.0-canary

# Update ingress to split traffic
# (requires additional ingress configuration)
```

## Monitoring and Observability

### Health Checks

- **Liveness Probes**: `/health` endpoint on port 8000 (backend)
- **Readiness Probes**: Same as liveness probes
- **Startup Probes**: Configured for gradual startup

### Metrics

- **HPA Metrics**: CPU and memory utilization
- **Custom Metrics**: Can be added via Prometheus
- **Application Metrics**: Exposed via `/metrics` endpoint

### Logging

- **Structured Logging**: JSON format for better parsing
- **Log Levels**: Configurable via `LOG_LEVEL` environment variable
- **Log Aggregation**: Compatible with ELK, Fluentd, or similar

## Security

### Network Security

- **Network Policies**: Restrict pod-to-pod communication
- **Ingress Security**: TLS termination and security headers
- **Service Mesh Ready**: Compatible with Istio/Linkerd

### Pod Security

- **Security Contexts**: Non-root user, read-only filesystem
- **RBAC**: Least privilege access
- **Pod Security Standards**: Restricted profile compatible

### HIPAA Compliance

- **Encryption**: TLS for all communications
- **Access Controls**: RBAC and network policies
- **Audit Logging**: Kubernetes audit logs enabled
- **Data Protection**: Encrypted secrets and persistent volumes

## Troubleshooting

### Common Issues

1. **Pods not starting**:
   ```bash
   kubectl describe pod <pod-name> -n pms
   kubectl logs <pod-name> -n pms
   ```

2. **Service connectivity**:
   ```bash
   kubectl get svc -n pms
   kubectl describe svc <service-name> -n pms
   ```

3. **Ingress issues**:
   ```bash
   kubectl describe ingress pms-ingress -n pms
   kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
   ```

4. **Certificate issues**:
   ```bash
   kubectl describe certificate pms-tls-secret -n pms
   kubectl describe clusterissuer letsencrypt-prod
   ```

### Debug Commands

```bash
# Check pod status
kubectl get pods -n pms -o wide

# Check events
kubectl get events -n pms --sort-by='.lastTimestamp'

# Check resource usage
kubectl top pods -n pms
kubectl top nodes

# Check HPA status
kubectl get hpa -n pms

# Check network policies
kubectl get networkpolicy -n pms
```

## Maintenance

### Regular Tasks

1. **Update Dependencies**:
   ```bash
   helm dependency update pms/
   ```

2. **Backup Configurations**:
   ```bash
   kubectl get all -n pms -o yaml > pms-backup.yaml
   ```

3. **Certificate Renewal**:
   - Automatic with cert-manager
   - Monitor certificate expiration

4. **Security Updates**:
   - Regular image updates
   - Kubernetes cluster updates
   - Helm chart updates

### Scaling

```bash
# Manual scaling
kubectl scale deployment pms-backend --replicas=5 -n pms

# Update HPA limits
kubectl patch hpa pms-backend-hpa -n pms -p '{"spec":{"maxReplicas":20}}'
```

## Migration from ECS

The transition from AWS ECS to Kubernetes includes:

### Completed
- ✅ Kubernetes deployment manifests
- ✅ Helm charts for advanced deployments
- ✅ Blue/green deployment scripts
- ✅ Network policies and security configurations
- ✅ Horizontal Pod Autoscaling
- ✅ Pod Disruption Budgets
- ✅ Ingress with TLS termination
- ✅ ConfigMaps and Secrets management

### Next Steps
- [ ] Set up monitoring with Prometheus/Grafana
- [ ] Implement service mesh (optional)
- [ ] Set up backup and disaster recovery
- [ ] Configure log aggregation
- [ ] Set up CI/CD pipeline integration

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review Kubernetes and application logs
3. Consult the team documentation
4. Contact the DevOps team

## Contributing

When making changes to the Kubernetes configurations:

1. Test in development environment first
2. Update documentation
3. Follow security best practices
4. Validate HIPAA compliance requirements
5. Update Helm chart versions appropriately
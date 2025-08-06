# Mental Health PMS Infrastructure

This directory contains infrastructure configurations for the Mental Health Practice Management System (PMS), supporting both legacy AWS ECS deployments and the new Kubernetes-based infrastructure.

## Architecture Overview

The PMS infrastructure has been transitioned from AWS ECS to Kubernetes to provide better scalability, portability, and modern DevOps practices while maintaining HIPAA compliance.

### Current Architecture (Kubernetes)

```
┌─────────────────┐    ┌─────────────────┐
│   Internet      │    │   Load Balancer │
│   Gateway       │────│   (Ingress)     │
└─────────────────┘    └─────────────────┘
                                │
                       ┌────────┴────────┐
                       │                 │
              ┌─────────────┐    ┌─────────────┐
              │  Frontend   │    │   Backend   │
              │   (React)   │    │  (FastAPI)  │
              │   Pods      │    │    Pods     │
              └─────────────┘    └─────────────┘
                       │                 │
                       └────────┬────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
           ┌─────────────┐         ┌─────────────┐
           │ PostgreSQL  │         │    Redis    │
           │ (Database)  │         │   (Cache)   │
           └─────────────┘         └─────────────┘
```

### Legacy Architecture (AWS ECS)

The legacy ECS-based infrastructure is still available for reference and migration purposes.

## Directory Structure

```
infra/
├── README.md                   # This file
├── requirements.txt            # Python dependencies for infrastructure tools
├── kubernetes/                 # Kubernetes configurations (CURRENT)
│   ├── README.md              # Kubernetes-specific documentation
│   ├── CICD-INTEGRATION.md    # CI/CD integration documentation
│   ├── LOCAL-TESTING.md       # Local Kubernetes testing guide
│   ├── *.yaml                 # Kubernetes manifests
│   └── helm/                  # Helm charts
├── scripts/                   # Deployment and automation scripts
│   ├── deploy-k8s.sh         # Kubernetes deployment script
│   ├── rollback-k8s.sh       # Kubernetes rollback script
│   ├── cicd-k8s-deploy.sh    # CI/CD integration script
│   ├── setup-local-k8s.sh    # Local Kubernetes setup script
│   ├── validate-cicd-setup.sh # CI/CD validation script
│   └── deploy-blue-green.sh  # Legacy ECS deployment script
├── monitoring/                # Monitoring configurations
│   ├── alerts/               # Alert definitions
│   ├── dashboards/           # Grafana dashboards
│   └── *.yml                 # Monitoring stack configs
└── terraform/               # Legacy Terraform configurations
    └── main.tf              # AWS ECS infrastructure
```

## Quick Start

### Kubernetes Deployment (Recommended)

1. **Prerequisites**:
   ```bash
   # Install required tools
   brew install kubectl helm awscli
   
   # Configure AWS credentials
   aws configure
   
   # Configure kubectl for your cluster
   aws eks update-kubeconfig --region us-west-2 --name your-cluster
   ```

2. **Deploy Application**:
   ```bash
   cd kubernetes
   
   # Set environment variables
   export ECR_REGISTRY="your-account.dkr.ecr.us-west-2.amazonaws.com"
   export VERSION="1.0.0"
   export DOMAIN_NAME="pms.example.com"
   
   # Deploy to staging
   ../scripts/deploy-k8s.sh staging
   
   # Deploy to production
   ../scripts/deploy-k8s.sh production
   ```

3. **Using Helm** (Advanced):
   ```bash
   cd kubernetes/helm
   
   # Install with Helm
   helm install pms pms/ \
     --namespace pms \
     --create-namespace \
     --set app.environment=staging
   ```

### Legacy ECS Deployment

For reference or migration purposes:

```bash
# Deploy to ECS (legacy)
./scripts/deploy-blue-green.sh staging 1.0.0
```

## CI/CD Integration

Kubernetes is fully integrated into our CI/CD pipeline with automated deployments, health checks, and rollback capabilities.

### GitHub Actions Integration

The CI/CD pipeline includes:
- **Automated Staging Deployments**: Triggered on main branch commits
- **Manual Production Deployments**: Requires approval for production releases
- **Health Checks**: Comprehensive validation after deployment
- **Automatic Rollbacks**: Rollback on deployment failures

### Deployment Methods

#### 1. Via CI/CD Pipeline
Deployments are automatically triggered through GitHub Actions:
- **Staging**: Automatic deployment on code merge
- **Production**: Manual approval required

#### 2. Manual Deployment
Use the unified CI/CD deployment script:
```bash
# Deploy to staging with Helm
./scripts/cicd-k8s-deploy.sh --environment staging --method helm --version v1.2.3

# Deploy to production with kubectl (dry run first)
./scripts/cicd-k8s-deploy.sh -e production -m kubectl -v v1.2.3 --dry-run
./scripts/cicd-k8s-deploy.sh -e production -m kubectl -v v1.2.3
```

#### 3. Direct Kubernetes Workflow
Trigger the dedicated Kubernetes workflow manually:
- Go to GitHub Actions → "Deploy to Kubernetes"
- Select environment, deployment method, and version
- Monitor deployment progress and health checks

### Key Features
- **Environment Validation**: Pre-deployment configuration validation
- **Health Monitoring**: Automated application and infrastructure health checks
- **Deployment Reports**: Comprehensive deployment status and metrics
- **Security Scanning**: Automated vulnerability scanning in pipeline
- **HIPAA Compliance**: Security controls and audit logging

For detailed CI/CD integration information, see [CICD-INTEGRATION.md](kubernetes/CICD-INTEGRATION.md).

## Local Kubernetes Testing

Test your Kubernetes setup locally before deploying to staging or production environments.

### Quick Start

```bash
# Interactive setup (recommended)
./scripts/setup-local-k8s.sh

# Or specify options directly
./scripts/setup-local-k8s.sh --type minikube
./scripts/setup-local-k8s.sh --type docker-desktop --skip-build
./scripts/setup-local-k8s.sh --type kind --name test-cluster
```

### Supported Local Kubernetes Options

1. **Docker Desktop Kubernetes** (Recommended for macOS)
   - Easy setup and integration with Docker
   - Good performance on macOS
   - Built-in load balancer support

2. **Minikube** (Lightweight)
   - Fast startup and multiple driver options
   - Add-on ecosystem
   - Multi-node cluster support

3. **Kind** (Kubernetes in Docker)
   - Very lightweight and fast
   - Great for CI/CD testing
   - Multi-node cluster support

### Local Testing Features

- **Automated Setup**: One-command setup for any local Kubernetes option
- **Image Building**: Automatic Docker image building and loading
- **Local Configuration**: Environment-specific values for local testing
- **Health Checks**: Comprehensive validation after deployment
- **Easy Cleanup**: Simple cleanup commands
- **Port Forwarding**: Alternative access methods

### Manual Testing Commands

```bash
# Build and test locally
docker build -t pms-backend:local-test ./apps/backend
docker build -t pms-frontend:local-test ./apps/frontend

# Deploy with Helm
helm upgrade --install pms-local apps/infra/kubernetes/helm/pms/ \
  --namespace pms-local \
  --create-namespace \
  --values apps/infra/kubernetes/helm/pms/values-local.yaml

# Test deployment
kubectl get pods -n pms-local
kubectl port-forward -n pms-local service/pms-frontend 3000:3000
```

### Cleanup

```bash
# Clean up local resources
./scripts/setup-local-k8s.sh --cleanup

# Or manually
helm uninstall pms-local -n pms-local
kubectl delete namespace pms-local
```

For detailed local testing instructions, see [LOCAL-TESTING.md](kubernetes/LOCAL-TESTING.md).

## Infrastructure Components

### Kubernetes Infrastructure

#### Core Components
- **Namespace**: Isolated environment for PMS resources
- **Deployments**: Backend (FastAPI) and Frontend (React) services
- **Services**: Internal service discovery and load balancing
- **Ingress**: External traffic routing with TLS termination
- **ConfigMaps**: Non-sensitive configuration data
- **Secrets**: Sensitive configuration data (base64 encoded)

#### Scaling and Availability
- **Horizontal Pod Autoscaler (HPA)**: Automatic scaling based on CPU/memory
- **Pod Disruption Budgets (PDB)**: Maintain availability during updates
- **Rolling Updates**: Zero-downtime deployments
- **Blue/Green Deployments**: Advanced deployment strategy

#### Security
- **Network Policies**: Micro-segmentation and traffic control
- **RBAC**: Role-based access control
- **Security Contexts**: Pod-level security configurations
- **TLS Encryption**: End-to-end encryption

#### Dependencies
- **PostgreSQL**: Primary database (via Helm chart)
- **Redis**: Caching and session storage (via Helm chart)
- **NGINX Ingress**: Load balancing and SSL termination
- **cert-manager**: Automatic TLS certificate management

### Legacy ECS Infrastructure

#### Core Components
- **ECS Cluster**: Container orchestration
- **Application Load Balancer**: Traffic distribution
- **RDS PostgreSQL**: Managed database service
- **ElastiCache Redis**: Managed caching service
- **VPC**: Network isolation

## Configuration Management

### Environment-Specific Configurations

#### Development
- Single replica deployments
- Relaxed security policies
- Debug logging enabled
- Local development domains

#### Staging
- Production-like configuration
- Reduced resource allocation
- Staging domain names
- Full monitoring enabled

#### Production
- High availability configuration
- Full resource allocation
- Production domain names
- Enhanced security policies
- Comprehensive monitoring

### Configuration Files

#### Kubernetes
- `kubernetes/configmap.yaml`: Application configuration
- `kubernetes/helm/pms/values.yaml`: Helm default values
- `kubernetes/helm/pms/values-prod.yaml`: Production overrides

#### Legacy ECS
- `terraform/main.tf`: Infrastructure as code
- Environment-specific `.env` files

## Security and Compliance

### HIPAA Compliance

#### Technical Safeguards
- **Encryption in Transit**: TLS 1.2+ for all communications
- **Encryption at Rest**: Encrypted storage volumes and databases
- **Access Controls**: RBAC and network policies
- **Audit Logging**: Comprehensive logging and monitoring
- **Automatic Logoff**: Session timeout configurations
- **Data Integrity**: Checksums and validation

#### Administrative Safeguards
- **Access Management**: Role-based permissions
- **Workforce Training**: Security awareness
- **Incident Response**: Defined procedures
- **Risk Assessment**: Regular security reviews

#### Physical Safeguards
- **Cloud Provider**: AWS/GCP/Azure compliance
- **Data Centers**: SOC 2 Type II certified
- **Access Controls**: Multi-factor authentication

### Security Best Practices

1. **Container Security**:
   - Non-root user execution
   - Read-only root filesystem
   - Minimal base images
   - Regular security updates

2. **Network Security**:
   - Network segmentation
   - Ingress/egress controls
   - TLS everywhere
   - Regular security scans

3. **Secrets Management**:
   - Kubernetes secrets
   - External secret management (optional)
   - Rotation policies
   - Least privilege access

## Monitoring and Observability

### Available Monitoring

#### Application Metrics
- **Health Checks**: Liveness and readiness probes
- **Performance Metrics**: Response times, throughput
- **Error Rates**: Application and HTTP errors
- **Resource Usage**: CPU, memory, disk utilization

#### Infrastructure Metrics
- **Cluster Health**: Node status, pod distribution
- **Network Performance**: Latency, packet loss
- **Storage Metrics**: Disk usage, I/O performance
- **Security Events**: Access logs, policy violations

### Monitoring Stack

The `monitoring/` directory contains configurations for:
- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboards
- **Alertmanager**: Alert routing and management
- **Log Aggregation**: Centralized logging

## Deployment Strategies

### Blue/Green Deployment

1. **Deploy New Version**: Create new deployment alongside existing
2. **Health Checks**: Verify new version functionality
3. **Traffic Switch**: Route traffic to new version
4. **Cleanup**: Remove old version after verification

### Rolling Updates

1. **Gradual Replacement**: Replace pods one by one
2. **Health Verification**: Check each new pod
3. **Automatic Rollback**: Revert on failure
4. **Zero Downtime**: Maintain service availability

### Canary Deployment

1. **Limited Rollout**: Deploy to subset of users
2. **Metrics Monitoring**: Compare performance
3. **Gradual Increase**: Expand to more users
4. **Full Deployment**: Complete rollout or rollback

## Disaster Recovery

### Backup Strategy

#### Database Backups
- **Automated Backups**: Daily PostgreSQL dumps
- **Point-in-Time Recovery**: Transaction log backups
- **Cross-Region Replication**: Geographic redundancy
- **Retention Policy**: 30-day backup retention

#### Configuration Backups
- **Infrastructure as Code**: Version-controlled configurations
- **Kubernetes Manifests**: Stored in Git repository
- **Secrets Backup**: Encrypted external storage
- **Documentation**: Up-to-date runbooks

### Recovery Procedures

1. **Service Restoration**: Redeploy from known-good configurations
2. **Data Recovery**: Restore from latest backup
3. **Verification**: Comprehensive testing
4. **Communication**: Stakeholder notifications

## Migration Guide

### From ECS to Kubernetes

#### Completed Migration Steps
1. ✅ **Infrastructure Design**: Kubernetes architecture planning
2. ✅ **Configuration Migration**: Environment variables and secrets
3. ✅ **Deployment Scripts**: Automated deployment processes
4. ✅ **Security Implementation**: Network policies and RBAC
5. ✅ **Monitoring Setup**: Health checks and metrics
6. ✅ **Documentation**: Comprehensive guides and runbooks

#### Remaining Tasks
1. **Production Deployment**: Deploy to production Kubernetes cluster
2. **DNS Migration**: Update DNS records to point to new infrastructure
3. **ECS Decommission**: Safely shut down legacy ECS services
4. **Monitoring Integration**: Connect to existing monitoring systems
5. **Team Training**: Kubernetes operations training

## Troubleshooting

### Common Issues

#### Kubernetes
- **Pod Startup Issues**: Check logs and resource limits
- **Service Discovery**: Verify service and endpoint configurations
- **Ingress Problems**: Check ingress controller and DNS
- **Certificate Issues**: Verify cert-manager and domain validation

#### Legacy ECS
- **Task Definition Issues**: Check container configurations
- **Load Balancer Problems**: Verify target group health
- **Database Connectivity**: Check security groups and subnets
- **Service Discovery**: Verify ECS service configurations

### Debug Commands

```bash
# Kubernetes debugging
kubectl get pods -n pms
kubectl describe pod <pod-name> -n pms
kubectl logs <pod-name> -n pms
kubectl get events -n pms

# ECS debugging
aws ecs describe-services --cluster pms-cluster --services pms-backend
aws ecs describe-tasks --cluster pms-cluster --tasks <task-arn>
aws logs get-log-events --log-group-name /ecs/pms-backend
```

## Support and Maintenance

### Regular Maintenance Tasks

1. **Security Updates**: Monthly security patches
2. **Dependency Updates**: Quarterly dependency reviews
3. **Certificate Renewal**: Automated with monitoring
4. **Backup Verification**: Weekly backup testing
5. **Performance Review**: Monthly performance analysis

### Support Contacts

- **DevOps Team**: devops@yourorg.com
- **Security Team**: security@yourorg.com
- **On-Call**: Use PagerDuty for urgent issues
- **Documentation**: Internal wiki and runbooks

## Contributing

When making infrastructure changes:

1. **Development First**: Test in development environment
2. **Code Review**: Peer review all changes
3. **Documentation**: Update relevant documentation
4. **Security Review**: Validate security implications
5. **Rollback Plan**: Prepare rollback procedures
6. **Monitoring**: Verify monitoring and alerting

## License

This infrastructure configuration is proprietary to [Your Organization] and subject to internal security and compliance policies.
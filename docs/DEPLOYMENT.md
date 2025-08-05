# Deployment Guide - Mental Health PMS

This document describes the Continuous Deployment (CD) pipeline with blue/green deployment strategy for the Mental Health Practice Management System.

## Overview

The deployment pipeline implements:
- **Automated staging deployment** on main branch merges
- **Manual production deployment** with approval gates
- **Blue/green deployment strategy** for zero-downtime deployments
- **One-click rollback** functionality
- **Version tracking** with git SHA embedding
- **HIPAA-compliant** deployment practices

## Architecture

### Deployment Strategy: Blue/Green

The system uses blue/green deployment to ensure:
- Zero-downtime deployments
- Instant rollback capability
- Safe production deployments
- Health check validation before traffic switching

### Environments

| Environment | URL | Auto-Deploy | Approval Required |
|-------------|-----|-------------|-------------------|
| Staging | https://staging.pms.example.com | ✅ Yes (on main merge) | ❌ No |
| Production | https://pms.example.com | ❌ No | ✅ Yes (manual) |

## Deployment Workflows

### Automatic Staging Deployment

**Trigger:** Push to `main` branch

1. **Build Phase**
   - Run tests (unit, integration, security)
   - Build Docker images with version tags
   - Embed git SHA and version in `/healthz` endpoint
   - Upload artifacts to registry

2. **Deploy Phase**
   - Deploy to staging using blue/green strategy
   - Run health checks
   - Perform smoke tests
   - Update version tracking

### Manual Production Deployment

**Trigger:** Manual workflow dispatch or staging success

1. **Approval Gate**
   - Requires manual approval in GitHub Actions
   - Reviews staging deployment status
   - Validates readiness for production

2. **Production Deploy**
   - Store current version for rollback
   - Deploy using blue/green strategy
   - Extended health checks (60s)
   - Update production version tracking
   - Send deployment notifications

## Version Tracking

### Version Format
```
v{YYYYMMDD}-{git-sha}
```

Example: `v20240101-abc1234`

### Health Endpoints

#### Backend: `/healthz`
```json
{
  "status": "healthy",
  "service": "pms-backend",
  "version": "v20240101-abc1234",
  "gitSha": "abc1234",
  "environment": "production",
  "buildTime": "2024-01-01T12:00:00Z"
}
```

#### Frontend: `/health`
```json
{
  "status": "healthy",
  "service": "pms-frontend"
}
```

## Deployment Commands

### Using Makefile

```bash
# Check deployment status
make deployment-status

# Deploy to staging (local)
make deploy-staging

# Deploy to production (redirects to GitHub Actions)
make deploy-production

# Rollback staging
make rollback-staging

# Rollback production
make rollback-production
```

### Using Scripts Directly

```bash
# Deploy using blue/green strategy
./apps/infra/scripts/deploy-blue-green.sh staging v20240101-abc1234
./apps/infra/scripts/deploy-blue-green.sh production v20240101-abc1234

# One-click rollback
./apps/infra/scripts/rollback.sh staging
./apps/infra/scripts/rollback.sh production

# List available versions
./apps/infra/scripts/rollback.sh --list staging
```

### Using GitHub Actions

1. **Automatic Staging**
   - Push to `main` branch
   - Monitor at: https://github.com/your-org/pms/actions

2. **Manual Production**
   - Go to: https://github.com/your-org/pms/actions/workflows/cd.yml
   - Click "Run workflow"
   - Select environment: `production`
   - Click "Run workflow"

3. **Rollback**
   - Go to: https://github.com/your-org/pms/actions/workflows/cd.yml
   - Click "Run workflow"
   - Select environment: `staging` or `production`
   - Check "rollback" option
   - Click "Run workflow"

## Rollback Procedures

### Automatic Rollback Triggers

- Health check failures during deployment
- Service stability issues
- Smoke test failures

### Manual Rollback

1. **Immediate Rollback**
   ```bash
   ./apps/infra/scripts/rollback.sh production
   ```

2. **Specific Version Rollback**
   ```bash
   ./apps/infra/scripts/rollback.sh production v20231201-def5678
   ```

3. **Rollback Verification**
   - Health checks pass
   - Version endpoint shows correct version
   - Application functionality verified

### Rollback Testing

Rollback procedures are tested:
- ✅ **Once per release cycle** in staging
- ✅ **Documented and validated** process
- ✅ **Automated health verification**
- ✅ **Version tracking confirmation**

## Monitoring & Observability

### Deployment Dashboard

**URL:** https://grafana.pms.example.com/d/deployment-dashboard

**Metrics:**
- Deployment status and timeline
- Current versions by environment
- Health check status
- Response times and error rates
- Recent deployment logs

### Key Metrics

- **Deployment Frequency:** Tracked per environment
- **Lead Time:** From commit to production
- **Mean Time to Recovery (MTTR):** Rollback time
- **Change Failure Rate:** Failed deployments

### Alerts

- Deployment failures
- Health check failures
- Version mismatch between services
- Extended deployment times

## Security & Compliance

### HIPAA Compliance

- ✅ **No PHI in logs** or deployment artifacts
- ✅ **Encrypted data** at rest and in transit
- ✅ **Audit logging** for all deployments
- ✅ **Access controls** for production deployments
- ✅ **Secure secrets management**

### Security Measures

- Container image scanning
- Dependency vulnerability checks
- Infrastructure as Code (IaC)
- Least privilege access
- Encrypted artifact storage

## Troubleshooting

### Common Issues

#### Deployment Stuck
```bash
# Check ECS service status
aws ecs describe-services --cluster pms-production --services pms-backend-production

# Check task health
aws ecs describe-tasks --cluster pms-production --tasks <task-arn>
```

#### Health Check Failures
```bash
# Test health endpoints
curl -f https://pms.example.com/healthz
curl -f https://pms.example.com/health

# Check application logs
aws logs tail /ecs/pms-backend-production --follow
```

#### Version Mismatch
```bash
# Check current versions
curl -s https://pms.example.com/healthz | jq '.version'

# Verify deployment metadata
aws ssm get-parameter --name "/pms/production/deployment-metadata"
```

### Emergency Procedures

1. **Immediate Rollback**
   ```bash
   ./apps/infra/scripts/rollback.sh production
   ```

2. **Service Restart**
   ```bash
   aws ecs update-service --cluster pms-production --service pms-backend-production --force-new-deployment
   ```

3. **Traffic Diversion**
   - Update load balancer rules
   - Redirect to maintenance page
   - Scale down problematic services

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AWS_REGION` | AWS deployment region | ✅ |
| `ECR_REGISTRY` | Container registry URL | ✅ |
| `ENVIRONMENT` | Target environment | ✅ |
| `VERSION` | Deployment version | ✅ |
| `GIT_SHA` | Git commit SHA | ✅ |

### AWS Resources

- **ECS Clusters:** `pms-staging`, `pms-production`
- **ECR Repositories:** `pms-backend`, `pms-frontend`
- **SSM Parameters:** Version and deployment metadata
- **CloudWatch Logs:** Application and deployment logs

## Best Practices

### Deployment

1. **Always test in staging first**
2. **Monitor health checks during deployment**
3. **Verify version endpoints after deployment**
4. **Keep rollback procedures tested and ready**
5. **Document any manual intervention**

### Security

1. **Never log PHI in deployment processes**
2. **Use secure secrets management**
3. **Rotate deployment credentials regularly**
4. **Audit all production deployments**
5. **Follow least privilege principles**

### Monitoring

1. **Set up alerts for deployment failures**
2. **Monitor key metrics continuously**
3. **Review deployment logs regularly**
4. **Track deployment frequency and success rates**
5. **Maintain deployment dashboard visibility**

## Support

For deployment issues:
1. Check the deployment dashboard
2. Review GitHub Actions logs
3. Consult this documentation
4. Contact the DevOps team
5. Follow emergency procedures if critical
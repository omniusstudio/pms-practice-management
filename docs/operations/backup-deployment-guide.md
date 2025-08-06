# HIPAA-Compliant Backup System Deployment Guide

This guide provides step-by-step instructions for deploying the automated backup and restore system for the Mental Health PMS.

## Prerequisites

### 1. Infrastructure Requirements
- Kubernetes cluster with RBAC enabled
- PostgreSQL database (primary)
- S3-compatible storage bucket
- GPG key pair for encryption
- kubectl and helm CLI tools

### 2. Required Permissions
- Kubernetes cluster admin access
- S3 bucket read/write permissions
- Database backup privileges

## Deployment Steps

### Step 1: Prepare GPG Keys

```bash
# Generate GPG key pair for backup encryption
gpg --batch --generate-key <<EOF
Key-Type: RSA
Key-Length: 4096
Subkey-Type: RSA
Subkey-Length: 4096
Name-Real: PMS Backup System
Name-Email: backup@pms.example.com
Expire-Date: 2y
Passphrase: $(openssl rand -base64 32)
%commit
EOF

# Export keys
gpg --armor --export backup@pms.example.com > /tmp/backup-public.key
gpg --armor --export-secret-keys backup@pms.example.com > /tmp/backup-private.key

# Get key ID
export GPG_KEY_ID=$(gpg --list-secret-keys --keyid-format LONG backup@pms.example.com | grep sec | awk '{print $2}' | cut -d'/' -f2)
```

### Step 2: Create S3 Bucket

```bash
# Create S3 bucket with versioning and encryption
aws s3 mb s3://pms-production-backups --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket pms-production-backups \
  --versioning-configuration Status=Enabled

# Enable server-side encryption
aws s3api put-bucket-encryption \
  --bucket pms-production-backups \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Set lifecycle policy for automatic cleanup
aws s3api put-bucket-lifecycle-configuration \
  --bucket pms-production-backups \
  --lifecycle-configuration file://backup-lifecycle.json
```

### Step 3: Create Kubernetes Namespace and Secrets

```bash
# Create namespace
kubectl create namespace pms

# Create backup secrets
kubectl create secret generic pms-backup-secrets \
  --namespace=pms \
  --from-literal=postgres-user="${POSTGRES_USER}" \
  --from-literal=postgres-password="${POSTGRES_PASSWORD}" \
  --from-literal=aws-access-key-id="${AWS_ACCESS_KEY_ID}" \
  --from-literal=aws-secret-access-key="${AWS_SECRET_ACCESS_KEY}" \
  --from-literal=gpg-key-id="${GPG_KEY_ID}" \
  --from-file=gpg-private-key=/tmp/backup-private.key \
  --from-file=gpg-public-key=/tmp/backup-public.key

# Create backup configuration
kubectl create configmap pms-backup-config \
  --namespace=pms \
  --from-literal=s3-bucket="pms-production-backups" \
  --from-literal=aws-region="us-east-1" \
  --from-literal=retention-days="30" \
  --from-literal=backup-schedule="0 2 * * *" \
  --from-literal=monitoring-schedule="0 * * * *" \
  --from-literal=verification-schedule="0 3 * * 0"
```

### Step 4: Create Backup Scripts ConfigMap

```bash
# Create scripts configmap from the backup scripts directory
kubectl create configmap pms-backup-scripts \
  --namespace=pms \
  --from-file=/Volumes/external\ storage\ /PMS/scripts/backup/
```

### Step 5: Deploy Backup Infrastructure

```bash
# Apply backup configuration
kubectl apply -f /Volumes/external\ storage\ /PMS/apps/infra/kubernetes/backup-config.yaml

# Apply backup CronJobs
kubectl apply -f /Volumes/external\ storage\ /PMS/apps/infra/kubernetes/backup-cronjob.yaml
```

### Step 6: Verify Deployment

```bash
# Check CronJobs
kubectl get cronjobs -n pms

# Check ConfigMaps and Secrets
kubectl get configmaps,secrets -n pms | grep backup

# Check PVC
kubectl get pvc -n pms | grep backup-logs

# Check RBAC
kubectl get serviceaccount,role,rolebinding -n pms | grep backup
```

### Step 7: Test Backup System

```bash
# Manually trigger a backup job
kubectl create job --from=cronjob/pms-backup pms-backup-test -n pms

# Monitor job progress
kubectl logs -f job/pms-backup-test -n pms

# Check backup in S3
aws s3 ls s3://pms-production-backups/

# Run backup verification
kubectl create job --from=cronjob/pms-backup-verify pms-backup-verify-test -n pms

# Check verification results
kubectl logs -f job/pms-backup-verify-test -n pms
```

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|----------|
| `POSTGRES_HOST` | Database hostname | `localhost` |
| `POSTGRES_PORT` | Database port | `5432` |
| `POSTGRES_DB` | Database name | `pms` |
| `POSTGRES_USER` | Database user | From secret |
| `POSTGRES_PASSWORD` | Database password | From secret |
| `AWS_ACCESS_KEY_ID` | AWS access key | From secret |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | From secret |
| `S3_BUCKET` | S3 bucket name | From config |
| `AWS_REGION` | AWS region | From config |
| `BACKUP_RETENTION_DAYS` | Retention period | `30` |
| `BACKUP_GPG_KEY_ID` | GPG key ID | From secret |

### Backup Schedules

- **Daily Backup**: `0 2 * * *` (2 AM UTC)
- **Hourly Monitoring**: `0 * * * *` (Every hour)
- **Weekly Verification**: `0 3 * * 0` (Sunday 3 AM UTC)

## Monitoring and Alerting

### Prometheus Metrics

The backup system exposes the following metrics:

- `pms_backup_duration_seconds` - Backup duration
- `pms_backup_size_bytes` - Backup size
- `pms_backup_success_total` - Successful backups count
- `pms_backup_failure_total` - Failed backups count
- `pms_backup_age_seconds` - Age of latest backup

### Log Locations

- Backup logs: `/var/log/pms/backup_*.log`
- Monitoring logs: `/var/log/pms/monitoring_*.log`
- Verification logs: `/var/log/pms/verification_*.log`

### Alert Conditions

- Backup failure
- Backup older than 25 hours
- Backup size deviation > 50%
- S3 connectivity issues
- GPG key expiration warning

## Troubleshooting

### Common Issues

1. **GPG Key Issues**
   ```bash
   # Check GPG key status
   kubectl exec -it deployment/pms-backend -n pms -- gpg --list-keys
   
   # Import keys if missing
   kubectl exec -it deployment/pms-backend -n pms -- gpg --import /root/.gnupg/private.key
   ```

2. **S3 Connectivity**
   ```bash
   # Test S3 access
   kubectl exec -it deployment/pms-backend -n pms -- aws s3 ls s3://pms-production-backups/
   ```

3. **Database Connectivity**
   ```bash
   # Test database connection
   kubectl exec -it deployment/pms-backend -n pms -- pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT
   ```

4. **Permission Issues**
   ```bash
   # Check service account permissions
   kubectl auth can-i get pods --as=system:serviceaccount:pms:pms-backup -n pms
   ```

### Log Analysis

```bash
# View recent backup logs
kubectl exec -it deployment/pms-backend -n pms -- tail -f /var/log/pms/backup_$(date +%Y%m%d).log

# Check for errors
kubectl exec -it deployment/pms-backend -n pms -- grep -i error /var/log/pms/backup_*.log

# View monitoring reports
kubectl exec -it deployment/pms-backend -n pms -- cat /var/log/pms/backup_monitoring_$(date +%Y%m%d).json
```

## Security Considerations

### Encryption
- All backups are encrypted with GPG using 4096-bit RSA keys
- S3 server-side encryption (AES256) is enabled
- Database connections use SSL/TLS

### Access Control
- Kubernetes RBAC limits backup service account permissions
- S3 bucket policies restrict access to backup operations
- GPG keys are stored in Kubernetes secrets

### Compliance
- Backup retention follows HIPAA requirements
- Audit logs are maintained for all backup operations
- Data integrity verification is performed weekly

## Maintenance

### Regular Tasks

1. **Monthly**: Review backup reports and metrics
2. **Quarterly**: Test restore procedures
3. **Annually**: Rotate GPG keys and update documentation

### Key Rotation

```bash
# Generate new GPG key pair
# Export new keys
# Update Kubernetes secret
kubectl patch secret pms-backup-secrets -n pms --type='json' -p='[
  {"op": "replace", "path": "/data/gpg-private-key", "value": "'$(base64 -w 0 /tmp/new-private.key)'"},
  {"op": "replace", "path": "/data/gpg-public-key", "value": "'$(base64 -w 0 /tmp/new-public.key)'"},
  {"op": "replace", "path": "/data/gpg-key-id", "value": "'$(echo -n $NEW_GPG_KEY_ID | base64 -w 0)'"}
]'

# Restart backup pods to pick up new keys
kubectl rollout restart deployment/pms-backend -n pms
```

## Recovery Procedures

Refer to the [Restore Runbook](restore-runbook.md) for detailed recovery procedures including:

- Full database restore
- Point-in-time recovery (PITR)
- Partial data recovery
- Cross-region disaster recovery

## Support

For issues with the backup system:

1. Check the troubleshooting section above
2. Review logs and monitoring reports
3. Consult the restore runbook for recovery procedures
4. Contact the infrastructure team for assistance
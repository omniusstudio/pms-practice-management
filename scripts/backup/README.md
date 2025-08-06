# Mental Health PMS - HIPAA-Compliant Backup System

This directory contains the complete backup and restore system for the Mental Health Patient Management System (PMS), designed to meet HIPAA compliance requirements and ensure data integrity and availability.

## Overview

The backup system provides:

- **Automated Daily Backups**: PostgreSQL base backups with WAL archiving
- **Point-in-Time Recovery (PITR)**: Restore to any point in time within retention period
- **Encryption**: GPG encryption for data at rest and in transit
- **Cloud Storage**: Secure S3 storage with server-side encryption
- **Monitoring**: Continuous health monitoring with alerting
- **Verification**: Weekly backup integrity verification
- **Compliance**: Full HIPAA audit trail and documentation

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │  Backup System  │    │   S3 Storage    │
│   Primary DB    │───▶│                 │───▶│   Encrypted     │
│                 │    │  - pg_backup    │    │   Backups       │
└─────────────────┘    │  - monitoring   │    └─────────────────┘
                       │  - verification │
                       └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Kubernetes    │
                       │   CronJobs      │
                       │                 │
                       └─────────────────┘
```

## Components

### Core Scripts

1. **`pg_backup.sh`** - Main backup script
   - Creates PostgreSQL base backups using `pg_basebackup`
   - Implements WAL archiving for PITR capability
   - Encrypts backups with GPG
   - Uploads to S3 with server-side encryption
   - Manages retention policies
   - Generates backup reports

2. **`restore.sh`** - Database restore script
   - Supports full database restore
   - Implements point-in-time recovery (PITR)
   - Downloads and decrypts S3 backups
   - Validates restore integrity
   - Generates restore reports

3. **`verify_backup.sh`** - Backup verification script
   - Tests backup integrity
   - Verifies encryption
   - Validates PostgreSQL backup structure
   - Performs test restores
   - Generates verification reports

4. **`monitor_backups.sh`** - Monitoring and alerting script
   - Monitors backup health and freshness
   - Checks S3 connectivity and permissions
   - Sends alerts via webhooks/Slack
   - Exports Prometheus metrics
   - Generates monitoring reports

### Kubernetes Integration

- **CronJobs**: Automated scheduling of backup operations
- **ConfigMaps**: Configuration management
- **Secrets**: Secure credential storage
- **RBAC**: Role-based access control
- **PVC**: Persistent log storage

### Documentation

- **Backup Policy**: HIPAA compliance requirements and procedures
- **Restore Runbook**: Step-by-step recovery procedures
- **Deployment Guide**: Installation and configuration instructions
- **Test Suite**: Comprehensive testing framework

## Quick Start

### Prerequisites

- Kubernetes cluster with PostgreSQL database
- S3-compatible storage bucket
- GPG key pair for encryption
- AWS credentials with S3 access

### Installation

1. **Deploy using Helm** (Recommended):
   ```bash
   helm upgrade --install pms ./apps/infra/kubernetes/helm/pms \
     --set backup.enabled=true \
     --set backup.s3.bucket=your-backup-bucket \
     --namespace pms
   ```

2. **Manual Deployment**:
   ```bash
   # Follow the detailed deployment guide
   cat docs/operations/backup-deployment-guide.md
   ```

### Verification

```bash
# Check backup system status
kubectl get cronjobs -n pms

# Trigger manual backup
kubectl create job --from=cronjob/pms-backup pms-backup-test -n pms

# Monitor backup progress
kubectl logs -f job/pms-backup-test -n pms

# Verify backup in S3
aws s3 ls s3://your-backup-bucket/
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `POSTGRES_HOST` | Database hostname | Yes |
| `POSTGRES_PORT` | Database port | Yes |
| `POSTGRES_DB` | Database name | Yes |
| `POSTGRES_USER` | Database user | Yes |
| `POSTGRES_PASSWORD` | Database password | Yes |
| `S3_BUCKET` | S3 bucket name | Yes |
| `AWS_REGION` | AWS region | Yes |
| `AWS_ACCESS_KEY_ID` | AWS access key | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Yes |
| `BACKUP_GPG_KEY_ID` | GPG key ID | Yes |
| `BACKUP_RETENTION_DAYS` | Retention period | No (30) |
| `ALERT_WEBHOOK_URL` | Alert webhook URL | No |
| `SLACK_WEBHOOK_URL` | Slack webhook URL | No |

### Backup Schedules

- **Daily Backup**: 2:00 AM UTC (`0 2 * * *`)
- **Hourly Monitoring**: Every hour (`0 * * * *`)
- **Weekly Verification**: Sunday 3:00 AM UTC (`0 3 * * 0`)

### Retention Policy

- **Local backups**: 7 days
- **S3 backups**: 30 days (configurable)
- **WAL files**: 7 days
- **Log files**: 90 days

## Security Features

### Encryption

- **GPG Encryption**: 4096-bit RSA keys for backup files
- **S3 Server-Side Encryption**: AES256 encryption at rest
- **TLS/SSL**: Encrypted data transmission
- **Key Management**: Secure key storage in Kubernetes secrets

### Access Control

- **Kubernetes RBAC**: Minimal required permissions
- **S3 Bucket Policies**: Restricted access to backup operations
- **Network Policies**: Isolated backup network traffic
- **Audit Logging**: Complete audit trail of all operations

### Compliance

- **HIPAA Requirements**: Meets all HIPAA backup and recovery requirements
- **Data Integrity**: Checksums and verification for all backups
- **Audit Trail**: Comprehensive logging and reporting
- **Retention Management**: Automated cleanup per compliance requirements

## Monitoring and Alerting

### Metrics

The system exports Prometheus metrics:

```
# Backup duration
pms_backup_duration_seconds{type="full|incremental"}

# Backup size
pms_backup_size_bytes{type="full|incremental"}

# Success/failure counters
pms_backup_success_total
pms_backup_failure_total

# Backup age
pms_backup_age_seconds

# Verification status
pms_backup_verification_success_total
pms_backup_verification_failure_total
```

### Alerts

Configured alerts for:

- Backup failures
- Backup age > 25 hours
- Backup size deviation > 50%
- S3 connectivity issues
- GPG key expiration warnings
- Verification failures

### Dashboards

Grafana dashboards available for:

- Backup system overview
- Backup performance trends
- Storage utilization
- Error rates and alerts

## Testing

### Automated Tests

```bash
# Run comprehensive test suite
python3 tests/backup/test_backup_restore.py

# Run specific test categories
python3 -m pytest tests/backup/ -k "test_backup_creation"
python3 -m pytest tests/backup/ -k "test_full_restore"
python3 -m pytest tests/backup/ -k "test_pitr"
```

### Manual Testing

```bash
# Test backup creation
./scripts/backup/pg_backup.sh

# Test backup verification
./scripts/backup/verify_backup.sh

# Test monitoring
./scripts/backup/monitor_backups.sh

# Test restore (use with caution)
./scripts/backup/restore.sh --backup-date=2024-01-15
```

## Troubleshooting

### Common Issues

1. **Backup Failures**
   - Check database connectivity
   - Verify S3 permissions
   - Check disk space
   - Review GPG key status

2. **Restore Issues**
   - Verify backup file integrity
   - Check target database permissions
   - Ensure sufficient disk space
   - Validate recovery target time

3. **Monitoring Alerts**
   - Check network connectivity
   - Verify webhook URLs
   - Review alert thresholds
   - Check Prometheus metrics

### Log Analysis

```bash
# View backup logs
kubectl exec -it deployment/pms-backend -n pms -- \
  tail -f /var/log/pms/backup_$(date +%Y%m%d).log

# Check for errors
kubectl exec -it deployment/pms-backend -n pms -- \
  grep -i error /var/log/pms/backup_*.log

# View JSON reports
kubectl exec -it deployment/pms-backend -n pms -- \
  cat /var/log/pms/backup_report_$(date +%Y%m%d).json
```

### Debug Mode

```bash
# Enable debug logging
export DEBUG=1
./scripts/backup/pg_backup.sh

# Dry run mode
export DRY_RUN=1
./scripts/backup/pg_backup.sh
```

## Recovery Procedures

### Full Database Restore

```bash
# Restore from latest backup
./scripts/backup/restore.sh --type=full

# Restore from specific backup
./scripts/backup/restore.sh --type=full --backup-date=2024-01-15
```

### Point-in-Time Recovery

```bash
# Restore to specific timestamp
./scripts/backup/restore.sh --type=pitr --recovery-target="2024-01-15 14:30:00"

# Restore to transaction ID
./scripts/backup/restore.sh --type=pitr --recovery-target-xid=12345
```

### Disaster Recovery

```bash
# Cross-region restore
./scripts/backup/restore.sh --type=full --s3-region=us-west-2

# Restore to different database
./scripts/backup/restore.sh --type=full --target-db=pms_recovery
```

## Maintenance

### Regular Tasks

- **Daily**: Monitor backup reports and alerts
- **Weekly**: Review verification reports
- **Monthly**: Analyze backup performance metrics
- **Quarterly**: Test restore procedures
- **Annually**: Rotate encryption keys

### Key Rotation

```bash
# Generate new GPG key pair
gpg --batch --generate-key backup-key-config.txt

# Update Kubernetes secrets
kubectl patch secret pms-backup-secrets -n pms --patch='{
  "data": {
    "gpg-private-key": "'$(base64 -w 0 new-private.key)'",
    "gpg-public-key": "'$(base64 -w 0 new-public.key)'"
  }
}'
```

### Performance Tuning

```bash
# Adjust backup compression
export BACKUP_COMPRESSION_LEVEL=6

# Tune parallel jobs
export BACKUP_PARALLEL_JOBS=4

# Optimize S3 upload
export S3_MULTIPART_THRESHOLD=64MB
```

## Support

For support and troubleshooting:

1. **Documentation**: Review all documentation in `docs/operations/`
2. **Logs**: Check system logs and backup reports
3. **Monitoring**: Review Grafana dashboards and Prometheus alerts
4. **Testing**: Run the test suite to identify issues
5. **Community**: Consult the project wiki and issue tracker

## Contributing

When contributing to the backup system:

1. **Testing**: Run the full test suite
2. **Documentation**: Update relevant documentation
3. **Security**: Follow security best practices
4. **Compliance**: Ensure HIPAA compliance is maintained
5. **Code Review**: Submit pull requests for review

## License

This backup system is part of the Mental Health PMS project and follows the same licensing terms.

---

**⚠️ Important Security Notice**

This backup system handles sensitive healthcare data. Always:
- Follow HIPAA compliance requirements
- Use strong encryption for all data
- Regularly test restore procedures
- Monitor system health continuously
- Keep documentation up to date
- Report security issues immediately
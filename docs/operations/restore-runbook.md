# Mental Health PMS Restore Runbook

## Overview

This runbook provides detailed step-by-step procedures for restoring the Mental Health Practice Management System database from backups. It covers various recovery scenarios and ensures HIPAA-compliant restoration processes.

## Quick Reference

| Recovery Type | RTO | RPO | Use Case |
|---------------|-----|-----|----------|
| Full Restore | 4 hours | 1 hour | Complete database loss |
| Point-in-Time Recovery | 6 hours | Any point | Data corruption at specific time |
| Partial Recovery | 2 hours | 1 hour | Specific table corruption |
| Cross-Region Recovery | 8 hours | 24 hours | Regional disaster |

## Prerequisites

### Required Access
- [ ] Kubernetes cluster access with `pms-backup` service account
- [ ] AWS S3 access to backup bucket
- [ ] GPG private key for backup decryption
- [ ] Database administrator privileges
- [ ] Incident response team notification access

### Required Tools
- [ ] `kubectl` configured for target cluster
- [ ] `aws` CLI configured with appropriate credentials
- [ ] `gpg` with backup encryption keys
- [ ] `psql` and PostgreSQL client tools
- [ ] Backup scripts from `/scripts/backup/`

### Environment Variables
```bash
export BACKUP_S3_BUCKET="pms-production-backups"
export BACKUP_ENCRYPTION_KEY_ID="pms-backup-key"
export AWS_DEFAULT_REGION="us-east-1"
export PGHOST="localhost"
export PGPORT="5432"
export PGDATABASE="pms_production"
export PGUSER="pms_admin"
```

## Recovery Scenarios

### Scenario 1: Full Database Restore

**When to use**: Complete database corruption, hardware failure, or accidental database drop.

#### Step 1: Assessment and Preparation (15 minutes)

1. **Assess the situation**
   ```bash
   # Check database status
   kubectl get pods -n pms -l app=pms-database
   
   # Check recent backup availability
   aws s3 ls s3://$BACKUP_S3_BUCKET/backups/ --recursive | tail -5
   ```

2. **Notify stakeholders**
   ```bash
   # Send incident notification
   curl -X POST $INCIDENT_WEBHOOK_URL \
     -H "Content-Type: application/json" \
     -d '{
       "incident_type": "database_restore",
       "severity": "critical",
       "message": "Initiating full database restore",
       "estimated_duration": "4 hours"
     }'
   ```

3. **Prepare recovery environment**
   ```bash
   # Create recovery namespace if needed
   kubectl create namespace pms-recovery --dry-run=client -o yaml | kubectl apply -f -
   
   # Scale down application pods
   kubectl scale deployment pms-backend -n pms --replicas=0
   kubectl scale deployment pms-frontend -n pms --replicas=0
   ```

#### Step 2: Backup Retrieval (30 minutes)

1. **Identify latest backup**
   ```bash
   LATEST_BACKUP=$(aws s3 ls s3://$BACKUP_S3_BUCKET/backups/ --recursive | \
     grep '.gpg$' | sort -k1,2 | tail -1 | awk '{print $4}')
   
   echo "Latest backup: $LATEST_BACKUP"
   ```

2. **Download and verify backup**
   ```bash
   # Create temporary directory
   RESTORE_DIR="/tmp/pms_restore_$(date +%Y%m%d_%H%M%S)"
   mkdir -p $RESTORE_DIR
   cd $RESTORE_DIR
   
   # Download backup
   aws s3 cp s3://$BACKUP_S3_BUCKET/$LATEST_BACKUP ./backup.tar.gz.gpg
   
   # Verify download
   EXPECTED_SIZE=$(aws s3 ls s3://$BACKUP_S3_BUCKET/$LATEST_BACKUP | awk '{print $3}')
   ACTUAL_SIZE=$(stat -c%s backup.tar.gz.gpg)
   
   if [ "$EXPECTED_SIZE" != "$ACTUAL_SIZE" ]; then
     echo "ERROR: Download size mismatch"
     exit 1
   fi
   ```

3. **Decrypt and extract backup**
   ```bash
   # Decrypt backup
   gpg --decrypt backup.tar.gz.gpg > backup.tar.gz
   
   # Verify decryption
   if ! file backup.tar.gz | grep -q "gzip compressed"; then
     echo "ERROR: Decryption failed"
     exit 1
   fi
   
   # Extract backup
   tar -xzf backup.tar.gz
   ```

#### Step 3: Database Restoration (2 hours)

1. **Stop existing database**
   ```bash
   # Scale down database pod
   kubectl scale statefulset pms-database -n pms --replicas=0
   
   # Wait for pod termination
   kubectl wait --for=delete pod -l app=pms-database -n pms --timeout=300s
   ```

2. **Prepare data directory**
   ```bash
   # Create recovery pod with database volume
   cat <<EOF | kubectl apply -f -
   apiVersion: v1
   kind: Pod
   metadata:
     name: pms-db-recovery
     namespace: pms
   spec:
     containers:
     - name: postgres
       image: postgres:15
       command: ["sleep", "3600"]
       volumeMounts:
       - name: postgres-data
         mountPath: /var/lib/postgresql/data
     volumes:
     - name: postgres-data
       persistentVolumeClaim:
         claimName: pms-database-data
   EOF
   
   # Wait for pod to be ready
   kubectl wait --for=condition=Ready pod/pms-db-recovery -n pms --timeout=300s
   
   # Clear existing data
   kubectl exec -n pms pms-db-recovery -- rm -rf /var/lib/postgresql/data/*
   ```

3. **Restore database files**
   ```bash
   # Copy backup files to pod
   kubectl cp $RESTORE_DIR/base.tar pms/pms-db-recovery:/tmp/base.tar
   
   # Extract base backup
   kubectl exec -n pms pms-db-recovery -- tar -xf /tmp/base.tar -C /var/lib/postgresql/data
   
   # Set proper permissions
   kubectl exec -n pms pms-db-recovery -- chown -R postgres:postgres /var/lib/postgresql/data
   kubectl exec -n pms pms-db-recovery -- chmod 700 /var/lib/postgresql/data
   ```

4. **Configure recovery**
   ```bash
   # Create recovery configuration
   kubectl exec -n pms pms-db-recovery -- tee /var/lib/postgresql/data/postgresql.conf <<EOF
   # Recovery configuration
   restore_command = 'cp /var/lib/postgresql/wal_archive/%f %p'
   recovery_target_timeline = 'latest'
   EOF
   
   # Create recovery signal file
   kubectl exec -n pms pms-db-recovery -- touch /var/lib/postgresql/data/recovery.signal
   ```

#### Step 4: Database Startup and Validation (1 hour)

1. **Start PostgreSQL**
   ```bash
   # Delete recovery pod
   kubectl delete pod pms-db-recovery -n pms
   
   # Scale up database
   kubectl scale statefulset pms-database -n pms --replicas=1
   
   # Wait for database to be ready
   kubectl wait --for=condition=Ready pod -l app=pms-database -n pms --timeout=600s
   ```

2. **Verify database health**
   ```bash
   # Check PostgreSQL status
   kubectl exec -n pms -c postgres pms-database-0 -- pg_isready
   
   # Connect and verify data
   kubectl exec -n pms -c postgres pms-database-0 -- psql -U $PGUSER -d $PGDATABASE -c "
     SELECT 
       schemaname,
       tablename,
       n_tup_ins as inserts,
       n_tup_upd as updates,
       n_tup_del as deletes
     FROM pg_stat_user_tables 
     ORDER BY schemaname, tablename;
   "
   ```

3. **Run smoke tests**
   ```bash
   # Execute smoke test script
   kubectl create job pms-smoke-test -n pms --image=postgres:15 -- /bin/bash -c "
     # Test database connectivity
     pg_isready -h pms-database -p 5432 -U $PGUSER
     
     # Test critical tables
     psql -h pms-database -U $PGUSER -d $PGDATABASE -c 'SELECT COUNT(*) FROM patients;'
     psql -h pms-database -U $PGUSER -d $PGDATABASE -c 'SELECT COUNT(*) FROM appointments;'
     psql -h pms-database -U $PGUSER -d $PGDATABASE -c 'SELECT COUNT(*) FROM audit_log;'
     
     # Test recent data
     psql -h pms-database -U $PGUSER -d $PGDATABASE -c "
       SELECT COUNT(*) FROM audit_log 
       WHERE created_at > NOW() - INTERVAL '24 hours';
     "
   "
   
   # Wait for smoke test completion
   kubectl wait --for=condition=Complete job/pms-smoke-test -n pms --timeout=300s
   
   # Check smoke test results
   kubectl logs job/pms-smoke-test -n pms
   ```

#### Step 5: Application Restart and Monitoring (30 minutes)

1. **Restart application services**
   ```bash
   # Scale up backend
   kubectl scale deployment pms-backend -n pms --replicas=3
   kubectl wait --for=condition=Available deployment/pms-backend -n pms --timeout=300s
   
   # Scale up frontend
   kubectl scale deployment pms-frontend -n pms --replicas=2
   kubectl wait --for=condition=Available deployment/pms-frontend -n pms --timeout=300s
   ```

2. **Verify application health**
   ```bash
   # Check application endpoints
   kubectl port-forward -n pms service/pms-backend 8080:8000 &
   sleep 5
   
   # Test health endpoint
   curl -f http://localhost:8080/health || echo "Health check failed"
   
   # Test database connectivity
   curl -f http://localhost:8080/api/v1/status || echo "API check failed"
   
   # Stop port-forward
   pkill -f "kubectl port-forward"
   ```

3. **Monitor system stability**
   ```bash
   # Monitor pods for 10 minutes
   for i in {1..10}; do
     echo "=== Minute $i ==="
     kubectl get pods -n pms
     kubectl top pods -n pms
     sleep 60
   done
   ```

#### Step 6: Cleanup and Documentation (15 minutes)

1. **Clean up temporary files**
   ```bash
   # Remove local restore directory
   rm -rf $RESTORE_DIR
   
   # Clean up Kubernetes resources
   kubectl delete job pms-smoke-test -n pms
   ```

2. **Document recovery**
   ```bash
   # Generate recovery report
   cat > /tmp/recovery_report_$(date +%Y%m%d_%H%M%S).json <<EOF
   {
     "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
     "recovery_type": "full_restore",
     "backup_used": "$LATEST_BACKUP",
     "duration_minutes": $(($(date +%s) - $START_TIME) / 60),
     "status": "completed",
     "smoke_tests": "passed",
     "notes": "Full database restore completed successfully"
   }
   EOF
   ```

3. **Send completion notification**
   ```bash
   curl -X POST $INCIDENT_WEBHOOK_URL \
     -H "Content-Type: application/json" \
     -d '{
       "incident_type": "database_restore",
       "status": "resolved",
       "message": "Full database restore completed successfully",
       "duration": "'$(($(date +%s) - $START_TIME))' seconds"
     }'
   ```

### Scenario 2: Point-in-Time Recovery (PITR)

**When to use**: Data corruption occurred at a specific time, need to recover to a point before corruption.

#### Step 1: Determine Recovery Target

1. **Identify corruption time**
   ```bash
   # Check audit logs for suspicious activity
   kubectl exec -n pms -c postgres pms-database-0 -- psql -U $PGUSER -d $PGDATABASE -c "
     SELECT 
       timestamp,
       user_id,
       action,
       table_name,
       record_id
     FROM audit_log 
     WHERE timestamp > '2024-01-01 10:00:00'
     ORDER BY timestamp DESC
     LIMIT 50;
   "
   
   # Set recovery target (example: 2024-01-01 09:30:00)
   RECOVERY_TARGET="2024-01-01 09:30:00"
   ```

#### Step 2: PITR Restoration Process

1. **Follow Steps 1-3 from Full Restore** (with modifications)

2. **Configure PITR recovery**
   ```bash
   # Create recovery configuration with target time
   kubectl exec -n pms pms-db-recovery -- tee /var/lib/postgresql/data/postgresql.conf <<EOF
   # PITR Recovery configuration
   restore_command = 'cp /var/lib/postgresql/wal_archive/%f %p'
   recovery_target_time = '$RECOVERY_TARGET'
   recovery_target_timeline = 'latest'
   recovery_target_action = 'promote'
   EOF
   
   # Create recovery signal file
   kubectl exec -n pms pms-db-recovery -- touch /var/lib/postgresql/data/recovery.signal
   ```

3. **Monitor recovery progress**
   ```bash
   # Watch PostgreSQL logs during recovery
   kubectl logs -n pms -c postgres pms-database-0 -f
   
   # Look for recovery completion message:
   # "redo done at [LSN] system usage: ..."
   # "database system is ready to accept connections"
   ```

4. **Verify recovery target**
   ```bash
   # Check recovery target was reached
   kubectl exec -n pms -c postgres pms-database-0 -- psql -U $PGUSER -d $PGDATABASE -c "
     SELECT pg_last_wal_replay_lsn(), 
            pg_last_xact_replay_timestamp();
   "
   
   # Verify data state at recovery point
   kubectl exec -n pms -c postgres pms-database-0 -- psql -U $PGUSER -d $PGDATABASE -c "
     SELECT COUNT(*) FROM audit_log 
     WHERE timestamp <= '$RECOVERY_TARGET';
   "
   ```

### Scenario 3: Partial Recovery

**When to use**: Specific table corruption, accidental data deletion from specific tables.

#### Step 1: Identify Affected Data

1. **Assess damage scope**
   ```bash
   # Identify affected tables
   AFFECTED_TABLES="patients,appointments"
   
   # Check current state
   kubectl exec -n pms -c postgres pms-database-0 -- psql -U $PGUSER -d $PGDATABASE -c "
     SELECT 
       schemaname,
       tablename,
       n_tup_ins,
       n_tup_upd,
       n_tup_del,
       n_live_tup,
       n_dead_tup
     FROM pg_stat_user_tables 
     WHERE tablename IN ('patients', 'appointments');
   "
   ```

#### Step 2: Restore to Temporary Database

1. **Create temporary database**
   ```bash
   # Create temporary database for partial restore
   kubectl exec -n pms -c postgres pms-database-0 -- psql -U $PGUSER -d postgres -c "
     CREATE DATABASE pms_temp_restore;
   "
   ```

2. **Restore backup to temporary database**
   ```bash
   # Follow backup retrieval steps from Scenario 1
   # Then restore to temporary database
   kubectl exec -n pms -c postgres pms-database-0 -- pg_restore \
     -U $PGUSER -d pms_temp_restore -v /tmp/backup.dump
   ```

#### Step 3: Extract and Restore Specific Data

1. **Export affected tables from backup**
   ```bash
   # Export specific tables
   kubectl exec -n pms -c postgres pms-database-0 -- pg_dump \
     -U $PGUSER -d pms_temp_restore \
     -t patients -t appointments \
     --data-only --inserts > /tmp/partial_restore.sql
   ```

2. **Restore specific data**
   ```bash
   # Backup current data (if needed)
   kubectl exec -n pms -c postgres pms-database-0 -- pg_dump \
     -U $PGUSER -d $PGDATABASE \
     -t patients -t appointments \
     --data-only > /tmp/current_data_backup.sql
   
   # Truncate affected tables (if full replacement)
   kubectl exec -n pms -c postgres pms-database-0 -- psql -U $PGUSER -d $PGDATABASE -c "
     TRUNCATE TABLE patients, appointments CASCADE;
   "
   
   # Restore data
   kubectl exec -n pms -c postgres pms-database-0 -- psql -U $PGUSER -d $PGDATABASE \
     -f /tmp/partial_restore.sql
   ```

3. **Verify partial restore**
   ```bash
   # Check record counts
   kubectl exec -n pms -c postgres pms-database-0 -- psql -U $PGUSER -d $PGDATABASE -c "
     SELECT 
       'patients' as table_name, COUNT(*) as record_count 
     FROM patients
     UNION ALL
     SELECT 
       'appointments' as table_name, COUNT(*) as record_count 
     FROM appointments;
   "
   ```

### Scenario 4: Cross-Region Recovery

**When to use**: Primary region failure, disaster recovery activation.

#### Step 1: Activate Secondary Region

1. **Switch to secondary region**
   ```bash
   # Update AWS region
   export AWS_DEFAULT_REGION="us-west-2"
   export BACKUP_S3_BUCKET="pms-dr-backups"
   
   # Configure kubectl for DR cluster
   kubectl config use-context pms-dr-cluster
   ```

2. **Verify DR environment**
   ```bash
   # Check DR cluster status
   kubectl get nodes
   kubectl get namespaces
   
   # Check backup availability
   aws s3 ls s3://$BACKUP_S3_BUCKET/backups/ --recursive | tail -5
   ```

#### Step 2: Deploy Application Stack

1. **Deploy database**
   ```bash
   # Deploy PostgreSQL to DR cluster
   helm upgrade --install pms-database ./helm/postgresql \
     --namespace pms --create-namespace \
     --values values-dr.yaml
   
   # Wait for database to be ready
   kubectl wait --for=condition=Ready pod -l app=pms-database -n pms --timeout=600s
   ```

2. **Restore database** (follow Scenario 1 steps)

3. **Deploy application services**
   ```bash
   # Deploy backend
   helm upgrade --install pms-backend ./helm/backend \
     --namespace pms \
     --values values-dr.yaml
   
   # Deploy frontend
   helm upgrade --install pms-frontend ./helm/frontend \
     --namespace pms \
     --values values-dr.yaml
   ```

#### Step 3: Update DNS and Load Balancers

1. **Update DNS records**
   ```bash
   # Update Route53 records to point to DR region
   aws route53 change-resource-record-sets \
     --hosted-zone-id Z1234567890 \
     --change-batch file://dns-failover.json
   ```

2. **Verify external access**
   ```bash
   # Test external endpoints
   curl -f https://pms.example.com/health
   curl -f https://api.pms.example.com/v1/status
   ```

## Troubleshooting

### Common Issues

#### Issue: Backup Download Fails
```bash
# Check S3 permissions
aws s3 ls s3://$BACKUP_S3_BUCKET/

# Verify AWS credentials
aws sts get-caller-identity

# Check network connectivity
curl -I https://s3.amazonaws.com
```

#### Issue: GPG Decryption Fails
```bash
# List available keys
gpg --list-secret-keys

# Import key if missing
gpg --import /path/to/private.key

# Test decryption with verbose output
gpg --decrypt --verbose backup.tar.gz.gpg
```

#### Issue: PostgreSQL Won't Start
```bash
# Check PostgreSQL logs
kubectl logs -n pms -c postgres pms-database-0

# Check data directory permissions
kubectl exec -n pms -c postgres pms-database-0 -- ls -la /var/lib/postgresql/data

# Verify configuration files
kubectl exec -n pms -c postgres pms-database-0 -- cat /var/lib/postgresql/data/postgresql.conf
```

#### Issue: Recovery Takes Too Long
```bash
# Monitor recovery progress
kubectl exec -n pms -c postgres pms-database-0 -- psql -U $PGUSER -d $PGDATABASE -c "
  SELECT 
    pg_last_wal_replay_lsn(),
    pg_last_xact_replay_timestamp(),
    EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) as lag_seconds;
"

# Check WAL replay rate
kubectl logs -n pms -c postgres pms-database-0 | grep "redo"
```

### Emergency Contacts

| Role | Contact | Phone | Email |
|------|---------|-------|-------|
| Database Administrator | John Doe | +1-555-0101 | john.doe@pms.com |
| Security Officer | Jane Smith | +1-555-0102 | jane.smith@pms.com |
| Operations Manager | Bob Johnson | +1-555-0103 | bob.johnson@pms.com |
| On-Call Engineer | Rotation | +1-555-0199 | oncall@pms.com |

### Escalation Procedures

1. **Level 1** (0-30 minutes): Operations team attempts recovery
2. **Level 2** (30-60 minutes): Database administrator engaged
3. **Level 3** (60+ minutes): Security officer and management notified
4. **Level 4** (4+ hours): External vendor support engaged

## Post-Recovery Checklist

- [ ] Database fully operational
- [ ] All applications connected and functional
- [ ] Smoke tests passed
- [ ] Performance metrics normal
- [ ] Backup system re-enabled
- [ ] Monitoring alerts cleared
- [ ] Stakeholders notified of completion
- [ ] Recovery documentation updated
- [ ] Post-incident review scheduled
- [ ] Lessons learned documented

---

**Document Information:**
- **Version**: 1.0
- **Last Updated**: [Current Date]
- **Next Review**: [3 months from last update]
- **Owner**: Database Operations Team
- **Classification**: Internal Use Only
# Database Migration & Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying database migrations across different environments in the Practice Management System (PMS). It covers migration procedures, rollback strategies, and environment-specific considerations.

## Migration Status

### Current State
- **Current Migration Head**: `2b8812283e69` (merge_all_branches)
- **Migration Tool**: Alembic
- **Database**: PostgreSQL
- **Total Tables**: 13 core tables + alembic_version

### Migration History
```
2b8812283e69 (HEAD) - Merge all branches
├── c8c1872a99cf - Schema cleanup audit
└── schema_cleanup_audit - Audit log enhancements
```

## Pre-Deployment Checklist

### 1. Environment Verification
- [ ] Database connectivity confirmed
- [ ] Backup completed and verified
- [ ] Migration files reviewed and tested
- [ ] Rollback plan prepared
- [ ] Monitoring alerts configured

### 2. Migration Validation
```bash
# Check current migration status
alembic current

# Verify pending migrations
alembic heads

# Review migration history
alembic history --verbose
```

### 3. Database Backup
```bash
# Create full database backup
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup integrity
pg_restore --list backup_$(date +%Y%m%d_%H%M%S).sql
```

## Deployment Procedures

### Local Development

1. **Setup Environment**
   ```bash
   cd /path/to/pms/apps/backend
   source venv/bin/activate
   export DATABASE_URL="postgresql://user:pass@localhost/pms_dev"
   ```

2. **Run Migrations**
   ```bash
   # Check current status
   alembic current
   
   # Apply all pending migrations
   alembic upgrade head
   
   # Verify successful deployment
   alembic current
   ```

3. **Validate Data Integrity**
   ```bash
   # Run data validation script
   python scripts/validate_migration.py
   ```

### Staging Environment

1. **Pre-Deployment**
   ```bash
   # Create staging backup
   pg_dump -h staging-db -U $DB_USER -d pms_staging > staging_backup_$(date +%Y%m%d_%H%M%S).sql
   
   # Verify application is in maintenance mode
   curl -f http://staging-api/health || echo "Application in maintenance mode"
   ```

2. **Migration Deployment**
   ```bash
   # Set staging environment
   export DATABASE_URL="postgresql://user:pass@staging-db/pms_staging"
   export ENVIRONMENT="staging"
   
   # Apply migrations with logging
   alembic upgrade head 2>&1 | tee migration_$(date +%Y%m%d_%H%M%S).log
   ```

3. **Post-Deployment Validation**
   ```bash
   # Verify migration status
   alembic current
   
   # Run integration tests
   pytest tests/integration/
   
   # Check application health
   curl -f http://staging-api/health
   ```

### Production Environment

1. **Pre-Production Checklist**
   - [ ] Staging deployment successful
   - [ ] Integration tests passed
   - [ ] Rollback plan tested
   - [ ] Maintenance window scheduled
   - [ ] Team notifications sent

2. **Zero-Downtime Deployment Strategy**
   ```bash
   # Step 1: Create production backup
   pg_dump -h prod-db -U $DB_USER -d pms_prod > prod_backup_$(date +%Y%m%d_%H%M%S).sql
   
   # Step 2: Apply backward-compatible migrations
   export DATABASE_URL="postgresql://user:pass@prod-db/pms_prod"
   alembic upgrade head
   
   # Step 3: Deploy application code
   # (Application deployment handled by CI/CD pipeline)
   
   # Step 4: Verify deployment
   alembic current
   curl -f http://prod-api/health
   ```

3. **Post-Production Validation**
   ```bash
   # Monitor key metrics
   python scripts/monitor_post_deployment.py
   
   # Verify data integrity
   python scripts/validate_production_data.py
   
   # Check performance metrics
   python scripts/check_query_performance.py
   ```

## Rollback Procedures

### Automatic Rollback Triggers
- Migration failure during execution
- Post-deployment validation failures
- Critical application errors
- Performance degradation > 50%

### Manual Rollback Process

1. **Identify Target Revision**
   ```bash
   # View migration history
   alembic history --verbose
   
   # Identify previous stable revision
   PREVIOUS_REVISION="c8c1872a99cf"  # Example
   ```

2. **Execute Rollback**
   ```bash
   # Rollback to previous revision
   alembic downgrade $PREVIOUS_REVISION
   
   # Verify rollback success
   alembic current
   ```

3. **Restore from Backup (if needed)**
   ```bash
   # Stop application
   systemctl stop pms-api
   
   # Restore database
   pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME backup_file.sql
   
   # Restart application
   systemctl start pms-api
   ```

## Environment-Specific Configurations

### Development
- **Database**: Local PostgreSQL
- **Migration Mode**: Interactive
- **Backup Frequency**: Before major changes
- **Rollback Strategy**: Drop/recreate database

### Staging
- **Database**: Shared staging instance
- **Migration Mode**: Automated with logging
- **Backup Frequency**: Before each deployment
- **Rollback Strategy**: Alembic downgrade + validation

### Production
- **Database**: High-availability cluster
- **Migration Mode**: Zero-downtime with monitoring
- **Backup Frequency**: Continuous + pre-deployment
- **Rollback Strategy**: Alembic downgrade or backup restore

## Monitoring & Alerting

### Key Metrics to Monitor
- Migration execution time
- Database connection pool usage
- Query performance impact
- Application error rates
- Data integrity checks

### Alert Thresholds
- Migration duration > 5 minutes
- Error rate increase > 10%
- Query performance degradation > 25%
- Failed health checks

### Monitoring Commands
```bash
# Check migration status
alembic current

# Monitor database connections
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check table sizes
psql -c "SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

## Troubleshooting

### Common Issues

1. **Migration Conflicts**
   ```bash
   # Resolve merge conflicts
   alembic merge -m "resolve_conflicts"
   alembic upgrade head
   ```

2. **Lock Timeouts**
   ```bash
   # Check for blocking queries
   psql -c "SELECT * FROM pg_locks WHERE NOT granted;"
   
   # Kill blocking sessions if necessary
   psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND query_start < now() - interval '5 minutes';"
   ```

3. **Data Validation Failures**
   ```bash
   # Run specific validation checks
   python scripts/validate_specific_table.py --table=clients
   
   # Check foreign key constraints
   psql -c "SELECT conname, conrelid::regclass FROM pg_constraint WHERE contype = 'f';"
   ```

### Emergency Contacts
- **Database Team**: db-team@company.com
- **DevOps Team**: devops@company.com
- **On-Call Engineer**: +1-555-0123

## Security Considerations

### Access Control
- Migration scripts require elevated database privileges
- Production access limited to authorized personnel
- All migration activities logged and audited

### Data Protection
- PHI data encrypted at rest and in transit
- Backup files encrypted and stored securely
- Migration logs sanitized of sensitive information

### Compliance
- HIPAA compliance maintained throughout migration process
- Audit trails preserved for regulatory requirements
- Data retention policies enforced

## Performance Optimization

### Migration Performance
- Large table migrations scheduled during low-usage periods
- Indexes created concurrently to avoid blocking
- Batch processing for data transformations

### Post-Migration Optimization
```sql
-- Update table statistics
ANALYZE;

-- Rebuild indexes if necessary
REINDEX DATABASE pms_prod;

-- Check for unused indexes
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE schemaname = 'public';
```

## Documentation Updates

After successful deployment:
1. Update this deployment guide with lessons learned
2. Document any new procedures or configurations
3. Update the ERD if schema changes were made
4. Notify stakeholders of completion

## Appendix

### Migration File Naming Convention
```
YYYYMMDD_HHMM_<revision_id>_<description>.py
```

### Required Environment Variables
```bash
DATABASE_URL=postgresql://user:pass@host:port/database
ENVIRONMENT=development|staging|production
ALEMBIC_CONFIG=alembic.ini
```

### Useful Alembic Commands
```bash
# Generate new migration
alembic revision --autogenerate -m "description"

# Show current revision
alembic current

# Show migration history
alembic history

# Upgrade to specific revision
alembic upgrade <revision>

# Downgrade to specific revision
alembic downgrade <revision>

# Show SQL for migration
alembic upgrade --sql head
```

This deployment guide should be reviewed and updated regularly to reflect changes in infrastructure, procedures, and lessons learned from deployments.
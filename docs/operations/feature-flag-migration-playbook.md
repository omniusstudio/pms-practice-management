# Feature Flag Migration Playbook

## Overview

This playbook provides step-by-step procedures for safely managing feature flag rollouts and rollbacks in the HIPAA-compliant Practice Management System. It builds upon the existing feature flag infrastructure to ensure safe, auditable, and reversible feature deployments.

## Prerequisites

### Required Access
- Production environment access
- Database migration permissions
- Feature flag management system access (LaunchDarkly or local configuration)
- Monitoring and alerting system access
- Audit logging access

### Required Tools
- `kubectl` (for Kubernetes deployments)
- `alembic` (for database migrations)
- `psql` or database client
- Monitoring dashboards
- Log aggregation tools

## Feature Flag Lifecycle

### Phase 1: Development and Testing
1. **Local Development**
   - Feature flags configured in `apps/backend/config/feature_flags.json`
   - Local testing with flags enabled/disabled
   - Unit and integration tests covering both flag states

2. **Staging Deployment**
   - Deploy to staging environment
   - Validate feature behavior with flags enabled
   - Run automated test suites
   - Performance testing with feature enabled

### Phase 2: Production Rollout
1. **Pre-deployment Preparation**
2. **Gradual Rollout**
3. **Full Activation**
4. **Monitoring and Validation**

### Phase 3: Rollback (if needed)
1. **Emergency Rollback**
2. **Planned Rollback**
3. **Post-rollback Validation**

## Detailed Procedures

### Pre-deployment Checklist

**Technical Validation:**
- [ ] Feature flag configuration reviewed and approved
- [ ] Database migrations tested and validated
- [ ] Rollback procedures tested in staging
- [ ] Performance impact assessed
- [ ] Security review completed
- [ ] HIPAA compliance verified

**Operational Readiness:**
- [ ] Monitoring alerts configured
- [ ] Rollback plan documented and approved
- [ ] Team notifications prepared
- [ ] Maintenance window scheduled (if required)
- [ ] Backup verification completed

**Documentation:**
- [ ] Feature documentation updated
- [ ] API documentation updated (if applicable)
- [ ] User training materials prepared
- [ ] Support team briefed

### Production Rollout Procedure

#### Step 1: Initial Deployment (Feature Disabled)

```bash
# 1. Deploy application with feature flag disabled
make deploy-production

# 2. Verify deployment health
kubectl get pods -n pms
kubectl logs -n pms deployment/pms-backend --tail=100

# 3. Run health checks
curl -f https://api.pms.example.com/health

# 4. Verify feature flag is disabled
curl -H "Authorization: Bearer $TOKEN" https://api.pms.example.com/api/v1/feature-flags/status
```

#### Step 2: Database Migration (if required)

```bash
# 1. Connect to production database
kubectl exec -it -n pms deployment/pms-backend -- bash

# 2. Run migrations
alembic upgrade head

# 3. Verify migration success
alembic current
alembic history --verbose

# 4. Test database connectivity
psql $DATABASE_URL -c "SELECT version();"
```

#### Step 3: Gradual Feature Activation

**Option A: Percentage-based Rollout (LaunchDarkly)**
```bash
# Enable for 5% of users
# Update via LaunchDarkly dashboard or API
curl -X PATCH "https://app.launchdarkly.com/api/v2/flags/$PROJECT_KEY/$FEATURE_KEY" \
  -H "Authorization: $LD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "patch": [
      {
        "op": "replace",
        "path": "/environments/production/rules/0/rollout/variations/0/weight",
        "value": 5000
      }
    ]
  }'
```

**Option B: Local Configuration Update**
```bash
# 1. Update feature flag configuration
kubectl edit configmap -n pms feature-flags-config

# 2. Restart pods to pick up new configuration
kubectl rollout restart deployment/pms-backend -n pms
kubectl rollout status deployment/pms-backend -n pms
```

#### Step 4: Monitoring and Validation

```bash
# 1. Monitor application metrics
# Check Grafana dashboards for:
# - Response times
# - Error rates
# - Database performance
# - Memory/CPU usage

# 2. Check audit logs
kubectl logs -n pms deployment/pms-backend | grep "feature_flag_toggled"

# 3. Validate feature functionality
# Run smoke tests specific to the feature

# 4. Monitor user feedback and support tickets
```

#### Step 5: Progressive Rollout

```bash
# Gradually increase percentage:
# 5% → 25% → 50% → 100%
# Wait 30-60 minutes between each increase
# Monitor metrics at each stage

# Example: Increase to 25%
curl -X PATCH "https://app.launchdarkly.com/api/v2/flags/$PROJECT_KEY/$FEATURE_KEY" \
  -H "Authorization: $LD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "patch": [
      {
        "op": "replace",
        "path": "/environments/production/rules/0/rollout/variations/0/weight",
        "value": 25000
      }
    ]
  }'
```

### Rollback Procedures

#### Emergency Rollback (< 5 minutes)

**Immediate Feature Disable:**
```bash
# Option A: LaunchDarkly (fastest)
curl -X PATCH "https://app.launchdarkly.com/api/v2/flags/$PROJECT_KEY/$FEATURE_KEY" \
  -H "Authorization: $LD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "patch": [
      {
        "op": "replace",
        "path": "/environments/production/on",
        "value": false
      }
    ]
  }'

# Option B: Local configuration (requires pod restart)
kubectl patch configmap -n pms feature-flags-config -p '{
  "data": {
    "feature_flags.json": "{\"production\": {\"$FEATURE_NAME\": false}}"
  }
}'
kubectl rollout restart deployment/pms-backend -n pms
```

**Verify Rollback:**
```bash
# 1. Confirm feature is disabled
curl -H "Authorization: Bearer $TOKEN" https://api.pms.example.com/api/v1/feature-flags/status

# 2. Monitor application recovery
kubectl logs -n pms deployment/pms-backend --tail=100

# 3. Run health checks
curl -f https://api.pms.example.com/health
```

#### Planned Rollback with Database Migration

```bash
# 1. Disable feature flag (as above)

# 2. Wait for traffic to stabilize (5-10 minutes)

# 3. Run database rollback migration
kubectl exec -it -n pms deployment/pms-backend -- bash
alembic downgrade -1  # or specific revision

# 4. Verify database state
alembic current
psql $DATABASE_URL -c "\\dt"  # List tables to verify structure

# 5. Deploy previous application version if needed
make rollback-production
```

### Monitoring and Alerting

#### Key Metrics to Monitor

1. **Application Performance**
   - Response time (95th percentile)
   - Error rate (4xx, 5xx responses)
   - Throughput (requests per second)
   - Database query performance

2. **Business Metrics**
   - Feature adoption rate
   - User engagement metrics
   - Conversion rates (if applicable)
   - Support ticket volume

3. **System Health**
   - CPU and memory usage
   - Database connections
   - Queue lengths
   - Cache hit rates

#### Alert Thresholds

```yaml
# Example Prometheus alerts
groups:
  - name: feature-flag-rollout
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected during feature rollout"
          
      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Response time degradation detected"
```

### Audit and Compliance

#### Required Audit Logs

All feature flag operations must be logged with:
- Timestamp (UTC)
- User/system performing the action
- Feature flag name and previous/new state
- Reason for change
- Environment (staging/production)

#### Example Audit Log Entry
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "event_type": "feature_flag_toggled",
  "user_id": "admin@pms.example.com",
  "feature_flag": "telehealth_appointments_enabled",
  "previous_state": false,
  "new_state": true,
  "environment": "production",
  "reason": "Gradual rollout - Phase 2 (25% of users)",
  "rollout_percentage": 25,
  "approval_ticket": "TICKET-12345"
}
```

### Troubleshooting

#### Common Issues and Solutions

**Issue: Feature flag not taking effect**
```bash
# 1. Check configuration
kubectl get configmap -n pms feature-flags-config -o yaml

# 2. Verify pod restart
kubectl get pods -n pms -o wide
kubectl describe pod -n pms $POD_NAME

# 3. Check application logs
kubectl logs -n pms deployment/pms-backend | grep "feature_flag"
```

**Issue: Database migration failure**
```bash
# 1. Check migration status
alembic current
alembic history

# 2. Review migration logs
kubectl logs -n pms deployment/pms-backend | grep "alembic"

# 3. Manual intervention (if safe)
alembic stamp head  # Only if migration completed but not recorded
```

**Issue: Performance degradation**
```bash
# 1. Immediate rollback
# (Use emergency rollback procedure above)

# 2. Analyze performance metrics
# Check Grafana dashboards
# Review database slow query logs

# 3. Investigate root cause
kubectl top pods -n pms
kubectl exec -it -n pms deployment/pms-backend -- top
```

### Communication Templates

#### Pre-rollout Notification
```
Subject: [PMS] Feature Rollout Starting: [FEATURE_NAME]

Team,

We are beginning the gradual rollout of [FEATURE_NAME] to production.

Timeline:
- Start: [TIME]
- 5% rollout: [TIME]
- 25% rollout: [TIME]
- 50% rollout: [TIME]
- 100% rollout: [TIME]

Monitoring: [DASHBOARD_LINK]
Rollback contact: [CONTACT_INFO]

Please monitor support channels for any issues.
```

#### Rollback Notification
```
Subject: [URGENT] [PMS] Feature Rollback: [FEATURE_NAME]

Team,

[FEATURE_NAME] has been rolled back due to [REASON].

Actions taken:
- Feature disabled at [TIME]
- [Additional actions if any]

Current status: [STATUS]
Next steps: [NEXT_STEPS]

Incident ticket: [TICKET_LINK]
```

## Best Practices

1. **Always test rollback procedures in staging first**
2. **Use gradual rollouts for all user-facing features**
3. **Monitor metrics continuously during rollouts**
4. **Have a dedicated person monitoring during rollouts**
5. **Document all decisions and observations**
6. **Keep rollback procedures simple and fast**
7. **Maintain audit trails for all changes**
8. **Communicate proactively with stakeholders**

## Emergency Contacts

- **On-call Engineer**: [CONTACT]
- **Database Administrator**: [CONTACT]
- **Security Team**: [CONTACT]
- **Compliance Officer**: [CONTACT]

---

**Document Version**: 1.0  
**Last Updated**: [DATE]  
**Next Review**: [DATE + 3 months]  
**Owner**: DevOps Team
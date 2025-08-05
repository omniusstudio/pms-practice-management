# Automated Key Rotation Implementation Guide

## Overview

This document describes the implementation of automated key rotation for the encryption key management system. The automated rotation system provides scheduled, policy-based key rotation to enhance security and meet compliance requirements.

## Architecture

### Components

1. **KeyRotationPolicy Model** - Defines rotation policies and schedules
2. **KeyRotationScheduler Service** - Manages automated rotation execution
3. **Enhanced EncryptionKey Model** - Links keys to rotation policies
4. **Database Migration** - Schema changes for rotation support

### Key Features

- **Time-based Rotation**: Rotate keys at specified intervals
- **Usage-based Rotation**: Rotate based on usage thresholds (future enhancement)
- **Event-driven Rotation**: Rotate on specific events (future enhancement)
- **Policy Management**: Create, update, and manage rotation policies
- **Audit Trail**: Complete logging of all rotation activities
- **Rollback Support**: Ability to rollback recent rotations
- **Tenant Isolation**: Policies are tenant-specific

## Database Schema

### KeyRotationPolicy Table

```sql
CREATE TABLE key_rotation_policies (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    policy_name VARCHAR(255) NOT NULL,
    description TEXT,
    key_type VARCHAR(50) NOT NULL,
    kms_provider VARCHAR(50) NOT NULL,
    rotation_trigger VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    
    -- Time-based settings
    rotation_interval_days INTEGER,
    rotation_time_of_day VARCHAR(8), -- HH:MM:SS
    timezone VARCHAR(50) DEFAULT 'UTC',
    
    -- Usage-based settings (future)
    max_usage_count INTEGER,
    usage_threshold_warning INTEGER,
    
    -- Event-based settings (future)
    rotation_events JSON,
    
    -- Rollback and retention
    enable_rollback BOOLEAN DEFAULT TRUE,
    rollback_period_hours INTEGER DEFAULT 24,
    retain_old_keys_days INTEGER DEFAULT 30,
    
    -- Metadata
    notification_settings JSON,
    compliance_tags JSON,
    authorized_services JSON,
    created_by_token_id UUID,
    last_modified_by_token_id UUID,
    correlation_id VARCHAR(255),
    
    -- Timestamps
    last_rotation_at TIMESTAMP WITH TIME ZONE,
    next_rotation_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

### EncryptionKey Updates

```sql
ALTER TABLE encryption_keys 
ADD COLUMN rotation_policy_id UUID 
REFERENCES key_rotation_policies(id) ON DELETE SET NULL;
```

## Usage Examples

### Creating a Rotation Policy

```python
from services.key_rotation_scheduler import KeyRotationScheduler
from models.key_rotation_policy import RotationTrigger
from models.encryption_key import KeyType, KeyProvider

# Initialize scheduler
scheduler = KeyRotationScheduler(db_session)

# Create a daily rotation policy for PHI keys
policy = await scheduler.create_rotation_policy(
    tenant_id="healthcare-org-123",
    policy_name="Daily PHI Key Rotation",
    description="Rotate PHI encryption keys daily at 2 AM UTC",
    key_type=KeyType.PHI_DATA,
    kms_provider=KeyProvider.AWS_KMS,
    rotation_trigger=RotationTrigger.TIME_BASED,
    rotation_interval_days=1,
    rotation_time_of_day="02:00:00",
    timezone="UTC",
    enable_rollback=True,
    rollback_period_hours=24,
    retain_old_keys_days=30,
    compliance_tags=["HIPAA", "SOC2"],
    notification_settings={
        "email": ["security@healthcare-org.com"],
        "slack_webhook": "https://hooks.slack.com/..."
    }
)
```

### Linking Keys to Policies

```python
from services.encryption_key_service import EncryptionKeyService

# Create key with rotation policy
key_service = EncryptionKeyService(db_session)
key = await key_service.create_key(
    tenant_id="healthcare-org-123",
    key_name="patient-data-encryption-key",
    key_type=KeyType.PHI_DATA,
    kms_provider=KeyProvider.AWS_KMS,
    kms_key_id="arn:aws:kms:us-east-1:123456789:key/abc123",
    kms_region="us-east-1"
)

# Link to rotation policy
key.rotation_policy_id = policy.id
db_session.commit()
```

### Starting the Scheduler

```python
# Start automated rotation scheduler
scheduler = KeyRotationScheduler(db_session)
await scheduler.start_scheduler(check_interval_minutes=15)

# The scheduler will now check every 15 minutes for keys that need rotation
# and automatically rotate them based on their policies
```

### Manual Rotation Check

```python
# Manually trigger rotation check
results = await scheduler.check_and_rotate_keys()

for result in results:
    print(f"Policy: {result['policy_name']}")
    print(f"Status: {result['status']}")
    print(f"Rotated Keys: {result['rotated_keys']}")
    print(f"Failed Keys: {result['failed_keys']}")
```

### Managing Policy Status

```python
from models.key_rotation_policy import PolicyStatus

# Suspend a policy
await scheduler.update_policy_status(policy.id, PolicyStatus.SUSPENDED)

# Reactivate a policy
await scheduler.update_policy_status(policy.id, PolicyStatus.ACTIVE)
```

### Viewing Rotation History

```python
# Get rotation history for a tenant
history = await scheduler.get_rotation_history(
    tenant_id="healthcare-org-123",
    limit=50
)

for record in history:
    print(f"Key: {record['key_name']}")
    print(f"Rotated: {record['rotated_at']}")
    print(f"Status: {record['status']}")
```

## Configuration

### Environment Variables

```bash
# Scheduler settings
KEY_ROTATION_CHECK_INTERVAL=15  # minutes
KEY_ROTATION_ENABLED=true

# Notification settings
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
SMTP_SERVER=smtp.company.com
SMTP_PORT=587
```

### Policy Configuration Options

#### Rotation Triggers

- `TIME_BASED`: Rotate at specified time intervals
- `USAGE_BASED`: Rotate after specified usage count (future)
- `EVENT_BASED`: Rotate on specific events (future)
- `MANUAL`: Manual rotation only

#### Time-based Settings

- `rotation_interval_days`: Days between rotations
- `rotation_time_of_day`: Preferred time for rotation (HH:MM:SS)
- `timezone`: Timezone for rotation scheduling

#### Rollback Settings

- `enable_rollback`: Allow rollback of rotations
- `rollback_period_hours`: Hours within which rollback is allowed
- `retain_old_keys_days`: Days to retain old keys after rotation

## Security Considerations

### Access Control

- Only authorized tokens can create/modify rotation policies
- Tenant isolation ensures policies only affect tenant's keys
- System-initiated rotations are logged with correlation IDs

### Audit Trail

- All rotation activities are logged
- Policy changes are tracked
- Failed rotations are recorded with error details

### Rollback Safety

- Old keys are retained for the configured period
- Rollback operations are time-limited
- Rollback actions are fully audited

## Monitoring and Alerting

### Key Metrics

- Successful rotations per day/week/month
- Failed rotation attempts
- Policy compliance rates
- Average rotation duration

### Alerts

- Failed rotation attempts
- Policies with no associated keys
- Keys approaching expiration without policies
- Unusual rotation patterns

### Health Checks

```python
# Check scheduler health
if scheduler._running:
    print("Scheduler is running")
else:
    print("Scheduler is stopped")

# Check policy health
active_policies = await scheduler._get_active_policies()
print(f"Active policies: {len(active_policies)}")
```

## Troubleshooting

### Common Issues

1. **Scheduler Not Running**
   - Check if `start_scheduler()` was called
   - Verify no exceptions in scheduler loop
   - Check database connectivity

2. **Keys Not Rotating**
   - Verify policy is active
   - Check `next_rotation_at` timestamp
   - Ensure keys are linked to policy
   - Verify KMS permissions

3. **Rotation Failures**
   - Check KMS connectivity and permissions
   - Verify key exists in KMS
   - Check database transaction issues

### Debug Commands

```python
# Check policy schedule
policy = db_session.get(KeyRotationPolicy, policy_id)
print(f"Next rotation: {policy.next_rotation_at}")
print(f"Should rotate now: {policy.should_rotate_now()}")

# Check keys for policy
keys = await scheduler._get_keys_for_policy(policy)
print(f"Keys to rotate: {len(keys)}")

# Manual rotation test
if keys:
    result = await scheduler._rotate_key(keys[0], policy)
    print(f"Rotation result: {result}")
```

## Performance Considerations

### Database Optimization

- Indexes on frequently queried columns
- Efficient policy lookup queries
- Batch processing for multiple keys

### Scheduler Optimization

- Configurable check intervals
- Async processing for concurrent rotations
- Error handling to prevent scheduler crashes

### KMS Optimization

- Connection pooling for KMS calls
- Retry logic for transient failures
- Rate limiting to avoid API throttling

## Future Enhancements

### Planned Features

1. **Usage-based Rotation**: Rotate keys after specified usage count
2. **Event-driven Rotation**: Rotate on security events or alerts
3. **Advanced Scheduling**: Cron-like scheduling expressions
4. **Multi-region Support**: Coordinate rotations across regions
5. **Integration APIs**: REST APIs for external rotation triggers
6. **Dashboard**: Web interface for policy management

### Extensibility

The system is designed to be extensible:

- New rotation triggers can be added to `RotationTrigger` enum
- Custom rotation logic can be implemented in scheduler
- Additional KMS providers can be supported
- Notification channels can be extended

## Compliance

### HIPAA Compliance

- Regular key rotation meets HIPAA requirements
- Audit trails provide required documentation
- Access controls ensure authorized access only

### SOC 2 Compliance

- Automated controls reduce human error
- Comprehensive logging supports audits
- Policy-based approach ensures consistency

### Industry Standards

- Follows NIST key management guidelines
- Implements defense-in-depth principles
- Supports zero-trust architecture

## Support

For questions or issues with the automated key rotation system:

1. Check this documentation
2. Review system logs
3. Run diagnostic commands
4. Contact the security team

---

*This document is part of the PMS encryption key management system documentation.*
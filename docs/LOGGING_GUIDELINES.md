# Logging Guidelines for HIPAA-Compliant Mental Health PMS

## Overview

This document provides comprehensive guidelines for logging in our HIPAA-compliant Mental Health Practice Management System. All logging must adhere to strict PHI (Protected Health Information) protection requirements while maintaining effective debugging and audit capabilities.

## Core Principles

### 1. **NO PHI in Logs**
- Never log patient names, SSNs, medical records, or any identifiable information
- All log entries are automatically scrubbed for PHI patterns
- Use resource IDs instead of names or personal identifiers

### 2. **Correlation ID Tracking**
- Every request gets a unique correlation ID for end-to-end tracing
- Correlation IDs are propagated across all services and components
- Format: `{source}-{timestamp}-{random}` (e.g., `client-1640995200000-abc123def`)

### 3. **Structured JSON Logging**
- All logs use consistent JSON structure
- Include required fields: `timestamp`, `level`, `event`, `correlation_id`
- Use standardized event types for filtering and analysis

## Implementation

### Backend Logging (Python/FastAPI)

#### Basic Usage

```python
import structlog
from middleware.logging import get_correlation_id
from utils.audit_logger import log_crud_action

logger = structlog.get_logger()

# Standard logging
logger.info(
    "User action completed",
    correlation_id=get_correlation_id(request),
    action="create_appointment",
    user_id="user_123",
    resource_id="appt_456"
)

# Audit logging for CRUD operations
log_crud_action(
    action="CREATE",
    resource="appointment",
    user_id="user_123",
    correlation_id=get_correlation_id(request),
    resource_id="appt_456",
    metadata={"duration_minutes": 60}
)
```

#### PHI Scrubbing

All log entries are automatically processed through PHI scrubbing:

```python
from utils.phi_scrubber import scrub_phi

# This will be automatically scrubbed
logger.info("Processing patient John Doe with SSN 123-45-6789")
# Becomes: "Processing patient [PATIENT-NAME-REDACTED] with SSN [SSN-REDACTED]"

# Manual scrubbing for complex data
user_data = scrub_phi({
    "name": "John Doe",
    "email": "john@example.com",
    "id": "user_123"
})
# Results in: {"name": "[REDACTED]", "email": "[EMAIL-REDACTED]", "id": "user_123"}
```

### Frontend Logging (TypeScript/React)

#### Basic Usage

```typescript
import { Logger, useLogger } from '../utils/logger';

// In a React component
const MyComponent = () => {
  const logger = useLogger();
  
  const handleSubmit = async () => {
    logger.info('Form submission started', {
      component: 'PatientForm',
      action: 'submit'
    });
    
    try {
      await api.post('/patients', formData);
      logger.auditAction('CREATE', 'patient', userId);
    } catch (error) {
      logger.error('Form submission failed', error, {
        component: 'PatientForm'
      });
    }
  };
};

// Static usage
Logger.info('Application started', {
  version: '1.0.0',
  environment: process.env.NODE_ENV
});
```

#### HTTP Request Logging

```typescript
import { api } from '../utils/http-client';

// Automatic correlation ID and request/response logging
const response = await api.get('/patients/123');
// Logs: "HTTP Request Started" and "API Call: GET /patients/123"
```

## Log Structure

### Standard Log Entry

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "info",
  "event": "user_action",
  "correlation_id": "backend-1640995200000-xyz789",
  "user_id": "user_123",
  "action": "view_patient",
  "resource_type": "patient",
  "resource_id": "patient_456",
  "duration_ms": 150
}
```

### Audit Log Entry

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "info",
  "event": "audit_log",
  "correlation_id": "backend-1640995200000-xyz789",
  "audit_action": "CREATE",
  "resource_type": "appointment",
  "resource_id": "appt_789",
  "user_id": "user_123",
  "changes": {
    "status": "scheduled",
    "duration_minutes": 60
  },
  "immutable": true
}
```

### Error Log Entry

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "error",
  "event": "request_error",
  "correlation_id": "backend-1640995200000-xyz789",
  "error_type": "ValidationError",
  "status_code": 400,
  "duration_ms": 50,
  "user_id": "user_123"
}
```

## Event Types

### Standard Events
- `request_start` - HTTP request initiated
- `request_complete` - HTTP request completed successfully
- `request_error` - HTTP request failed
- `user_action` - User performed an action
- `audit_log` - CRUD operation audit trail
- `security_audit` - Authentication/authorization events
- `data_access_audit` - Data access tracking
- `system_audit` - System events and errors

### Custom Events
Use descriptive event names following the pattern: `{domain}_{action}`
- `appointment_scheduled`
- `payment_processed`
- `report_generated`
- `backup_completed`

## Query Examples

### Find All Requests for a User

```bash
# Using jq to filter logs
cat application.log | jq 'select(.user_id == "user_123")'

# Using grep for correlation ID
grep "correlation_id.*backend-1640995200000-xyz789" application.log
```

### Trace Complete Request Flow

```bash
# Follow a request from start to finish
cat application.log | jq 'select(.correlation_id == "backend-1640995200000-xyz789")' | jq -s 'sort_by(.timestamp)'
```

### Find All Audit Events

```bash
# All CRUD operations
cat application.log | jq 'select(.event == "audit_log")'

# Specific resource type
cat application.log | jq 'select(.event == "audit_log" and .resource_type == "patient")'
```

### Error Analysis

```bash
# All errors in the last hour
cat application.log | jq 'select(.level == "error" and (.timestamp | fromdateiso8601) > (now - 3600))'

# Errors by type
cat application.log | jq 'select(.level == "error") | .error_type' | sort | uniq -c
```

### Performance Monitoring

```bash
# Slow requests (>1000ms)
cat application.log | jq 'select(.duration_ms > 1000)'

# Average response time by endpoint
cat application.log | jq 'select(.event == "request_complete") | {path: .path, duration: .duration_ms}' | jq -s 'group_by(.path) | map({path: .[0].path, avg_duration: (map(.duration) | add / length)})'
```

## Log Retention and Access

### Retention Policies
- **Operational Logs**: 7 days (debugging, performance monitoring)
- **Audit Logs**: 7 years (HIPAA compliance requirement)
- **Security Logs**: 1 year (security incident investigation)

### Access Controls
- **Developers**: Read access to operational logs (non-production)
- **DevOps**: Read access to all logs
- **Security Team**: Full access to security and audit logs
- **Compliance Team**: Read access to audit logs

### Log Storage
- Logs are encrypted at rest and in transit
- Centralized log collection via secure endpoints
- Automated backup and archival processes
- Geographic replication for disaster recovery

## PHI Scrubbing Patterns

### Automatically Detected Patterns
- Social Security Numbers: `123-45-6789` → `[SSN-REDACTED]`
- Email Addresses: `user@example.com` → `[EMAIL-REDACTED]`
- Phone Numbers: `(555) 123-4567` → `[PHONE-REDACTED]`
- Credit Cards: `4111 1111 1111 1111` → `[CARD-REDACTED]`
- Medical Record Numbers: `MRN: 123456` → `[MRN-REDACTED]`
- Dates of Birth: `01/15/1990` → `[DOB-REDACTED]`

### Sensitive Field Names
Fields with these names are automatically redacted:
- `name`, `first_name`, `last_name`, `full_name`
- `email`, `email_address`
- `phone`, `phone_number`, `telephone`
- `ssn`, `social_security_number`
- `date_of_birth`, `dob`, `birth_date`
- `address`, `street_address`, `home_address`
- `medical_record_number`, `mrn`, `patient_id`
- `diagnosis`, `medical_condition`, `treatment`
- `prescription`, `medication`

## Best Practices

### Do's ✅
- Use correlation IDs for all requests
- Log user actions for audit trails
- Include context information (user_id, resource_id)
- Use structured logging with consistent fields
- Log at appropriate levels (DEBUG, INFO, WARN, ERROR)
- Include performance metrics (duration, response size)

### Don'ts ❌
- Never log PHI or PII
- Don't log passwords, tokens, or secrets
- Avoid logging entire request/response bodies
- Don't use correlation IDs as security tokens
- Don't log stack traces in production (PHI risk)
- Avoid excessive logging that impacts performance

## Troubleshooting

### Common Issues

1. **Missing Correlation IDs**
   - Ensure middleware is properly configured
   - Check that correlation IDs are propagated in HTTP headers
   - Verify frontend is sending X-Correlation-ID header

2. **PHI in Logs**
   - Review PHI scrubbing patterns
   - Add custom patterns for domain-specific PHI
   - Implement additional field-level scrubbing

3. **Log Volume Issues**
   - Adjust log levels for production
   - Implement sampling for high-volume endpoints
   - Use asynchronous logging to reduce performance impact

4. **Missing Audit Trails**
   - Ensure audit logging is called for all CRUD operations
   - Verify immutable flag is set for audit entries
   - Check that audit logs are properly retained

### Monitoring and Alerts

- **High Error Rates**: Alert when error rate exceeds 5%
- **Slow Responses**: Alert when 95th percentile exceeds 2 seconds
- **Missing Correlation IDs**: Alert when >1% of requests lack correlation IDs
- **PHI Detection**: Alert immediately if PHI patterns are detected in logs
- **Audit Log Gaps**: Alert if audit logs are missing for CRUD operations

## Compliance Verification

### Regular Audits
- Monthly spot-checks for PHI in logs
- Quarterly correlation ID coverage analysis
- Annual audit log retention verification
- Continuous monitoring for new PHI patterns

### Validation Queries

```bash
# Check for potential PHI leakage
cat application.log | grep -E "\b\d{3}-\d{2}-\d{4}\b|\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

# Verify correlation ID coverage
cat application.log | jq 'select(.correlation_id == null or .correlation_id == "")' | wc -l

# Audit log completeness
cat application.log | jq 'select(.event == "audit_log")' | jq -s 'group_by(.resource_type) | map({resource: .[0].resource_type, count: length})'
```

---

**Last Updated**: January 2024  
**Version**: 1.0  
**Owner**: DevOps & Security Teams  
**Review Cycle**: Quarterly
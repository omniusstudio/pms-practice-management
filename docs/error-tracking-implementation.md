# Error Tracking and Alerting Implementation

This document describes the implementation of error tracking and alerting system for the Mental Health Practice Management System, ensuring HIPAA compliance and comprehensive monitoring.

## Overview

The error tracking system consists of:
- **Sentry Integration**: Client and server-side error tracking with PHI scrubbing
- **Alert Routing**: Automated notifications to Slack and PagerDuty
- **Test Endpoints**: Validation and testing capabilities
- **Health Monitoring**: System health checks for error tracking components

## Architecture

### Backend Components

1. **Sentry Service** (`services/sentry_service.py`)
   - Configures Sentry SDK with HIPAA-compliant PHI scrubbing
   - Handles exception capture and message logging
   - Provides test event generation

2. **Alert Service** (`services/alert_service.py`)
   - Routes alerts to Slack and PagerDuty
   - Implements severity-based routing
   - Scrubs PHI from alert content
   - Supports test alert generation

3. **Sentry Integration** (`integrations/sentry_integration.py`)
   - FastAPI middleware for request/response tracking
   - Global exception handler with alert integration
   - Test endpoints for validation

### Frontend Components

1. **Sentry Service** (`src/services/sentryService.ts`)
   - Client-side error tracking with PHI scrubbing
   - React Router integration
   - User context anonymization

2. **PHI Scrubber** (`src/utils/phiScrubber.ts`)
   - Frontend PHI detection and scrubbing
   - URL parameter sanitization
   - Form data scrubbing

3. **Enhanced Error Boundary** (`src/components/ErrorBoundary.tsx`)
   - Integrated with Sentry for error capture
   - Breadcrumb tracking for user actions

## Configuration

### Environment Variables

#### Backend (.env)
```bash
# Sentry Configuration
SENTRY_DSN=https://your-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=1.0.0
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1

# Alert Routing
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
PAGERDUTY_INTEGRATION_KEY=your-pagerduty-integration-key
ALERT_CHANNEL_CRITICAL=#pms-critical-alerts
ALERT_CHANNEL_WARNING=#pms-alerts
```

#### Frontend (.env)
```bash
# Sentry Configuration
REACT_APP_SENTRY_DSN=https://your-dsn@sentry.io/project-id
REACT_APP_SENTRY_ENVIRONMENT=production
REACT_APP_SENTRY_RELEASE=1.0.0
REACT_APP_SENTRY_TRACES_SAMPLE_RATE=0.1
```

## HIPAA Compliance Features

### PHI Scrubbing Patterns

The system automatically scrubs the following PHI patterns:
- Social Security Numbers (XXX-XX-XXXX, XXXXXXXXX)
- Phone numbers (XXX-XXX-XXXX, (XXX) XXX-XXXX)
- Email addresses
- Date of birth patterns
- Medical record numbers
- Patient names and identifiers
- Addresses and ZIP codes
- Insurance information

### User Anonymization

- User IDs are hashed and anonymized (e.g., `user_1234`)
- Sensitive headers are redacted
- Request/response data is scrubbed
- Stack traces are sanitized

### Data Retention

- Session replay is disabled
- Error data retention follows HIPAA requirements
- Sensitive context is removed before transmission

## Alert Routing

### Severity Levels

- **CRITICAL**: Sent to Slack and PagerDuty
- **WARNING**: Sent to Slack only
- **INFO**: Sent to Slack only

### Slack Integration

Alerts are formatted with:
- Color-coded severity indicators
- Service and environment information
- Correlation IDs for tracking
- Anonymized user information

### PagerDuty Integration

Critical alerts trigger PagerDuty incidents with:
- Deduplication keys for grouping
- Custom details for context
- Automatic escalation policies

## Test Endpoints

### Backend Test Routes

1. **Sentry Error Test**
   ```bash
   POST /api/test/sentry-error
   ```
   Generates a test exception captured by Sentry

2. **Alert Test**
   ```bash
   POST /api/test/alert
   ```
   Sends a test alert to configured channels

3. **Error with Alert Test**
   ```bash
   POST /api/test/error-with-alert
   ```
   Generates an error and sends corresponding alert

4. **Health Check**
   ```bash
   GET /api/health/error-tracking
   ```
   Returns status of error tracking components

### Frontend Test Functions

```typescript
import { createSentryTestError } from './services/sentryService';

// Generate test error
createeSentryTestError();
```

## Usage Examples

### Backend Error Capture

```python
from services.sentry_service import get_sentry_service
from services.alert_service import get_alert_service, AlertSeverity

sentry_service = get_sentry_service()
alert_service = get_alert_service()

try:
    # Your code here
    pass
except Exception as e:
    # Capture in Sentry
    sentry_service.capture_exception(
        e,
        extra_context={
            "user_id": user_id,
            "correlation_id": correlation_id,
        }
    )
    
    # Send alert
    await alert_service.send_error_alert(
        exception=e,
        severity=AlertSeverity.CRITICAL,
        user_id=user_id,
        correlation_id=correlation_id
    )
```

### Frontend Error Capture

```typescript
import { captureSentryException, setSentryUser } from './services/sentryService';

// Set user context
setSentryUser('user123', { role: 'provider' });

try {
  // Your code here
} catch (error) {
  captureSentryException(error, {
    component: 'PatientForm',
    action: 'save_patient',
  });
}
```

## Monitoring and Maintenance

### Health Checks

Regularly monitor the health endpoint:
```bash
curl http://localhost:8000/api/health/error-tracking
```

### Alert Testing

Periodically test alert routing:
```bash
curl -X POST http://localhost:8000/api/test/alert
```

### PHI Scrubbing Validation

```typescript
import { validatePHIScrubbing } from './utils/phiScrubber';

// Validate scrubbing is working
const isValid = validatePHIScrubbing();
console.log('PHI scrubbing valid:', isValid);
```

## Troubleshooting

### Common Issues

1. **Sentry DSN Not Configured**
   - Check environment variables
   - Verify DSN format and project access

2. **Alerts Not Sending**
   - Verify webhook URLs and integration keys
   - Check network connectivity
   - Review alert service logs

3. **PHI Leakage**
   - Review scrubbing patterns
   - Test with sample PHI data
   - Update patterns as needed

### Debugging

Enable debug mode in development:
```bash
SENTRY_DEBUG=true
LOG_LEVEL=DEBUG
```

## Security Considerations

1. **Environment Variables**: Store sensitive configuration in secure environment variables
2. **Network Security**: Use HTTPS for all webhook URLs
3. **Access Control**: Limit access to error tracking dashboards
4. **Data Retention**: Configure appropriate retention policies
5. **Regular Audits**: Review error logs for potential PHI exposure

## Performance Impact

- Sentry sampling rates are configured to minimize performance impact
- PHI scrubbing adds minimal overhead
- Alert routing is asynchronous to avoid blocking requests
- Error boundaries prevent cascading failures

## Compliance Checklist

- [ ] PHI scrubbing patterns are comprehensive
- [ ] User anonymization is implemented
- [ ] Session replay is disabled
- [ ] Data retention policies are configured
- [ ] Access controls are in place
- [ ] Regular testing is performed
- [ ] Documentation is up to date

## Future Enhancements

1. **Machine Learning**: Implement ML-based PHI detection
2. **Custom Dashboards**: Create HIPAA-compliant error dashboards
3. **Advanced Alerting**: Implement smart alert grouping and suppression
4. **Integration**: Add support for additional monitoring tools
5. **Automation**: Implement automated PHI pattern updates
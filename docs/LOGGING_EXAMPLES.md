# Logging Examples and Query Guide

## Overview
This document provides examples of how to query and analyze logs from the Mental Health Practice Management System.

## Log Structure
All logs are structured in JSON format with the following common fields:
- `timestamp`: ISO format timestamp
- `level`: Log level (INFO, WARNING, ERROR)
- `logger`: Logger name
- `correlation_id`: Unique request identifier
- `event`: Event type or message

## Correlation ID Verification

### Test Correlation ID Functionality
```bash
# Test with custom correlation ID
curl -H "X-Correlation-ID: test-123" http://localhost:8000/

# Expected response includes correlation_id
{
  "message": "Mental Health PMS API",
  "status": "healthy",
  "correlation_id": "test-123"
}

# Response headers should include:
# x-correlation-id: test-123
```

### Test Auto-Generated Correlation ID
```bash
# Request without correlation ID header
curl http://localhost:8000/health

# System generates UUID-based correlation ID
{
  "status": "healthy",
  "service": "pms-backend",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## PHI Scrubbing Verification

### Test PHI Scrubbing Patterns
```python
# Test SSN scrubbing
from utils.phi_scrubber import scrub_phi_from_string

original = "Patient SSN: 123-45-6789"
scrubbed = scrub_phi_from_string(original)
print(scrubbed)  # Output: "Patient SSN: [SSN-REDACTED]"

# Test email scrubbing
original = "Contact: john.doe@example.com"
scrubbed = scrub_phi_from_string(original)
print(scrubbed)  # Output: "Contact: [EMAIL-REDACTED]"

# Test phone scrubbing
original = "Phone: (555) 123-4567"
scrubbed = scrub_phi_from_string(original)
print(scrubbed)  # Output: "Phone: [PHONE-REDACTED]"
```

### Test Dictionary PHI Scrubbing
```python
from utils.phi_scrubber import scrub_phi_from_dict

data = {
    "patient_name": "John Doe",
    "email": "john@example.com",
    "phone": "555-1234",
    "notes": "Patient has SSN 123-45-6789"
}

scrubbed = scrub_phi_from_dict(data)
print(scrubbed)
# Output:
# {
#     "patient_name": "[REDACTED]",
#     "email": "[REDACTED]", 
#     "phone": "[REDACTED]",
#     "notes": "Patient has SSN [SSN-REDACTED]"
# }
```

## Log Query Examples

### Query by Correlation ID
```bash
# Find all logs for a specific request
grep '"correlation_id":"test-123"' /var/log/pms/app.log

# Using jq for JSON parsing
cat /var/log/pms/app.log | jq 'select(.correlation_id == "test-123")'
```

### Query Request Performance
```bash
# Find slow requests (>1000ms)
cat /var/log/pms/app.log | jq 'select(.duration_ms > 1000)'

# Average request duration
cat /var/log/pms/app.log | jq -s 'map(select(.duration_ms)) | add/length'
```

### Query Error Logs
```bash
# Find all error logs
cat /var/log/pms/app.log | jq 'select(.level == "ERROR")'

# Find errors by correlation ID
cat /var/log/pms/app.log | jq 'select(.level == "ERROR" and .correlation_id == "abc-123")'
```

### Query Audit Logs
```bash
# Find all CRUD operations
cat /var/log/pms/audit.log | jq 'select(.event == "audit_log")'

# Find specific user actions
cat /var/log/pms/audit.log | jq 'select(.user_id == "user_123")'

# Find data access events
cat /var/log/pms/audit.log | jq 'select(.event == "data_access_audit")'
```

### Query Security Events
```bash
# Find authentication events
cat /var/log/pms/audit.log | jq 'select(.event == "security_audit")'

# Find failed login attempts
cat /var/log/pms/audit.log | jq 'select(.auth_event == "LOGIN" and .success == false)'
```

## Elasticsearch Queries (Production)

### Basic Correlation ID Search
```json
{
  "query": {
    "match": {
      "correlation_id": "test-123"
    }
  }
}
```

### Time Range with Correlation ID
```json
{
  "query": {
    "bool": {
      "must": [
        {"match": {"correlation_id": "test-123"}},
        {
          "range": {
            "@timestamp": {
              "gte": "2024-01-01T00:00:00",
              "lte": "2024-01-01T23:59:59"
            }
          }
        }
      ]
    }
  }
}
```

### Aggregation by Status Code
```json
{
  "aggs": {
    "status_codes": {
      "terms": {
        "field": "status_code"
      }
    }
  }
}
```

## Compliance Verification

### PHI Pattern Detection (Should Return No Results)
```bash
# Check for SSN patterns (should be empty)
grep -E '\b\d{3}-\d{2}-\d{4}\b' /var/log/pms/*.log

# Check for email patterns (should be empty)
grep -E '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b' /var/log/pms/*.log

# Check for phone patterns (should be empty)
grep -E '\b\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b' /var/log/pms/*.log
```

### Verify Correlation ID Coverage
```bash
# All request logs should have correlation IDs
cat /var/log/pms/app.log | jq 'select(.request_complete == true and (.correlation_id | length) == 0)'
# Should return empty result
```

### Audit Log Immutability Check
```bash
# All audit logs should be marked immutable
cat /var/log/pms/audit.log | jq 'select(.immutable != true)'
# Should return empty result
```

## Monitoring Queries

### Request Rate
```bash
# Requests per minute
cat /var/log/pms/app.log | jq -r '.timestamp' | cut -c1-16 | sort | uniq -c
```

### Error Rate
```bash
# Error percentage
cat /var/log/pms/app.log | jq -s '
  (map(select(.level == "ERROR")) | length) / length * 100
'
```

### Top Slow Requests
```bash
# Top 10 slowest requests
cat /var/log/pms/app.log | jq -s 'sort_by(.duration_ms) | reverse | .[0:10]'
```

## Testing Checklist

- [x] Requests show up with correlation ID in response body
- [x] Requests show up with correlation ID in response headers  
- [x] PHI patterns are scrubbed from logs (SSN, email, phone)
- [x] Correlation IDs are preserved from request headers
- [x] Auto-generated correlation IDs work when not provided
- [ ] Structured JSON logs are written to files
- [ ] Audit logging functions work correctly
- [ ] Log retention policies are configured
- [ ] Elasticsearch integration works (production)

## Acceptance Criteria Status

✅ **Requests showing up with a trace/correlation ID**: Verified working
✅ **No PHI fields present in logs (spot-check)**: PHI scrubbing verified
✅ **Query examples documented**: This document provides comprehensive examples

## Next Steps

1. Configure log file output for structured logs
2. Set up log rotation and retention policies
3. Deploy Elasticsearch/Fluent Bit stack for production
4. Implement log monitoring and alerting
5. Create log analysis dashboards
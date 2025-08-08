# API Guidelines for HIPAA-Compliant Practice Management System

## Overview

This document establishes comprehensive API standards for the Mental Health Practice Management System, ensuring consistency, security, and HIPAA compliance across all endpoints.

## Table of Contents

1. [General Principles](#general-principles)
2. [OpenAPI Specifications](#openapi-specifications)
3. [Error Handling Standards](#error-handling-standards)
4. [Pagination Standards](#pagination-standards)
5. [Authentication & Authorization](#authentication--authorization)
6. [HIPAA Compliance Requirements](#hipaa-compliance-requirements)
7. [Request/Response Patterns](#requestresponse-patterns)
8. [Idempotency](#idempotency)
9. [Versioning](#versioning)
10. [Testing Requirements](#testing-requirements)

## General Principles

### RESTful Design
- Use HTTP methods semantically (GET, POST, PUT, DELETE, PATCH)
- Resource-oriented URLs with clear hierarchies
- Stateless operations with proper HTTP status codes
- Consistent naming conventions (kebab-case for URLs, snake_case for JSON)

### Security First
- All endpoints require authentication unless explicitly documented
- Role-based access control (RBAC) enforcement
- No PHI in URLs, logs, or error messages
- Correlation IDs for request tracking

### Consistency
- Standardized response formats across all endpoints
- Uniform error handling and status codes
- Consistent pagination patterns
- Predictable field naming and data types

## OpenAPI Specifications

### Documentation Requirements

All API endpoints MUST include:

```yaml
# Example endpoint documentation
paths:
  /api/patients:
    get:
      summary: "List patients with pagination"
      description: "Retrieve a paginated list of patients with optional filtering"
      tags: ["patients"]
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            minimum: 1
            default: 1
        - name: per_page
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 20
      responses:
        '200':
          description: "Successful response"
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PaginatedPatientsResponse'
        '401':
          $ref: '#/components/responses/UnauthorizedError'
        '403':
          $ref: '#/components/responses/ForbiddenError'
```

### Required Fields
- **summary**: Brief description of the endpoint
- **description**: Detailed explanation of functionality
- **tags**: Logical grouping for documentation
- **parameters**: All query parameters, path parameters, and headers
- **responses**: All possible HTTP status codes with examples
- **security**: Authentication requirements

### Schema Definitions

All request/response models MUST be defined in the `components/schemas` section:

```yaml
components:
  schemas:
    Patient:
      type: object
      required: ["id", "created_at", "updated_at"]
      properties:
        id:
          type: string
          format: uuid
          description: "Unique patient identifier"
        created_at:
          type: string
          format: date-time
          description: "Creation timestamp"
        updated_at:
          type: string
          format: date-time
          description: "Last update timestamp"
```

## Error Handling Standards

### Standard Error Response Format

All errors MUST follow this structure:

```json
{
  "error": "ERROR_TYPE",
  "message": "Human-readable error description",
  "correlation_id": "uuid-v4-correlation-id",
  "details": {
    "field_errors": {
      "field_name": ["Validation error message"]
    },
    "error_code": "SPECIFIC_ERROR_CODE"
  }
}
```

### Error Types

| Error Type | HTTP Status | Description |
|------------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `AUTHENTICATION_ERROR` | 401 | Authentication required or failed |
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `NOT_FOUND_ERROR` | 404 | Resource not found |
| `CONFLICT_ERROR` | 409 | Resource conflict (e.g., duplicate) |
| `RATE_LIMIT_ERROR` | 429 | Rate limit exceeded |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected server error |
| `SERVICE_UNAVAILABLE_ERROR` | 503 | Service temporarily unavailable |

### PHI Scrubbing Requirements

- All error messages MUST be scrubbed of PHI
- Use generic error messages for client-facing responses
- Detailed errors logged server-side with correlation IDs
- No patient names, SSNs, or other identifiers in error responses

### Example Error Responses

```json
// Validation Error
{
  "error": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "details": {
    "field_errors": {
      "email": ["Invalid email format"],
      "phone": ["Phone number is required"]
    }
  }
}

// Authorization Error
{
  "error": "AUTHORIZATION_ERROR",
  "message": "Insufficient permissions to access this resource",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440001",
  "details": {
    "required_role": "provider",
    "error_code": "INSUFFICIENT_ROLE"
  }
}
```

## Pagination Standards

### Standard Pagination Format

All paginated endpoints MUST use this response structure:

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 150,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  },
  "correlation_id": "uuid-v4-correlation-id"
}
```

### Query Parameters

- `page`: Page number (1-based, default: 1)
- `per_page`: Items per page (default: 20, max: 100)
- `sort`: Sort field (default: created_at)
- `order`: Sort order (asc/desc, default: desc)

### Implementation Requirements

- Use cursor-based pagination for large datasets
- Include total counts for UI pagination controls
- Validate page boundaries and return appropriate errors
- Support filtering with consistent query parameter patterns

## Authentication & Authorization

### Authentication Requirements

- All endpoints require valid JWT tokens unless explicitly marked as public
- Tokens must include user ID, roles, and expiration
- Support for token refresh and rotation
- Correlation ID tracking for all authenticated requests

### Authorization Patterns

```python
# Role-based access control
@router.get("/patients")
async def list_patients(
    current_user: AuthenticatedUser = Depends(require_auth_dependency),
    _: None = Depends(require_role("provider"))
):
    # Endpoint implementation
    pass

# Resource-based access control
@router.get("/patients/{patient_id}")
async def get_patient(
    patient_id: UUID,
    current_user: AuthenticatedUser = Depends(require_auth_dependency),
    _: None = Depends(require_patient_access(patient_id))
):
    # Endpoint implementation
    pass
```

### Required Headers

- `Authorization: Bearer <jwt-token>`
- `X-Correlation-ID: <uuid>` (optional, generated if not provided)
- `Content-Type: application/json` (for POST/PUT/PATCH)

## HIPAA Compliance Requirements

### PHI Protection

- No PHI in URLs, query parameters, or logs
- All PHI encrypted in transit and at rest
- Audit logging for all PHI access
- Automatic PHI scrubbing in error responses

### Audit Requirements

```python
# Audit logging example
@audit_log(resource_type="patient", action="read")
async def get_patient(patient_id: UUID):
    # Implementation logs:
    # - User ID
    # - Resource accessed
    # - Timestamp
    # - IP address
    # - User agent
    pass
```

### Data Minimization

- Return only necessary fields in responses
- Support field selection via query parameters
- Implement role-based field filtering
- Use DTOs to control data exposure

## Request/Response Patterns

### Standard Response Wrapper

```json
{
  "data": {}, // or [] for lists
  "correlation_id": "uuid-v4",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### List Responses

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 150,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  },
  "correlation_id": "uuid-v4",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Field Naming Conventions

- Use `snake_case` for JSON fields
- Use `kebab-case` for URL paths
- Use descriptive, unambiguous field names
- Include units in field names when applicable (e.g., `duration_minutes`)

## Idempotency

### Idempotency Key Support

For state-changing operations (POST, PUT, PATCH), support idempotency keys:

```http
POST /api/patients
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com"
}
```

### Implementation Requirements

- Store idempotency keys with request fingerprints
- Return cached responses for duplicate requests
- Expire idempotency keys after 24 hours
- Handle concurrent requests with same key

## Versioning

### API Versioning Strategy

- Use URL path versioning: `/api/v1/patients`
- Maintain backward compatibility for at least 2 versions
- Deprecation notices in response headers
- Clear migration guides for version changes

### Version Headers

```http
API-Version: 1.0
Deprecation: "2024-12-31"
Sunset: "2025-03-31"
```

## Testing Requirements

### Contract Testing

- All endpoints must have contract tests
- Validate OpenAPI schema compliance
- Test error response formats
- Verify pagination behavior

### Security Testing

- Authentication bypass attempts
- Authorization boundary testing
- PHI exposure validation
- Rate limiting verification

### Performance Testing

- Response time requirements (< 200ms for simple queries)
- Pagination performance with large datasets
- Concurrent request handling
- Memory usage optimization

## Implementation Checklist

For each new endpoint:

- [ ] OpenAPI documentation complete
- [ ] Error handling implemented
- [ ] Pagination (if applicable)
- [ ] Authentication/authorization
- [ ] PHI scrubbing verified
- [ ] Audit logging implemented
- [ ] Unit tests written
- [ ] Integration tests written
- [ ] Contract tests written
- [ ] Performance tested
- [ ] Security reviewed

## Examples

### Complete Endpoint Example

```python
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from uuid import UUID

from middleware.auth_middleware import AuthenticatedUser, require_auth_dependency
from utils.response_models import APIResponse, ListResponse
from utils.error_handlers import APIError
from utils.audit_logger import audit_log

router = APIRouter(prefix="/patients", tags=["patients"])

@router.get(
    "/",
    response_model=ListResponse[PatientResponse],
    summary="List patients",
    description="Retrieve a paginated list of patients with optional filtering"
)
@audit_log(resource_type="patient", action="list")
async def list_patients(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term"),
    current_user: AuthenticatedUser = Depends(require_auth_dependency),
    db: AsyncSession = Depends(get_db)
):
    """List patients with pagination and search."""
    try:
        # Implementation here
        patients, total = await patient_service.list_patients(
            page=page,
            per_page=per_page,
            search=search,
            user=current_user
        )
        
        return create_list_response(
            data=patients,
            page=page,
            per_page=per_page,
            total_items=total
        )
    except Exception as e:
        logger.error(f"Error listing patients: {str(e)}")
        raise APIError(
            message="Failed to retrieve patients",
            error_type="INTERNAL_SERVER_ERROR",
            status_code=500
        )
```

---

**Document Version**: 1.0  
**Last Updated**: January 2024  
**Owner**: API Team  
**Review Cycle**: Quarterly
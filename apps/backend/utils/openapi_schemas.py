"""OpenAPI schema utilities for enhanced API documentation.

This module provides utilities for generating comprehensive OpenAPI schemas
with HIPAA compliance considerations and standardized error responses.
"""

from typing import Any, Dict, List, Optional, Type, Union

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

# Error handlers imported for reference in documentation
from utils.pagination import PaginationMeta


class ErrorResponseSchema(BaseModel):
    """Standard error response schema."""

    error: str
    message: str
    correlation_id: str
    details: Optional[Dict[str, Any]] = None


class ValidationErrorSchema(ErrorResponseSchema):
    """Validation error response schema."""

    details: Dict[str, List[str]]


class AuthorizationErrorSchema(ErrorResponseSchema):
    """Authorization error response schema."""

    details: Optional[Dict[str, Union[str, bool]]] = None


class RateLimitErrorSchema(ErrorResponseSchema):
    """Rate limit error response schema."""

    details: Optional[Dict[str, int]] = None


class PaginatedResponseSchema(BaseModel):
    """Generic paginated response schema."""

    success: bool = True
    data: List[Any]
    pagination: PaginationMeta
    message: Optional[str] = None


def get_standard_responses() -> Dict[Union[int, str], Dict[str, Any]]:
    """Get standard error responses for OpenAPI documentation.

    Returns:
        Dict: Standard error response schemas
    """
    return {
        400: {
            "description": "Validation Error",
            "model": ValidationErrorSchema,
            "content": {
                "application/json": {
                    "example": {
                        "error": "VALIDATION_ERROR",
                        "message": "Request validation failed",
                        "correlation_id": ("123e4567-e89b-12d3-a456-426614174000"),
                        "details": {
                            "field_errors": {
                                "email": ["Invalid email format"],
                                "age": ["Must be greater than 0"],
                            }
                        },
                    }
                }
            },
        },
        401: {
            "description": "Authentication Error",
            "model": ErrorResponseSchema,
            "content": {
                "application/json": {
                    "example": {
                        "error": "AUTHENTICATION_ERROR",
                        "message": "Authentication required",
                        "correlation_id": ("123e4567-e89b-12d3-a456-426614174000"),
                        "details": {},
                    }
                }
            },
        },
        403: {
            "description": "Authorization Error",
            "model": AuthorizationErrorSchema,
            "content": {
                "application/json": {
                    "example": {
                        "error": "AUTHORIZATION_ERROR",
                        "message": "Insufficient permissions",
                        "correlation_id": ("123e4567-e89b-12d3-a456-426614174000"),
                        "details": {
                            "required_role": "admin",
                            "error_code": "INSUFFICIENT_ROLE",
                        },
                    }
                }
            },
        },
        404: {
            "description": "Not Found Error",
            "model": ErrorResponseSchema,
            "content": {
                "application/json": {
                    "example": {
                        "error": "NOT_FOUND_ERROR",
                        "message": "Resource not found",
                        "correlation_id": ("123e4567-e89b-12d3-a456-426614174000"),
                        "details": {},
                    }
                }
            },
        },
        409: {
            "description": "Conflict Error",
            "model": ErrorResponseSchema,
            "content": {
                "application/json": {
                    "example": {
                        "error": "CONFLICT_ERROR",
                        "message": "Resource conflict",
                        "correlation_id": ("123e4567-e89b-12d3-a456-426614174000"),
                        "details": {},
                    }
                }
            },
        },
        429: {
            "description": "Rate Limit Error",
            "model": RateLimitErrorSchema,
            "content": {
                "application/json": {
                    "example": {
                        "error": "RATE_LIMIT_ERROR",
                        "message": "Rate limit exceeded",
                        "correlation_id": ("123e4567-e89b-12d3-a456-426614174000"),
                        "details": {"retry_after_seconds": 60},
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error",
            "model": ErrorResponseSchema,
            "content": {
                "application/json": {
                    "example": {
                        "error": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                        "correlation_id": ("123e4567-e89b-12d3-a456-426614174000"),
                        "details": {},
                    }
                }
            },
        },
        503: {
            "description": "Service Unavailable Error",
            "model": ErrorResponseSchema,
            "content": {
                "application/json": {
                    "example": {
                        "error": "SERVICE_UNAVAILABLE_ERROR",
                        "message": "Service temporarily unavailable",
                        "correlation_id": ("123e4567-e89b-12d3-a456-426614174000"),
                        "details": {"retry_after_seconds": 300},
                    }
                }
            },
        },
    }


def get_paginated_response_schema(
    item_model: Type[BaseModel], description: str = "Paginated response"
) -> Dict[str, Any]:
    """Generate OpenAPI schema for paginated responses.

    Args:
        item_model: Pydantic model for individual items
        description: Description for the response

    Returns:
        Dict: OpenAPI schema for paginated response
    """
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": True},
                        "data": {"type": "array", "items": item_model.schema()},
                        "pagination": PaginationMeta.schema(),
                        "message": {
                            "type": "string",
                            "example": "Retrieved items successfully",
                        },
                    },
                    "required": ["success", "data", "pagination"],
                }
            }
        },
    }


def enhance_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """Enhance OpenAPI schema with HIPAA compliance information.

    Args:
        app: FastAPI application instance

    Returns:
        Dict: Enhanced OpenAPI schema
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Mental Health Practice Management System API",
        version="1.0.0",
        description="""
        HIPAA-compliant API for mental health practice management.

        ## Security

        This API implements comprehensive security measures:
        - JWT-based authentication
        - Role-based access control (RBAC)
        - PHI scrubbing in logs and error messages
        - Audit logging for all operations
        - Rate limiting and request validation

        ## HIPAA Compliance

        All endpoints are designed with HIPAA compliance in mind:
        - No PHI in error messages or logs
        - Comprehensive audit trails
        - Secure data handling and transmission
        - Access controls and user authentication

        ## Error Handling

        All errors follow a standardized format with correlation IDs
        for tracking and debugging while maintaining patient privacy.

        ## Pagination

        List endpoints support standardized pagination with metadata
        including total counts, page information, and navigation flags.

        ## Idempotency

        Critical operations support idempotency keys to ensure
        safe retry of operations without duplicate side effects.
        """,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token for API authentication",
        }
    }

    # Add global security requirement
    openapi_schema["security"] = [{"BearerAuth": []}]

    # Add custom headers
    openapi_schema["components"]["parameters"] = {
        "IdempotencyKey": {
            "name": "Idempotency-Key",
            "in": "header",
            "required": False,
            "schema": {"type": "string", "maxLength": 255},
            "description": "Unique key for idempotent operations",
        },
        "CorrelationId": {
            "name": "X-Correlation-ID",
            "in": "header",
            "required": False,
            "schema": {"type": "string"},
            "description": "Request correlation ID for tracking",
        },
    }

    # Add HIPAA compliance tags
    openapi_schema["tags"] = [
        {
            "name": "Authentication",
            "description": "User authentication and authorization",
        },
        {"name": "Patients", "description": "Patient management (HIPAA-protected)"},
        {"name": "Providers", "description": "Healthcare provider management"},
        {
            "name": "Appointments",
            "description": "Appointment scheduling and management",
        },
        {
            "name": "Notes",
            "description": "Clinical notes and documentation (HIPAA-protected)",
        },
        {"name": "Admin", "description": "Administrative functions"},
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

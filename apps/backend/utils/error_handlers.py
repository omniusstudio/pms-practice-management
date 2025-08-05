"""Standardized error handling utilities for API endpoints."""

import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from middleware.correlation import get_correlation_id
from utils.audit_logger import log_authentication_event

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Standardized error response schema."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    correlation_id: str = Field(..., description="Request correlation ID")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )


class APIError(Exception):
    """Base API error with standardized handling."""

    def __init__(
        self,
        message: str,
        error_type: str = "API_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.details = details or {}
        self.correlation_id = correlation_id or str(uuid4())
        super().__init__(message)


class ValidationError(APIError):
    """Validation error with 400 status."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_type="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
            correlation_id=correlation_id,
        )


class AuthenticationError(APIError):
    """Authentication error with 401 status."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_type="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
            correlation_id=correlation_id,
        )


class AuthorizationError(APIError):
    """Authorization error with 403 status."""

    def __init__(
        self,
        message: str = "Access denied",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_type="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
            correlation_id=correlation_id,
        )


class NotFoundError(APIError):
    """Not found error with 404 status."""

    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_type="NOT_FOUND_ERROR",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
            correlation_id=correlation_id,
        )


class DatabaseError(APIError):
    """Database error with 500 status."""

    def __init__(
        self,
        message: str = "Database operation failed",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_type="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            correlation_id=correlation_id,
        )


def handle_database_error(
    e: Exception, correlation_id: str, operation: str = "database operation"
) -> APIError:
    """Convert database exceptions to standardized API errors."""

    if isinstance(e, IntegrityError):
        return ValidationError(
            message="Data integrity constraint violation",
            details={"operation": operation, "constraint_error": str(e.orig)},
            correlation_id=correlation_id,
        )
    elif isinstance(e, SQLAlchemyError):
        return DatabaseError(
            message=f"Database {operation} failed",
            details={"operation": operation, "error": str(e)},
            correlation_id=correlation_id,
        )
    else:
        return APIError(
            message=f"Unexpected error during {operation}",
            details={"operation": operation, "error": str(e)},
            correlation_id=correlation_id,
        )


def log_and_raise_error(
    error: APIError,
    db_session=None,
    user_id: Optional[str] = None,
    operation: Optional[str] = None,
) -> None:
    """Log error and perform cleanup before raising."""

    # Rollback database transaction if provided
    if db_session:
        try:
            db_session.rollback()
        except Exception:
            pass  # Ignore rollback errors

    # Log the error with structured logging
    logger.error(
        f"{error.error_type}: {error.message}",
        extra={
            "correlation_id": error.correlation_id,
            "error_type": error.error_type,
            "status_code": error.status_code,
            "details": error.details,
            "operation": operation,
        },
    )

    # Log authentication failures for audit
    if isinstance(error, (AuthenticationError, AuthorizationError)) and user_id:
        try:
            event_type = (
                "AUTHENTICATION_FAILED"
                if isinstance(error, AuthenticationError)
                else "AUTHORIZATION_FAILED"
            )
            log_authentication_event(
                event_type=event_type,
                user_id=user_id,
                correlation_id=error.correlation_id,
                success=False,
                failure_reason=f"{error.message} (operation: {operation})",
            )
        except Exception:
            pass  # Don't fail on audit logging errors

    raise HTTPException(
        status_code=error.status_code,
        detail={
            "error": error.error_type,
            "message": error.message,
            "correlation_id": error.correlation_id,
            "details": error.details,
        },
    )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Global API error handler for FastAPI."""

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_type,
            "message": exc.message,
            "correlation_id": exc.correlation_id,
            "details": exc.details,
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with proper logging."""

    correlation_id = str(uuid4())
    try:
        correlation_id = get_correlation_id()
    except Exception:
        pass

    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "correlation_id": correlation_id,
            "error_type": "INTERNAL_SERVER_ERROR",
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "correlation_id": correlation_id,
        },
    )

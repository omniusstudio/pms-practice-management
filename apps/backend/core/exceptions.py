"""Custom exceptions for the PMS application.

This module defines HIPAA-compliant custom exceptions with proper logging
and error handling for authentication, authorization, and validation errors.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PMSException(Exception):
    """Base exception class for PMS application."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

        # Log the exception (without PHI)
        logger.error(
            f"PMSException: {message}",
            extra={"error_code": error_code, "exception_type": self.__class__.__name__},
        )


class AuthenticationError(PMSException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "AUTH_FAILED",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)


class AuthorizationError(PMSException):
    """Raised when authorization fails."""

    def __init__(
        self,
        message: str = "Authorization failed",
        error_code: str = "AUTHZ_FAILED",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)


class ValidationError(PMSException):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        error_code: str = "VALIDATION_FAILED",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)


class TokenError(PMSException):
    """Raised when token operations fail."""

    def __init__(
        self,
        message: str = "Token operation failed",
        error_code: str = "TOKEN_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)


class SessionError(PMSException):
    """Raised when session operations fail."""

    def __init__(
        self,
        message: str = "Session operation failed",
        error_code: str = "SESSION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)


class ConfigurationError(PMSException):
    """Raised when configuration is invalid."""

    def __init__(
        self,
        message: str = "Configuration error",
        error_code: str = "CONFIG_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)


class DatabaseError(PMSException):
    """Raised when database operations fail."""

    def __init__(
        self,
        message: str = "Database operation failed",
        error_code: str = "DB_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)


class ExternalServiceError(PMSException):
    """Raised when external service calls fail."""

    def __init__(
        self,
        message: str = "External service error",
        error_code: str = "EXTERNAL_SERVICE_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)


class RateLimitError(PMSException):
    """Raised when rate limits are exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        error_code: str = "RATE_LIMIT_EXCEEDED",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)


class HIPAAComplianceError(PMSException):
    """Raised when HIPAA compliance requirements are violated."""

    def __init__(
        self,
        message: str = "HIPAA compliance violation",
        error_code: str = "HIPAA_VIOLATION",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)

        # Log HIPAA violations with high priority
        logger.critical(
            f"HIPAA Compliance Violation: {message}",
            extra={"error_code": error_code, "compliance_issue": True},
        )

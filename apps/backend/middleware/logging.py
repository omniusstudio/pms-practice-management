"""Logging middleware for correlation ID tracking and request logging."""

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation IDs to requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation ID tracking."""
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        # Add correlation ID to request state
        request.state.correlation_id = correlation_id

        # Bind correlation ID to logger context
        logger_with_context = logger.bind(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            user_agent=request.headers.get("user-agent", "unknown"),
        )

        # Log request start
        start_time = time.time()
        logger_with_context.info(
            "Request started", request_start=True, timestamp=start_time
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate request duration
            duration = time.time() - start_time

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            # Log successful request completion
            logger_with_context.info(
                "Request completed",
                request_complete=True,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

            return response

        except Exception as exc:
            # Calculate request duration for failed requests
            duration = time.time() - start_time

            # Log request failure (no PHI in error messages)
            logger_with_context.error(
                "Request failed",
                request_error=True,
                error_type=type(exc).__name__,
                duration_ms=round(duration * 1000, 2),
                # Note: exc details are scrubbed to prevent PHI exposure
            )

            # Re-raise the exception
            raise


def get_correlation_id(request: Request) -> str:
    """Get correlation ID from request state."""
    return getattr(request.state, "correlation_id", "unknown")

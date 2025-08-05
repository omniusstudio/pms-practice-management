"""Correlation ID middleware for request tracking."""

import uuid
from contextvars import ContextVar
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Context variable to store correlation ID
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation IDs for request tracking.

    This middleware:
    1. Extracts correlation ID from X-Correlation-ID header
    2. Generates a new one if not provided
    3. Stores it in context for use throughout the request
    4. Adds it to the response headers
    """

    def __init__(self, app, header_name: str = "X-Correlation-ID"):
        """Initialize correlation ID middleware.

        Args:
            app: FastAPI application
            header_name: Header name for correlation ID
        """
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add correlation ID.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response with correlation ID header
        """
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get(self.header_name, str(uuid.uuid4()))

        # Store in context
        token = _correlation_id.set(correlation_id)

        try:
            # Process request
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers[self.header_name] = correlation_id

            return response

        finally:
            # Clean up context
            _correlation_id.reset(token)


def get_correlation_id() -> str:
    """Get current correlation ID from context.

    Returns:
        Current correlation ID or generates new one if not set
    """
    correlation_id = _correlation_id.get()
    if correlation_id is None:
        # Fallback - generate new correlation ID
        correlation_id = str(uuid.uuid4())
        _correlation_id.set(correlation_id)

    return correlation_id


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context.

    Args:
        correlation_id: Correlation ID to set
    """
    _correlation_id.set(correlation_id)

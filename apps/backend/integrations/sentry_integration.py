"""Sentry integration for FastAPI application."""

import logging
import os

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from services.alert_service import AlertSeverity, get_alert_service
from services.sentry_service import get_sentry_service
from utils.phi_scrubber import scrub_phi

logger = logging.getLogger(__name__)


def init_sentry(app: FastAPI) -> None:
    """Initialize Sentry integration for FastAPI app.

    Args:
        app: FastAPI application instance
    """
    sentry_service = get_sentry_service()
    alert_service = get_alert_service()

    # Initialize Sentry
    sentry_service.initialize()

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Global exception handler with Sentry and alert integration.

        Args:
            request: FastAPI request object
            exc: Exception that occurred

        Returns:
            JSON error response
        """
        # Get correlation ID from request headers
        correlation_id = request.headers.get("X-Correlation-ID")

        # Get user ID from request (if authenticated)
        user_id = getattr(request.state, "user_id", None)

        # Capture exception in Sentry
        sentry_service.capture_exception(
            exc,
            extra_context={
                "request_url": str(request.url),
                "request_method": request.method,
                "correlation_id": correlation_id,
                "user_id": user_id,
            },
        )

        # Send alert for critical errors
        try:
            await alert_service.send_error_alert(
                exception=exc,
                severity=AlertSeverity.CRITICAL,
                user_id=user_id,
                correlation_id=correlation_id,
                extra_context={
                    "request_url": str(request.url),
                    "request_method": request.method,
                },
            )
        except Exception as alert_error:
            logger.error(f"Failed to send error alert: {alert_error}")

        # Return sanitized error response
        error_message = "An internal server error occurred"

        # In development, include more details
        if os.getenv("ENVIRONMENT") == "development":
            error_message = scrub_phi(str(exc))

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": error_message,
                "correlation_id": correlation_id,
            },
        )

    @app.middleware("http")
    async def sentry_middleware(request: Request, call_next):
        """Middleware to add request context to Sentry.

        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler

        Returns:
            Response from next handler
        """
        # Add correlation ID if not present
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            import uuid

            correlation_id = str(uuid.uuid4())
            request.state.correlation_id = correlation_id

        # Set Sentry context using SDK directly
        # sentry_sdk already imported at module level
        with sentry_sdk.push_scope() as scope:
            user_id = getattr(request.state, "user_id", None)
            if user_id:
                scope.set_user({"id": f"user_{hash(user_id) % 10000:04d}"})
            scope.set_tag("correlation_id", correlation_id)

        # Add request breadcrumb
        sentry_sdk.add_breadcrumb(
            message=f"{request.method} {request.url.path}",
            category="request",
            level="info",
            data={
                "method": request.method,
                "url": str(request.url),
                "correlation_id": correlation_id,
            },
        )

        response = await call_next(request)

        # Add response breadcrumb
        sentry_sdk.add_breadcrumb(
            message=f"Response {response.status_code}",
            category="response",
            level="info" if response.status_code < 400 else "warning",
            data={
                "status_code": response.status_code,
                "correlation_id": correlation_id,
            },
        )

        return response


def add_error_tracking_routes(app: FastAPI) -> None:
    """Add error tracking test routes.

    Args:
        app: FastAPI application instance
    """
    logger.info("Adding error tracking routes...")
    try:
        sentry_service = get_sentry_service()
        alert_service = get_alert_service()
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

    logger.info("Registering /api/test/sentry-error endpoint")

    @app.post("/api/test/sentry-error")
    async def test_sentry_error(request: Request):
        """Test endpoint to generate Sentry error.

        Returns:
            Test error response
        """
        correlation_id = getattr(request.state, "correlation_id", None)

        # Create test exception
        try:
            raise ValueError(
                "Test error for Sentry validation. "
                "PHI test: Patient John Doe SSN 123-45-6789"
            )
        except ValueError as e:
            sentry_service.capture_exception(
                e,
                extra_context={
                    "test_type": "sentry_validation",
                    "correlation_id": correlation_id,
                },
            )
            raise

    @app.post("/api/test/alert")
    async def test_alert(request: Request):
        """Test endpoint to generate alert.

        Returns:
            Alert test response
        """
        correlation_id = getattr(request.state, "correlation_id", None)

        # Send test alert
        results = await alert_service.send_test_alert()

        return {
            "message": "Test alert sent",
            "results": results,
            "correlation_id": correlation_id,
        }

    @app.post("/api/test/error-with-alert")
    async def test_error_with_alert(request: Request):
        """Test endpoint to generate error with alert.

        Returns:
            Error with alert test response
        """
        correlation_id = getattr(request.state, "correlation_id", None)
        user_id = getattr(request.state, "user_id", "test-user-123")

        # Create test exception
        test_exception = RuntimeError(
            "Test critical error with alert. "
            "PHI test: Patient Jane Smith DOB 1990-01-01"
        )

        # Capture in Sentry
        sentry_service.capture_exception(
            test_exception,
            extra_context={
                "test_type": "error_with_alert",
                "correlation_id": correlation_id,
                "user_id": user_id,
            },
        )

        # Send alert
        alert_results = await alert_service.send_error_alert(
            exception=test_exception,
            severity=AlertSeverity.CRITICAL,
            user_id=user_id,
            correlation_id=correlation_id,
            extra_context={
                "test_type": "error_with_alert",
                "endpoint": "/api/test/error-with-alert",
            },
        )

        return {
            "message": "Test error captured and alert sent",
            "alert_results": alert_results,
            "correlation_id": correlation_id,
        }

    @app.get("/api/health/error-tracking")
    async def error_tracking_health():
        """Health check for error tracking services.

        Returns:
            Health status of error tracking components
        """
        health_status = {
            "sentry": {
                "configured": bool(os.getenv("SENTRY_DSN")),
                "environment": os.getenv("SENTRY_ENVIRONMENT", "development"),
            },
            "alerts": {
                "slack_configured": bool(os.getenv("SLACK_WEBHOOK_URL")),
                "pagerduty_configured": bool(os.getenv("PAGERDUTY_INTEGRATION_KEY")),
            },
        }

        return {
            "status": "healthy",
            "components": health_status,
        }

    logger.info("Error tracking routes added successfully")

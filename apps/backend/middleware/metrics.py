"""Prometheus metrics middleware for HIPAA-compliant monitoring."""

import time
from typing import Callable

import structlog
from fastapi import Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from utils.phi_scrubber import scrub_phi_from_string

logger = structlog.get_logger()

# RED Metrics (Rate, Errors, Duration)
REQUEST_COUNT = Counter(
    "pms_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code", "environment"],
)

REQUEST_DURATION = Histogram(
    "pms_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "environment"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

ERROR_COUNT = Counter(
    "pms_http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "error_type", "environment"],
)

# USE Metrics (Utilization, Saturation, Errors)
ACTIVE_REQUESTS = Gauge(
    "pms_http_requests_active", "Currently active HTTP requests", ["environment"]
)

AUDIT_EVENTS = Counter(
    "pms_audit_events_total",
    "Total audit events",
    ["event_type", "resource_type", "environment"],
)

PHI_SCRUB_COUNT = Counter(
    "pms_phi_scrub_total",
    "Total PHI scrubbing operations",
    ["scrub_type", "environment"],
)

# Business Metrics
USER_ACTIONS = Counter(
    "pms_user_actions_total",
    "Total user actions",
    ["action_type", "resource_type", "environment"],
)

AUTH_EVENTS = Counter(
    "pms_auth_events_total",
    "Authentication events",
    ["event_type", "success", "environment"],
)


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for all HTTP requests."""

    def __init__(self, app, environment: str = "development"):
        super().__init__(app)
        self.environment = environment

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        # Skip metrics collection for the metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        # Scrub PHI from endpoint path for safe labeling
        safe_endpoint = scrub_phi_from_string(
            request.url.path, use_centralized_config=True
        )
        method = request.method

        # Track active requests
        ACTIVE_REQUESTS.labels(environment=self.environment).inc()

        start_time = time.time()
        status_code = "500"  # Default to error in case of exception

        try:
            response = await call_next(request)
            status_code = str(response.status_code)

            # Record successful request
            REQUEST_COUNT.labels(
                method=method,
                endpoint=safe_endpoint,
                status_code=status_code,
                environment=self.environment,
            ).inc()

            return response

        except Exception as exc:
            # Record error metrics
            error_type = type(exc).__name__
            ERROR_COUNT.labels(
                method=method,
                endpoint=safe_endpoint,
                error_type=error_type,
                environment=self.environment,
            ).inc()

            # Log error for debugging (PHI-safe)
            logger.error(
                "Request failed in metrics middleware",
                method=method,
                endpoint=safe_endpoint,
                error_type=error_type,
                correlation_id=getattr(request.state, "correlation_id", "unknown"),
            )

            raise

        finally:
            # Record request duration
            duration = time.time() - start_time
            REQUEST_DURATION.labels(
                method=method, endpoint=safe_endpoint, environment=self.environment
            ).observe(duration)

            # Decrement active requests
            ACTIVE_REQUESTS.labels(environment=self.environment).dec()

        return response

    def _scrub_endpoint_path(self, path: str) -> str:
        """Scrub PHI from endpoint path for metrics labels."""
        # Remove query parameters that might contain PHI
        if "?" in path:
            path = path.split("?")[0]

        # Scrub any remaining PHI patterns
        scrubbed_path = scrub_phi_from_string(path, use_centralized_config=True)

        return scrubbed_path


def record_audit_event(
    event_type: str, resource_type: str, environment: str = "development"
):
    """Record audit event metric."""
    # Scrub PHI from labels using centralized config
    scrubbed_event_type = scrub_phi_from_string(event_type, use_centralized_config=True)
    scrubbed_resource_type = scrub_phi_from_string(
        resource_type, use_centralized_config=True
    )

    AUDIT_EVENTS.labels(
        event_type=scrubbed_event_type,
        resource_type=scrubbed_resource_type,
        environment=environment,
    ).inc()


def record_user_action(
    action_type: str, resource_type: str, environment: str = "development"
):
    """Record user action metric."""
    # Scrub PHI from labels using centralized config
    scrubbed_action_type = scrub_phi_from_string(
        action_type, use_centralized_config=True
    )
    scrubbed_resource_type = scrub_phi_from_string(
        resource_type, use_centralized_config=True
    )

    USER_ACTIONS.labels(
        action_type=scrubbed_action_type,
        resource_type=scrubbed_resource_type,
        environment=environment,
    ).inc()


def record_auth_event(event_type: str, success: bool, environment: str = "development"):
    """Record authentication event metric."""
    AUTH_EVENTS.labels(
        event_type=event_type, success=str(success).lower(), environment=environment
    ).inc()


def record_phi_scrub(scrub_type: str, environment: str = "development"):
    """Record PHI scrubbing operation metric."""
    PHI_SCRUB_COUNT.labels(scrub_type=scrub_type, environment=environment).inc()


async def metrics_endpoint(request: Request) -> StarletteResponse:
    """Prometheus metrics endpoint."""
    metrics_data = generate_latest()
    return StarletteResponse(content=metrics_data, media_type=CONTENT_TYPE_LATEST)

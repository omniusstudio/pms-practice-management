"""Security middleware for HIPAA-compliant encryption in-transit/at-rest."""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

from config.security_config import SecurityConfig, get_hsts_header, get_security_config

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce security headers and HTTPS redirection."""

    def __init__(self, app, security_config: SecurityConfig | None = None):
        super().__init__(app)
        self.security_config = security_config or get_security_config()
        logger.info(
            "Security middleware initialized",
            extra={
                "tls_min_version": self.security_config.tls_min_version,
                "hsts_enabled": True,
                "secure_cookies": (self.security_config.cookie_secure),
            },
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add security headers to response."""

        # Check if HTTPS is required and redirect if necessary
        if self._should_redirect_to_https(request):
            return self._redirect_to_https(request)

        # Process the request
        response = await call_next(request)

        # Add security headers
        self._add_security_headers(response)

        # Configure secure cookies
        self._configure_secure_cookies(response)

        return response

    def _should_redirect_to_https(self, request: Request) -> bool:
        """Check if request should be redirected to HTTPS."""
        import os

        # Skip HTTPS redirect for health checks and local development
        if request.url.path in ["/health", "/healthz", "/readyz"]:
            return False

        # Skip HTTPS redirect in test environment
        environment = os.getenv("ENVIRONMENT", "development")
        if environment in ["test", "development"]:
            return False

        # Check if running in production and not using HTTPS
        is_production = request.headers.get("x-forwarded-proto") != "https"
        client_host = (
            getattr(request.client, "host", "unknown") if request.client else "unknown"
        )
        is_local = client_host in ["127.0.0.1", "localhost"]

        return is_production and not is_local and not request.url.scheme == "https"

    def _redirect_to_https(self, request: Request) -> RedirectResponse:
        """Redirect HTTP request to HTTPS."""
        https_url = request.url.replace(scheme="https")
        logger.info(
            "Redirecting to HTTPS",
            extra={
                "original_url": str(request.url),
                "https_url": str(https_url),
                "client_ip": (
                    getattr(request.client, "host", "unknown")
                    if request.client
                    else "unknown"
                ),
            },
        )
        return RedirectResponse(url=str(https_url), status_code=301)

    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response."""
        # Add HSTS header
        hsts_header = get_hsts_header(self.security_config)
        response.headers["Strict-Transport-Security"] = hsts_header

        # Add other security headers
        for header_name, header_value in self.security_config.security_headers.items():
            response.headers[header_name] = header_value

        # Add cache control for sensitive endpoints
        if self._is_sensitive_endpoint(response):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

    def _configure_secure_cookies(self, response: Response) -> None:
        """Configure secure cookie settings."""
        # This will be handled by session middleware
        # but we can add additional cookie security here if needed
        pass

    def _is_sensitive_endpoint(self, response: Response) -> bool:
        """Check if the endpoint contains sensitive data."""
        # Add logic to identify sensitive endpoints
        # For now, assume all API endpoints are sensitive
        return True


class TLSEnforcementMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce TLS version requirements."""

    def __init__(self, app, security_config: SecurityConfig | None = None):
        super().__init__(app)
        self.security_config = security_config or get_security_config()
        logger.info(
            "TLS enforcement middleware initialized",
            extra={
                "min_tls_version": self.security_config.tls_min_version,
                "allowed_ciphers": (len(self.security_config.tls_ciphers)),
            },
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Enforce TLS version requirements."""

        # Check TLS version if available in headers
        tls_version = request.headers.get("x-forwarded-tls-version")
        if tls_version and not self._is_tls_version_allowed(tls_version):
            logger.warning(
                "Rejected request with insufficient TLS version",
                extra={
                    "client_tls_version": tls_version,
                    "required_min_version": (self.security_config.tls_min_version),
                    "client_ip": (
                        getattr(request.client, "host", "unknown")
                        if request.client
                        else "unknown"
                    ),
                },
            )
            return Response(
                content=("TLS version not supported. Minimum required: TLS 1.2"),
                status_code=426,  # Upgrade Required
                headers={"Upgrade": "TLS/1.2, TLS/1.3"},
            )

        return await call_next(request)

    def _is_tls_version_allowed(self, tls_version: str) -> bool:
        """Check if TLS version meets minimum requirements."""
        # Map TLS versions to numeric values for comparison
        tls_versions = {
            "TLSv1.0": 1.0,
            "TLSv1.1": 1.1,
            "TLSv1.2": 1.2,
            "TLSv1.3": 1.3,
        }

        client_version = tls_versions.get(tls_version, 0.0)
        min_version = tls_versions.get(self.security_config.tls_min_version, 1.2)

        return client_version >= min_version


def add_security_middleware(app, security_config: SecurityConfig | None = None):
    """Add security middleware to FastAPI application."""
    config = security_config or get_security_config()

    # Add TLS enforcement middleware
    app.add_middleware(TLSEnforcementMiddleware, security_config=config)

    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware, security_config=config)

    logger.info(
        "Security middleware added to application",
        extra={
            "middlewares": [
                "TLSEnforcementMiddleware",
                "SecurityHeadersMiddleware",
            ],
            "tls_min_version": config.tls_min_version,
            "hsts_max_age": config.hsts_max_age,
        },
    )

"""Enhanced audit logging middleware for HIPAA-compliant audit trails."""

import time
from typing import Any, Callable, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from middleware.correlation import get_correlation_id
from services.feature_flags_service import is_enabled
from utils.audit_logger import log_crud_action, log_data_access, log_system_event
from utils.phi_scrubber import scrub_phi


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic audit logging of API requests."""

    def __init__(self, app, audit_sensitive_endpoints: bool = True):
        """Initialize audit middleware.

        Args:
            app: FastAPI application instance
            audit_sensitive_endpoints: Whether to audit sensitive endpoints
        """
        super().__init__(app)
        # Middleware initialized
        self.audit_sensitive_endpoints = audit_sensitive_endpoints
        self.sensitive_resources = {
            "clients",
            "patients",
            "providers",
            "notes",
            "appointments",
            "ledger",
        }
        self.crud_methods = {
            "POST": "CREATE",
            "PUT": "UPDATE",
            "PATCH": "UPDATE",
            "DELETE": "DELETE",
            "GET": "read",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and response with audit logging."""
        start_time = time.time()
        correlation_id = get_correlation_id()

        # Extract user info from request
        user_id = self._extract_user_id(request)

        # Determine if this is a sensitive resource operation
        resource_info = self._extract_resource_info(request)

        # Process request
        response = await call_next(request)

        # Log audit trail if enabled and applicable
        should_audit = self._should_audit_request(request, response, resource_info)
        # Debug: audit decision made
        if should_audit:
            await self._log_request_audit(
                request,
                response,
                resource_info,
                user_id,
                correlation_id,
                start_time,
            )

        return response

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request context."""
        # Try to get from auth middleware context
        if hasattr(request.state, "user"):
            return getattr(request.state.user, "user_id", None)

        # Fallback to headers or query params
        return request.headers.get("X-User-ID") or request.query_params.get("user_id")

    def _extract_resource_info(self, request: Request) -> Dict[str, Any]:
        """Extract resource information from request path."""
        path_parts = request.url.path.strip("/").split("/")

        resource_info = {
            "resource_type": None,
            "resource_id": None,
            "action": self.crud_methods.get(request.method, "UNKNOWN"),
            "is_sensitive": False,
        }

        # Parse resource type from path
        for part in path_parts:
            if part in self.sensitive_resources:
                # clients -> Client
                resource_info["resource_type"] = part.rstrip("s").title()
                resource_info["is_sensitive"] = True
                break

        # Extract resource ID if present (UUID pattern or numeric ID)
        for i, part in enumerate(path_parts):
            # Check if this part comes after a resource type
            if i > 0 and path_parts[i - 1] in self.sensitive_resources:
                resource_info["resource_id"] = part
                break
            # Also check for UUID pattern
            elif len(part) == 36 and "-" in part:
                resource_info["resource_id"] = part
                break

        return resource_info

    def _should_audit_request(
        self,
        request: Request,
        response: Response,
        resource_info: Dict[str, Any],
    ) -> bool:
        """Determine if request should be audited."""
        # Skip health checks and non-sensitive endpoints
        skip_paths = ["/health", "/metrics", "/docs", "/openapi.json"]
        if request.url.path in skip_paths:
            return False

        # Skip if audit trail is disabled
        if not is_enabled("audit_trail"):
            return False

        # Skip if not sensitive resource and audit_sensitive_endpoints is False
        if not self.audit_sensitive_endpoints and not resource_info["is_sensitive"]:
            return False

        # Skip successful GET requests unless enhanced audit is enabled
        if (
            request.method == "GET"
            and 200 <= response.status_code < 300
            and not is_enabled("audit_trail_enhanced")
        ):
            return False

        return True

    async def _log_request_audit(
        self,
        request: Request,
        response: Response,
        resource_info: Dict[str, Any],
        user_id: Optional[str],
        correlation_id: str,
        start_time: float,
    ) -> None:
        """Log audit trail for the request."""
        try:
            # Prepare audit metadata
            metadata = {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "ip_address": self._get_client_ip(request),
                "user_agent": request.headers.get("User-Agent", ""),
                "immutable": True,
            }
            # Scrub PHI from base metadata
            metadata = scrub_phi(metadata)

            # Add enhanced metadata if feature flag is enabled
            if is_enabled("audit_trail_enhanced", user_id):
                enhanced_metadata = {
                    "query_params": dict(request.query_params),
                    "content_type": request.headers.get("Content-Type", ""),
                    "content_length": request.headers.get("Content-Length", "0"),
                    "referer": request.headers.get("Referer", ""),
                }
                # Scrub PHI from enhanced metadata
                enhanced_metadata = scrub_phi(enhanced_metadata)
                metadata.update(enhanced_metadata)

            # Log based on operation type
            if resource_info["is_sensitive"] and resource_info["resource_type"]:
                crud_actions = ["CREATE", "UPDATE", "DELETE"]
                if resource_info["action"] in crud_actions:
                    # Extract changes from request body for CREATE/UPDATE
                    changes = None
                    if hasattr(request.state, "body"):
                        changes = getattr(request.state, "body", None)

                    log_crud_action(
                        action=resource_info["action"],
                        resource=resource_info["resource_type"],
                        user_id=user_id or "anonymous",
                        correlation_id=correlation_id,
                        resource_id=resource_info.get("resource_id"),
                        changes=changes,
                        metadata=metadata,
                    )
                elif resource_info["action"] == "read":
                    log_data_access(
                        user_id=user_id or "anonymous",
                        correlation_id=correlation_id,
                        resource_type=resource_info["resource_type"],
                        resource_id=resource_info.get("resource_id", "collection"),
                        access_type="read",
                        query_params=dict(request.query_params),
                    )
            else:
                # Log as system event for non-resource operations
                severity = "INFO" if 200 <= response.status_code < 400 else "WARNING"
                log_system_event(
                    event_type=f"API_{request.method}",
                    correlation_id=correlation_id,
                    severity=severity,
                    details=metadata,
                )

        except Exception as e:
            # Log audit failure but don't break the request
            log_system_event(
                event_type="AUDIT_FAILURE",
                correlation_id=correlation_id,
                severity="ERROR",
                details={"error": str(e), "path": request.url.path},
            )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host

        return "unknown"

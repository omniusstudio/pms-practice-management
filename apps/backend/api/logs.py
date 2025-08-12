"""Logging API endpoints for frontend log collection."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from middleware.correlation import get_correlation_id
from utils.phi_scrubber import scrub_phi
from utils.response_models import APIResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["logging"])


class LogEntry(BaseModel):
    """Log entry model for frontend logs."""

    level: str = Field(..., description="Log level (info, warn, error, debug)")
    message: str = Field(..., description="Log message")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")
    correlationId: Optional[str] = Field(None, description="Correlation ID")
    userId: Optional[str] = Field(None, description="User ID")
    component: Optional[str] = Field(None, description="Frontend component")
    action: Optional[str] = Field(None, description="User action")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details")
    url: Optional[str] = Field(None, description="Current URL")
    userAgent: Optional[str] = Field(None, description="User agent")


@router.post(
    "/logs",
    response_model=APIResponse[Dict[str, str]],
    status_code=status.HTTP_201_CREATED,
    summary="Submit frontend log entry",
    description=(
        "Accept log entries from the frontend application for " "centralized logging."
    ),
)
async def submit_log(
    log_entry: LogEntry,
    request: Request,
    correlation_id: str = Depends(get_correlation_id),
) -> APIResponse[Dict[str, str]]:
    """Submit a log entry from the frontend.

    This endpoint accepts log entries from the frontend and processes them
    through the backend logging system with PHI scrubbing and proper
    formatting.
    """
    try:
        # Use correlation ID from log entry if provided, otherwise use
        # middleware-generated one
        effective_correlation_id = log_entry.correlationId or correlation_id

        # Scrub PHI from log message and context
        scrubbed_message = scrub_phi(log_entry.message)
        scrubbed_context = {}
        if log_entry.context:
            for key, value in log_entry.context.items():
                if isinstance(value, str):
                    scrubbed_context[key] = scrub_phi(value)
                else:
                    scrubbed_context[key] = value

        # Prepare log data for backend logging
        log_data = {
            "frontend_log": True,
            "level": log_entry.level,
            "message": scrubbed_message,
            "timestamp": log_entry.timestamp or datetime.utcnow().isoformat(),
            "correlation_id": effective_correlation_id,
            "user_id": log_entry.userId,
            "component": log_entry.component,
            "action": log_entry.action,
            "context": scrubbed_context,
            "url": log_entry.url,
            "user_agent": (log_entry.userAgent or request.headers.get("user-agent")),
            "client_ip": request.client.host if request.client else "unknown",
        }

        # Add error details if present
        if log_entry.error:
            log_data["error"] = {
                "name": log_entry.error.get("name"),
                "message": scrub_phi(log_entry.error.get("message", "")),
                "stack": scrub_phi(log_entry.error.get("stack", "")),
            }

        # Log to backend system based on level
        log_level = log_entry.level.lower()
        if log_level == "error":
            logger.error(f"Frontend Error: {scrubbed_message}", extra=log_data)
        elif log_level == "warn":
            logger.warning(f"Frontend Warning: {scrubbed_message}", extra=log_data)
        elif log_level == "debug":
            logger.debug(f"Frontend Debug: {scrubbed_message}", extra=log_data)
        else:  # info or default
            logger.info(f"Frontend Info: {scrubbed_message}", extra=log_data)

        return APIResponse(
            success=True,
            data={"log_id": effective_correlation_id, "status": "logged"},
            message="Log entry processed successfully",
            correlation_id=effective_correlation_id,
        )

    except Exception as e:
        logger.error(
            f"Failed to process frontend log entry: {str(e)}",
            extra={
                "correlation_id": correlation_id,
                "error": str(e),
                "log_level": log_entry.level if log_entry else "unknown",
            },
        )

        return APIResponse(
            success=False,
            data=None,
            message="Failed to process log entry",
            correlation_id=correlation_id,
        )


@router.get(
    "/logs/health",
    response_model=APIResponse[Dict[str, str]],
    summary="Check logging service health",
    description="Health check endpoint for the logging service.",
)
async def logging_health_check(
    correlation_id: str = Depends(get_correlation_id),
) -> APIResponse[Dict[str, str]]:
    """Health check for the logging service."""
    return APIResponse(
        success=True,
        data={"status": "healthy", "service": "logging"},
        message="Logging service is operational",
        correlation_id=correlation_id,
    )

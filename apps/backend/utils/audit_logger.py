"""Audit logging utilities for HIPAA-compliant immutable logging."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog

from .phi_scrubber import scrub_phi

logger = structlog.get_logger()


def log_crud_action(
    action: str,
    resource: str,
    user_id: str,
    correlation_id: str,
    resource_id: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Log CRUD action for audit trail (immutable).

    Args:
        action: CRUD action (CREATE, READ, UPDATE, DELETE)
        resource: Resource type being acted upon
        user_id: ID of user performing action
        correlation_id: Request correlation ID
        resource_id: ID of specific resource (if applicable)
        changes: Changes made (for UPDATE operations)
        metadata: Additional metadata
    """
    # Prepare audit log entry
    audit_entry = {
        "event": "audit_log",
        "audit_action": action.upper(),
        "resource_type": resource,
        "user_id": user_id,
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "immutable": True,  # Mark as immutable audit log
    }

    # Add resource ID if provided
    if resource_id:
        audit_entry["resource_id"] = resource_id

    # Add scrubbed changes for UPDATE operations
    if changes:
        audit_entry["changes"] = scrub_phi(changes)

    # Add scrubbed metadata
    if metadata:
        audit_entry["metadata"] = scrub_phi(metadata)

    # Log the audit entry (structured and immutable)
    logger.info(f"Audit: {action.upper()} {resource}", **audit_entry)


def log_authentication_event(
    event_type: str,
    user_id: str,
    correlation_id: str,
    success: bool,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    failure_reason: Optional[str] = None,
) -> None:
    """Log authentication events for security audit.

    Args:
        event_type: Type of auth event (LOGIN, LOGOUT, PASSWORD_CHANGE)
        user_id: User ID attempting authentication
        correlation_id: Request correlation ID
        success: Whether the authentication was successful
        ip_address: Client IP address
        user_agent: Client user agent
        failure_reason: Reason for failure (if applicable)
    """
    audit_entry = {
        "auth_event": event_type.upper(),
        "user_id": user_id,
        "correlation_id": correlation_id,
        "success": success,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "immutable": True,
    }

    # Add client information (scrubbed)
    if ip_address:
        audit_entry["client_ip"] = scrub_phi(ip_address)

    if user_agent:
        audit_entry["user_agent"] = scrub_phi(user_agent)

    # Add failure reason if applicable
    if not success and failure_reason:
        audit_entry["failure_reason"] = scrub_phi(failure_reason)

    # Log the security event
    status = "SUCCESS" if success else "FAILED"
    event_upper = event_type.upper()
    message = f"Security: {event_upper} {status}"
    logger.info(message, **audit_entry)


def log_data_access(
    user_id: str,
    correlation_id: str,
    resource_type: str,
    resource_id: str,
    access_type: str = "READ",
    query_params: Optional[Dict[str, Any]] = None,
) -> None:
    """Log data access events for compliance.

    Args:
        user_id: User accessing the data
        correlation_id: Request correlation ID
        resource_type: Type of resource accessed
        resource_id: ID of resource accessed
        access_type: Type of access (READ, search, export)
        query_params: Query parameters used
    """
    audit_entry = {
        "event": "data_access_audit",
        "user_id": user_id,
        "correlation_id": correlation_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "access_type": access_type.upper(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "immutable": True,
    }

    # Add scrubbed query parameters
    if query_params:
        audit_entry["query_params"] = scrub_phi(query_params)

    # Log the data access event
    logger.info(f"Data Access: {access_type.upper()} {resource_type}", **audit_entry)


def log_system_event(
    event_type: str,
    correlation_id: str,
    severity: str = "INFO",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log system events for operational monitoring.

    Args:
        event_type: Type of system event
        correlation_id: Request correlation ID
        severity: Event severity (INFO, WARNING, ERROR, CRITICAL)
        details: Additional event details
    """
    audit_entry = {
        "event": "system_audit",
        "system_event": event_type.upper(),
        "correlation_id": correlation_id,
        "severity": severity.upper(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "immutable": True,
    }

    # Add scrubbed details
    if details:
        audit_entry["details"] = scrub_phi(details)

    # Log the system event
    log_method = getattr(logger, severity.lower(), logger.info)
    log_method(f"System: {event_type.upper()}", **audit_entry)

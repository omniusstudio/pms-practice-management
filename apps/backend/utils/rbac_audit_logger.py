"""RBAC-specific audit logging utilities for Phase 3 monitoring and compliance.

This module provides specialized audit logging for RBAC operations including:
- Role assignments and changes
- Permission modifications
- Access review activities
- RBAC policy changes
- Authentication and authorization events
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit import AuditLog

from .audit_logger import log_crud_action
from .phi_scrubber import scrub_phi

logger = structlog.get_logger()


def log_rbac_role_assignment(
    user_id: str,
    target_user_id: str,
    roles_added: List[str],
    roles_removed: List[str],
    correlation_id: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Log RBAC role assignment changes.

    Args:
        user_id: ID of user making the change
        target_user_id: ID of user whose roles are being changed
        roles_added: List of roles being added
        roles_removed: List of roles being removed
        correlation_id: Request correlation ID
        ip_address: Client IP address
        user_agent: Client user agent
    """
    audit_entry = {
        "event": "rbac_role_assignment",
        "user_id": user_id,
        "target_user_id": target_user_id,
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "immutable": True,
        "roles_added": roles_added,
        "roles_removed": roles_removed,
        "change_type": "role_assignment",
    }

    # Add client information (scrubbed)
    if ip_address:
        audit_entry["client_ip"] = scrub_phi(ip_address)
    if user_agent:
        audit_entry["user_agent"] = scrub_phi(user_agent)

    # Log the RBAC change
    action_desc = (
        f"Roles +{roles_added} -{roles_removed}"
        if roles_added or roles_removed
        else "No changes"
    )
    logger.info(f"RBAC: Role Assignment - {action_desc}", **audit_entry)


def log_rbac_permission_check(
    user_id: str,
    required_roles: List[str],
    user_roles: List[str],
    resource: str,
    action: str,
    success: bool,
    correlation_id: str,
    ip_address: Optional[str] = None,
    failure_reason: Optional[str] = None,
) -> None:
    """Log RBAC permission checks and access attempts.

    Args:
        user_id: ID of user attempting access
        required_roles: Roles required for the action
        user_roles: Roles the user currently has
        resource: Resource being accessed
        action: Action being attempted
        success: Whether access was granted
        correlation_id: Request correlation ID
        ip_address: Client IP address
        failure_reason: Reason for access denial (if applicable)
    """
    audit_entry = {
        "event": "rbac_permission_check",
        "user_id": user_id,
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "immutable": True,
        "required_roles": required_roles,
        "user_roles": user_roles,
        "resource": resource,
        "action": action,
        "success": success,
    }

    # Add client information (scrubbed)
    if ip_address:
        audit_entry["client_ip"] = scrub_phi(ip_address)

    # Add failure reason if applicable
    if not success and failure_reason:
        audit_entry["failure_reason"] = scrub_phi(failure_reason)

    # Log the permission check
    status = "GRANTED" if success else "DENIED"
    logger.info(f"RBAC: Permission {status} - {action} on {resource}", **audit_entry)


def log_rbac_access_review_action(
    user_id: str,
    action: str,
    review_id: Optional[str] = None,
    target_user_id: Optional[str] = None,
    findings: Optional[Dict[str, Any]] = None,
    recommendations: Optional[List[str]] = None,
    correlation_id: Optional[str] = None,
) -> None:
    """Log access review related actions.

    Args:
        user_id: ID of user performing the review action
        action: Type of review action (generate_report, complete_review, etc.)
        review_id: ID of the access review
        target_user_id: ID of user being reviewed (if applicable)
        findings: Review findings
        recommendations: Review recommendations
        correlation_id: Request correlation ID
    """
    audit_entry = {
        "event": "rbac_access_review",
        "user_id": user_id,
        "correlation_id": (
            correlation_id or f"access_review_{int(datetime.now().timestamp())}"
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "immutable": True,
        "review_action": action.upper(),
    }

    # Add optional fields
    if review_id:
        audit_entry["review_id"] = review_id
    if target_user_id:
        audit_entry["target_user_id"] = target_user_id
    if findings:
        audit_entry["findings"] = scrub_phi(findings)
    if recommendations:
        audit_entry["recommendations"] = recommendations

    # Log the access review action
    logger.info(f"RBAC: Access Review - {action.upper()}", **audit_entry)


def log_rbac_policy_change(
    user_id: str,
    policy_type: str,
    change_description: str,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> None:
    """Log RBAC policy and configuration changes.

    Args:
        user_id: ID of user making the policy change
        policy_type: Type of policy being changed
            (role_definition, permission_mapping, etc.)
        change_description: Description of the change
        old_values: Previous policy values
        new_values: New policy values
        correlation_id: Request correlation ID
    """
    audit_entry = {
        "event": "rbac_policy_change",
        "user_id": user_id,
        "correlation_id": (
            correlation_id or f"policy_change_{int(datetime.now().timestamp())}"
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "immutable": True,
        "policy_type": policy_type,
        "change_description": change_description,
    }

    # Add change details (scrubbed)
    if old_values:
        audit_entry["old_values"] = scrub_phi(old_values)
    if new_values:
        audit_entry["new_values"] = scrub_phi(new_values)

    # Log the policy change
    logger.info(f"RBAC: Policy Change - {policy_type}", **audit_entry)


async def create_rbac_audit_record(
    session: AsyncSession,
    user_id: str,
    action: str,
    resource_type: str,
    correlation_id: str,
    resource_id: Optional[str] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    """Create an RBAC audit record in the database.

    Args:
        session: Database session
        user_id: ID of user performing the action
        action: Action being performed
        resource_type: Type of RBAC resource
        correlation_id: Request correlation ID
        resource_id: ID of specific resource
        old_values: Previous values
        new_values: New values
        ip_address: Client IP address
        user_agent: Client user agent

    Returns:
        Created AuditLog record
    """
    # Create audit log record
    audit_log = AuditLog(
        correlation_id=correlation_id,
        user_id=UUID(user_id) if user_id else None,
        action=f"RBAC_{action.upper()}",
        resource_type=f"rbac_{resource_type}",
        resource_id=UUID(resource_id) if resource_id else None,
        old_values=scrub_phi(old_values) if old_values else None,
        new_values=scrub_phi(new_values) if new_values else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    session.add(audit_log)
    await session.flush()  # Get the ID without committing

    # Also log to structured logger
    log_crud_action(
        action=f"RBAC_{action.upper()}",
        resource=f"rbac_{resource_type}",
        user_id=user_id,
        correlation_id=correlation_id,
        resource_id=resource_id,
        changes=new_values,
        metadata={
            "audit_log_id": str(audit_log.id),
            "ip_address": ip_address,
            "user_agent": user_agent,
        },
    )

    return audit_log


def log_rbac_authentication_event(
    event_type: str,
    user_id: str,
    correlation_id: str,
    success: bool,
    roles: Optional[List[str]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    failure_reason: Optional[str] = None,
) -> None:
    """Log RBAC-related authentication events.

    Args:
        event_type: Type of auth event (LOGIN, LOGOUT, ROLE_CHANGE)
        user_id: User ID
        correlation_id: Request correlation ID
        success: Whether the event was successful
        roles: User roles at time of event
        ip_address: Client IP address
        user_agent: Client user agent
        failure_reason: Reason for failure (if applicable)
    """
    audit_entry = {
        "event": "rbac_authentication",
        "auth_event": event_type.upper(),
        "user_id": user_id,
        "correlation_id": correlation_id,
        "success": success,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "immutable": True,
    }

    # Add user roles if provided
    if roles:
        audit_entry["user_roles"] = roles

    # Add client information (scrubbed)
    if ip_address:
        audit_entry["client_ip"] = scrub_phi(ip_address)
    if user_agent:
        audit_entry["user_agent"] = scrub_phi(user_agent)

    # Add failure reason if applicable
    if not success and failure_reason:
        audit_entry["failure_reason"] = scrub_phi(failure_reason)

    # Log the authentication event
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"RBAC: Auth {event_type.upper()} {status}", **audit_entry)

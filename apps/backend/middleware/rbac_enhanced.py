"""Enhanced RBAC Middleware for Phase 2 Implementation.

This module provides enhanced role-based access control with:
- Enhanced role validation middleware
- Access review logging
- Quarterly access review support
- HIPAA compliance features
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, Request, status
from pydantic import BaseModel

from middleware.auth_middleware import AuthenticatedUser, get_current_user
from utils.error_handlers import AuthenticationError

logger = logging.getLogger(__name__)


class AccessReviewLog(BaseModel):
    """Model for access review logging."""

    user_id: UUID
    resource: str
    action: str
    permission_required: str
    access_granted: bool
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    correlation_id: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class RoleValidationResult(BaseModel):
    """Result of role validation."""

    valid: bool
    user_roles: List[str]
    required_roles: List[str]
    missing_roles: List[str]
    excessive_permissions: List[str]
    recommendations: List[str]


class EnhancedRBACMiddleware:
    """Enhanced RBAC middleware with logging and validation."""

    def __init__(self):
        self.access_logs: List[AccessReviewLog] = []
        self.role_hierarchy = {
            "admin": ["clinician", "biller", "front_desk"],
            "clinician": [],
            "biller": [],
            "front_desk": [],
        }

    async def log_access_attempt(
        self,
        request: Request,
        user: AuthenticatedUser,
        resource: str,
        action: str,
        permission_required: str,
        access_granted: bool,
    ) -> None:
        """Log access attempt for audit and review purposes."""

        correlation_id = getattr(request.state, "correlation_id", "unknown")

        access_log = AccessReviewLog(
            user_id=UUID(user.user_id),
            resource=resource,
            action=action,
            permission_required=permission_required,
            access_granted=access_granted,
            timestamp=datetime.now(timezone.utc),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            correlation_id=correlation_id,
        )

        self.access_logs.append(access_log)

        # Log for audit trail
        logger.info(
            "Access attempt logged",
            extra={
                "user_id": str(user.user_id),
                "resource": resource,
                "action": action,
                "permission_required": permission_required,
                "access_granted": access_granted,
                "correlation_id": correlation_id,
                "ip_address": access_log.ip_address,
                "user_agent": access_log.user_agent,
            },
        )

    def validate_role_hierarchy(self, user_roles: List[str]) -> RoleValidationResult:
        """Validate user roles against hierarchy and least privilege."""

        valid_roles = set(self.role_hierarchy.keys())
        user_role_set = set(user_roles)

        # Check for invalid roles
        invalid_roles = user_role_set - valid_roles
        if invalid_roles:
            return RoleValidationResult(
                valid=False,
                user_roles=user_roles,
                required_roles=[],
                missing_roles=[],
                excessive_permissions=list(invalid_roles),
                recommendations=[f"Remove invalid roles: {', '.join(invalid_roles)}"],
            )

        # Check for role conflicts (admin should not have other roles)
        recommendations = []
        excessive_permissions = []

        if "admin" in user_role_set and len(user_role_set) > 1:
            other_roles = user_role_set - {"admin"}
            excessive_permissions.extend(other_roles)
            recommendations.append(
                f"Admin role includes all permissions. "
                f"Remove redundant roles: {', '.join(other_roles)}"
            )

        # Check for overlapping permissions
        for role in user_role_set:
            implied_roles = set(self.role_hierarchy.get(role, []))
            overlap = user_role_set & implied_roles
            if overlap:
                excessive_permissions.extend(overlap)
                recommendations.append(
                    f"Role '{role}' already includes permissions "
                    f"from: {', '.join(overlap)}"
                )

        return RoleValidationResult(
            valid=len(excessive_permissions) == 0,
            user_roles=user_roles,
            required_roles=[],
            missing_roles=[],
            excessive_permissions=list(set(excessive_permissions)),
            recommendations=recommendations,
        )

    def get_minimum_required_roles(self, permissions: List[str]) -> List[str]:
        """Determine minimum roles required for given permissions."""

        # Permission to role mapping
        permission_roles = {
            "read:all": ["admin"],
            "write:all": ["admin"],
            "delete:all": ["admin"],
            "manage:users": ["admin"],
            "manage:system": ["admin"],
            "manage:billing": ["admin"],
            "audit:access": ["admin"],
            "read:patients": ["admin", "clinician", "biller", "front_desk"],
            "write:patients": ["admin", "clinician", "front_desk"],
            "read:appointments": ["admin", "clinician", "biller", "front_desk"],
            "write:appointments": ["admin", "clinician", "front_desk"],
            "read:notes": ["admin", "clinician"],
            "write:notes": ["admin", "clinician"],
            "read:billing": ["admin", "biller"],
            "write:billing": ["admin", "biller"],
            "read:ledger": ["admin", "biller"],
            "write:ledger": ["admin", "biller"],
            "read:financial_reports": ["admin", "biller"],
            "read:profile": ["admin", "clinician", "biller", "front_desk"],
            "write:profile": ["admin", "clinician", "biller", "front_desk"],
        }

        required_roles = set()
        for permission in permissions:
            roles = permission_roles.get(permission, [])
            if roles:
                # Find the least privileged role that can satisfy this
                # permission
                if "front_desk" in roles:
                    required_roles.add("front_desk")
                elif "biller" in roles:
                    required_roles.add("biller")
                elif "clinician" in roles:
                    required_roles.add("clinician")
                elif "admin" in roles:
                    required_roles.add("admin")

        return list(required_roles)

    async def enhanced_require_roles(
        self,
        request: Request,
        required_roles: List[str],
        resource: str = "unknown",
        action: str = "access",
    ) -> AuthenticatedUser:
        """Enhanced role requirement with logging and validation."""

        user = await get_current_user(request)
        if not user:
            await self.log_access_attempt(
                request=request,
                user=None,
                resource=resource,
                action=action,
                permission_required=(f"roles:{','.join(required_roles)}"),
                access_granted=False,
            )
            raise AuthenticationError(
                message="Authentication required",
                correlation_id=getattr(request.state, "correlation_id", "unknown"),
            )

        # Validate role hierarchy
        validation_result = self.validate_role_hierarchy(user.roles)
        if not validation_result.valid:
            logger.warning(
                "Role validation failed",
                extra={
                    "user_id": user.user_id,
                    "user_roles": user.roles,
                    "excessive_permissions": validation_result.excessive_permissions,
                    "recommendations": validation_result.recommendations,
                },
            )

        # Check role access
        has_access = user.has_any_role(required_roles)

        # Log access attempt
        await self.log_access_attempt(
            request=request,
            user=user,
            resource=resource,
            action=action,
            permission_required=(f"roles:{','.join(required_roles)}"),
            access_granted=has_access,
        )

        if not has_access:
            logger.warning(
                "Insufficient roles for access",
                extra={
                    "user_id": user.user_id,
                    "required_roles": required_roles,
                    "user_roles": user.roles,
                    "resource": resource,
                    "action": action,
                    "path": request.url.path,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )

        return user

    async def enhanced_require_permissions(
        self,
        request: Request,
        required_permissions: List[str],
        resource: str = "unknown",
        action: str = "access",
    ) -> AuthenticatedUser:
        """Enhanced permission requirement with logging and validation."""

        user = await get_current_user(request)
        if not user:
            await self.log_access_attempt(
                request=request,
                user=None,
                resource=resource,
                action=action,
                permission_required=(f"permissions:{','.join(required_permissions)}"),
                access_granted=False,
            )
            raise AuthenticationError(
                message="Authentication required",
                correlation_id=getattr(request.state, "correlation_id", "unknown"),
            )

        # Check permissions
        has_access = user.has_all_permissions(required_permissions)

        # Log access attempt
        await self.log_access_attempt(
            request=request,
            user=user,
            resource=resource,
            action=action,
            permission_required=(f"permissions:{','.join(required_permissions)}"),
            access_granted=has_access,
        )

        if not has_access:
            # Suggest minimum required roles
            min_roles = self.get_minimum_required_roles(required_permissions)

            logger.warning(
                "Insufficient permissions for access",
                extra={
                    "user_id": user.user_id,
                    "required_permissions": required_permissions,
                    "user_permissions": user.permissions,
                    "suggested_roles": min_roles,
                    "resource": resource,
                    "action": action,
                    "path": request.url.path,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )

        return user

    def get_access_logs(
        self,
        user_id: Optional[UUID] = None,
        resource: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[AccessReviewLog]:
        """Get access logs for review purposes."""

        logs = self.access_logs

        if user_id:
            logs = [log for log in logs if log.user_id == user_id]

        if resource:
            logs = [log for log in logs if log.resource == resource]

        if start_date:
            logs = [log for log in logs if log.timestamp >= start_date]

        if end_date:
            logs = [log for log in logs if log.timestamp <= end_date]

        return logs


# Global instance
enhanced_rbac = EnhancedRBACMiddleware()

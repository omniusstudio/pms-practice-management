"""Authentication Middleware for OIDC Integration.

This module provides middleware for JWT token validation, user authentication,
and role-based access control (RBAC) for HIPAA-compliant applications.
"""

import logging
from typing import List, Optional

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from utils.error_handlers import AuthenticationError
from pydantic import BaseModel, ConfigDict, PrivateAttr

from core.config import get_settings
from database import get_db

# from models.auth_token import AuthToken  # Disabled
from models.user import User

# SQLAlchemy imports removed - not currently used


# from services.auth_service import get_async_auth_service  # Disabled

logger = logging.getLogger(__name__)
settings = get_settings()

security = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    """Authenticated user context."""

    _user: User = PrivateAttr()
    # token: AuthToken  # Disabled
    token: Optional[dict] = None  # Placeholder for disabled auth tokens
    permissions: List[str] = []

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    def __init__(self, user: User, **data):
        super().__init__(**data)
        self._user = user

    @property
    def user(self) -> User:
        """Get the user object."""
        return self._user

    @property
    def user_id(self) -> str:
        """Get user ID."""
        return str(self._user.id) if self._user else ""

    @property
    def email(self) -> str:
        """Get user email."""
        return str(self._user.email) if self._user else ""

    @property
    def display_name(self) -> str:
        """Get user display name."""
        if not self._user:
            return ""
        display = getattr(self._user, "display_name", None)
        first = getattr(self._user, "first_name", None) or ""
        last = getattr(self._user, "last_name", None) or ""
        email = str(self._user.email) if self._user.email else ""
        return display or f"{first} {last}".strip() or email

    @property
    def roles(self) -> List[str]:
        """Get user roles."""
        if not self._user:
            return []
        user_roles = getattr(self._user, "roles", None)
        return list(user_roles) if user_roles else []

    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return "admin" in self.roles

    @property
    def is_active(self) -> bool:
        """Check if user is active."""
        if not self._user:
            return False
        active = getattr(self._user, "is_active", None)
        return bool(active) if active is not None else False

    def has_role(self, role: str) -> bool:
        """Check if user has specific role."""
        return self._user.has_role(role)

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions

    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(self.has_role(role) for role in roles)

    def has_all_permissions(self, permissions: List[str]) -> bool:
        """Check if user has all specified permissions."""
        return all(self.has_permission(perm) for perm in permissions)


async def get_current_user(
    request: Request, credentials: Optional[HTTPAuthorizationCredentials] = None
) -> Optional[AuthenticatedUser]:
    """Get current authenticated user from request."""
    if not credentials:
        credentials = await security(request)

    if not credentials:
        return None

    try:
        # Get correlation ID for audit logging
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        # DISABLED: Auth service functionality is disabled
        # auth_svc = get_async_auth_service(db, correlation_id)
        # token = await auth_svc.validate_token(credentials.credentials)
        # Authentication is disabled - return None
        logger.debug(
            "Authentication disabled", extra={"correlation_id": correlation_id}
        )
        return None

        # # Get user
        # stmt = select(User).where(User.id == token.user_id)
        # result = await db.execute(stmt)
        # user = result.scalar_one_or_none()

        # DISABLED: All authentication logic is disabled
        # if not user or not user.is_active:
        #     logger.warning(
        #         "User not found or inactive",
        #         extra={"user_id": str(token.user_id)}
        #     )
        #     return None
        #
        # # Update last login time
        # user.last_login_at = datetime.now(timezone.utc)
        #
        # # Get user permissions (combine role-based and direct permissions)
        # permissions = list(user.permissions or [])
        #
        # # Add role-based permissions
        # role_permissions = get_role_permissions(user.roles or [])
        # permissions.extend(role_permissions)
        #
        # # Remove duplicates
        # permissions = list(set(permissions))
        #
        # logger.debug(
        #     "User authenticated successfully",
        #     extra={
        #         "user_id": str(user.id),
        #         "roles": user.roles,
        #         "permissions_count": len(permissions),
        #     },
        # )
        #
        # return AuthenticatedUser(
        #     user=user, token=token, permissions=permissions
        # )

    except Exception as e:
        logger.error("Authentication failed", extra={"error": str(e)})
        return None


def get_role_permissions(roles: List[str]) -> List[str]:
    """Get permissions for given roles."""
    role_permission_map = {
        "admin": [
            "read:all",
            "write:all",
            "delete:all",
            "manage:users",
            "manage:system",
            "manage:billing",
            "audit:access",
            "read:patients",
            "write:patients",
            "read:appointments",
            "write:appointments",
            "read:notes",
            "write:notes",
            "read:billing",
            "write:billing",
            "read:ledger",
            "write:ledger",
            "read:financial_reports",
        ],
        "clinician": [
            "read:patients",
            "write:patients",
            "read:appointments",
            "write:appointments",
            "read:notes",
            "write:notes",
            "read:profile",
            "write:profile",
        ],
        "biller": [
            "read:billing",
            "write:billing",
            "read:ledger",
            "write:ledger",
            "read:financial_reports",
            "read:patients",  # Need patient info for billing
            "read:appointments",  # Need appointments for billing
            "read:profile",
            "write:profile",
        ],
        "front_desk": [
            "read:appointments",
            "write:appointments",
            "read:patients",
            "write:patients",
            "read:profile",
            "write:profile",
        ],
        # Legacy roles for backward compatibility
        "provider": [
            "read:patients",
            "write:patients",
            "read:appointments",
            "write:appointments",
            "read:notes",
            "write:notes",
            "read:profile",
        ],
        "staff": [
            "read:appointments",
            "write:appointments",
            "read:patients",
            "read:profile",
        ],
        "user": ["read:profile", "write:profile"],
    }

    permissions = []
    for role in roles:
        permissions.extend(role_permission_map.get(role, []))

    return list(set(permissions))


async def require_auth(
    request: Request, credentials: Optional[HTTPAuthorizationCredentials] = None
) -> AuthenticatedUser:
    """Require authentication and return authenticated user."""
    user = await get_current_user(request, credentials)

    if not user:
        logger.warning(
            "Authentication required but not provided", extra={"path": request.url.path}
        )
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        raise AuthenticationError(
            message="Authentication failed",
            correlation_id=correlation_id
        )

    return user


def require_roles(required_roles: List[str]):
    """Decorator to require specific roles."""

    async def dependency(
        request: Request, user: Optional[AuthenticatedUser] = None
    ) -> AuthenticatedUser:
        if not user:
            user = await require_auth(request)

        if not user.has_any_role(required_roles):
            logger.warning(
                "Insufficient roles for access",
                extra={
                    "user_id": user.user_id,
                    "required_roles": required_roles,
                    "user_roles": user.roles,
                    "path": request.url.path,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )

        return user

    return dependency


def require_permissions(required_permissions: List[str]):
    """Decorator to require specific permissions."""

    async def dependency(
        request: Request, user: Optional[AuthenticatedUser] = None
    ) -> AuthenticatedUser:
        if not user:
            user = await require_auth(request)

        if not user.has_all_permissions(required_permissions):
            logger.warning(
                "Insufficient permissions for access",
                extra={
                    "user_id": user.user_id,
                    "required_permissions": required_permissions,
                    "user_permissions": user.permissions,
                    "path": request.url.path,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )

        return user

    return dependency


class AuthMiddleware:
    """Authentication middleware for FastAPI."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        """Process request through authentication middleware."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Skip authentication for certain paths
        skip_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics",
            "/auth/login",
            "/auth/callback",
            "/auth/providers",
        ]

        if any(request.url.path.startswith(path) for path in skip_paths):
            await self.app(scope, receive, send)
            return

        # Add database session to request state
        async with get_db() as db:
            request.state.db = db

            # Try to authenticate user
            try:
                user = await get_current_user(request)
                request.state.user = user

                # Log authenticated requests
                if user:
                    logger.info(
                        "Authenticated request",
                        extra={
                            "user_id": user.user_id,
                            "method": request.method,
                            "path": request.url.path,
                            "user_agent": request.headers.get("user-agent", "unknown"),
                        },
                    )

            except Exception as e:
                logger.error(
                    "Authentication middleware error",
                    extra={"error": str(e), "path": request.url.path},
                )
                request.state.user = None

            await self.app(scope, receive, send)


# Dependency functions for FastAPI
async def get_current_user_dependency(request: Request) -> Optional[AuthenticatedUser]:
    """FastAPI dependency to get current user."""
    return getattr(request.state, "user", None)


async def require_auth_dependency(request: Request) -> AuthenticatedUser:
    """FastAPI dependency to require authentication."""
    user = getattr(request.state, "user", None)

    if not user:
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        raise AuthenticationError(
            message="Authentication failed",
            correlation_id=correlation_id
        )

    return user


# Role-based dependencies
require_admin = require_roles(["admin"])
require_admin_role = require_roles(["admin"])  # Alias for admin.py
require_clinician = require_roles(["clinician", "admin"])
require_biller = require_roles(["biller", "admin"])
require_front_desk = require_roles(["front_desk", "admin"])

# Legacy role dependencies for backward compatibility
require_provider = require_roles(["provider", "clinician", "admin"])
require_staff = require_roles(["staff", "front_desk", "admin"])

# Permission-based dependencies
require_read_patients = require_permissions(["read:patients"])
require_write_patients = require_permissions(["write:patients"])
require_read_billing = require_permissions(["read:billing"])
require_write_billing = require_permissions(["write:billing"])
require_read_ledger = require_permissions(["read:ledger"])
require_write_ledger = require_permissions(["write:ledger"])
require_read_financial_reports = require_permissions(["read:financial_reports"])
require_manage_users = require_permissions(["manage:users"])
require_manage_billing = require_permissions(["manage:billing"])

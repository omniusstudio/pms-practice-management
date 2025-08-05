"""User model for OAuth2/OIDC authentication."""

from datetime import datetime, timezone
from typing import List

from sqlalchemy import JSON, Boolean, Column, DateTime, Index, String
from sqlalchemy.orm import relationship

from .base import BaseModel


class User(BaseModel):
    """User model for OAuth2/OIDC authentication.

    This model supports:
    - OAuth2/OIDC provider integration
    - Role-based access control (RBAC)
    - MFA readiness
    - HIPAA-compliant audit trails
    """

    __tablename__ = "users"

    # Identity information from OIDC provider
    email = Column(String(255), unique=True, nullable=False, index=True)
    provider_id = Column(String(255), nullable=False, index=True)
    provider_name = Column(String(100), nullable=False)

    # User profile information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    display_name = Column(String(200), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Authorization and access control
    roles = Column(JSON, default=list, nullable=False)
    permissions = Column(JSON, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_admin = Column(Boolean, default=False, nullable=False)

    # Authentication tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(String(50), default="0", nullable=False)
    failed_login_attempts = Column(String(50), default="0", nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # MFA support (ready for future implementation)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(255), nullable=True)
    backup_codes = Column(JSON, default=list, nullable=False)

    # OIDC token information
    oidc_refresh_token_hash = Column(String(255), nullable=True)
    oidc_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    auth_tokens = relationship(
        "AuthToken",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="AuthToken.user_id",
    )

    # Indexes for performance and security
    __table_args__ = (
        Index("idx_users_email_active", "email", "is_active"),
        Index("idx_users_provider", "provider_name", "provider_id"),
        Index("idx_users_active_roles", "is_active", "roles"),
        Index("idx_users_last_login", "last_login_at"),
    )

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.display_name or str(self.email).split("@")[0]

    @property
    def is_locked(self) -> bool:
        """Check if user account is locked."""
        if not self.locked_until:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        roles_list = self.roles or []
        return role in roles_list

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        permissions_list = self.permissions or []
        return permission in permissions_list

    def add_role(self, role: str) -> None:
        """Add a role to the user."""
        from sqlalchemy.orm import object_session

        session = object_session(self)
        if session:
            current_roles = self.roles or []
            if role not in current_roles:
                new_roles = current_roles + [role]
                session.execute(
                    f"UPDATE {self.__tablename__} SET roles = :roles "
                    f"WHERE id = :id",
                    {"roles": new_roles, "id": str(self.id)},
                )

    def remove_role(self, role: str) -> None:
        """Remove a role from the user."""
        from sqlalchemy.orm import object_session

        session = object_session(self)
        if session:
            current_roles = self.roles or []
            if role in current_roles:
                new_roles = [r for r in current_roles if r != role]
                session.execute(
                    f"UPDATE {self.__tablename__} SET roles = :roles "
                    f"WHERE id = :id",
                    {"roles": new_roles, "id": str(self.id)},
                )

    def add_permission(self, permission: str) -> None:
        """Add a permission to the user."""
        from sqlalchemy.orm import object_session

        session = object_session(self)
        if session:
            current_permissions = self.permissions or []
            if permission not in current_permissions:
                new_permissions = current_permissions + [permission]
                session.execute(
                    f"UPDATE {self.__tablename__} SET permissions = "
                    f":permissions WHERE id = :id",
                    {"permissions": new_permissions, "id": str(self.id)},
                )

    def remove_permission(self, permission: str) -> None:
        """Remove a permission from the user."""
        from sqlalchemy.orm import object_session

        session = object_session(self)
        if session:
            current_permissions = self.permissions or []
            if permission in current_permissions:
                new_permissions = [p for p in current_permissions if p != permission]
                session.execute(
                    f"UPDATE {self.__tablename__} SET permissions = "
                    f":permissions WHERE id = :id",
                    {"permissions": new_permissions, "id": str(self.id)},
                )

    def record_login(self) -> None:
        """Record a successful login."""
        self.last_login_at = datetime.now(timezone.utc)
        self.login_count = str(int(self.login_count or "0") + 1)
        self.failed_login_attempts = "0"
        self.locked_until = None

    def record_failed_login(
        self, max_attempts: int = 5, lockout_minutes: int = 30
    ) -> None:
        """Record a failed login attempt and lock account if necessary."""
        failed_count = int(self.failed_login_attempts or "0") + 1
        self.failed_login_attempts = str(failed_count)

        if failed_count >= max_attempts:
            self.locked_until = datetime.now(timezone.utc).replace(
                minute=datetime.now(timezone.utc).minute + lockout_minutes
            )

    def unlock_account(self) -> None:
        """Unlock the user account."""
        self.locked_until = None
        self.failed_login_attempts = "0"

    def enable_mfa(self, secret: str, backup_codes: List[str]) -> None:
        """Enable MFA for the user (placeholder for future implementation)."""
        # TODO: Implement MFA secret encryption
        self.mfa_enabled = True
        self.mfa_secret = secret  # Should be encrypted
        self.backup_codes = backup_codes  # Should be encrypted

    def disable_mfa(self) -> None:
        """Disable MFA for the user."""
        self.mfa_enabled = False
        self.mfa_secret = None
        self.backup_codes = []

    def __repr__(self) -> str:
        """String representation of the user."""
        return (
            f"<User(id={self.id}, email={self.email}, provider={self.provider_name})>"
        )

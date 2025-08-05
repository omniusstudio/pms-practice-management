"""Audit log model for HIPAA compliance."""

from sqlalchemy import JSON, Column, Index, String, Text

from .base import BaseModel
from .types import UUID


class AuditLog(BaseModel):
    """Audit log for tracking all system actions (HIPAA requirement)."""

    __tablename__ = "audit_log"

    # Request tracking
    correlation_id = Column(String(255), nullable=False, index=True)

    # User information
    user_id: Column[UUID] = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Action details
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id: Column[UUID] = Column(UUID(as_uuid=True), nullable=True)

    # Data changes
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)

    # Request context
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(Text, nullable=True)

    # Indexes for performance and compliance queries
    __table_args__ = (
        Index("idx_audit_correlation_id", "correlation_id"),
        Index("idx_audit_user_id", "user_id"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_created_at", "created_at"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_user_date", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation without PHI."""
        return (
            f"<AuditLog(id={self.id}, "
            f"action={self.action}, "
            f"resource={self.resource_type})>"
        )

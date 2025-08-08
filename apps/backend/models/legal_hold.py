"""Legal hold model for data retention compliance."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Index, String, Text

from .base import BaseModel


class HoldStatus(str, Enum):
    """Status of legal holds."""

    ACTIVE = "active"
    RELEASED = "released"
    EXPIRED = "expired"


class HoldReason(str, Enum):
    """Reasons for legal holds."""

    LITIGATION = "litigation"
    INVESTIGATION = "investigation"
    REGULATORY_REQUEST = "regulatory_request"
    AUDIT = "audit"
    OTHER = "other"


class LegalHold(BaseModel):
    """Legal hold records for data retention exemptions.

    This model tracks records that must be preserved beyond normal
    retention periods due to legal, regulatory, or compliance requirements.
    """

    __tablename__ = "legal_holds"

    # Hold identification
    hold_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Hold details
    reason: Column[HoldReason] = Column(SQLEnum(HoldReason), nullable=False)
    status: Column[HoldStatus] = Column(
        SQLEnum(HoldStatus), nullable=False, default=HoldStatus.ACTIVE
    )

    # Target data specification
    resource_type = Column(String(100), nullable=False)  # e.g., 'clients'
    resource_id = Column(String(255), nullable=True)  # Specific record ID
    filter_criteria = Column(Text, nullable=True)  # JSON filter criteria

    # Hold lifecycle
    hold_start_date = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    hold_end_date = Column(DateTime(timezone=True), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)

    # Legal and compliance tracking
    case_number = Column(String(255), nullable=True)
    legal_contact = Column(String(255), nullable=True)
    compliance_notes = Column(Text, nullable=True)

    # Administrative
    auto_release = Column(Boolean, default=False, nullable=False)
    notification_sent = Column(Boolean, default=False, nullable=False)

    # Indexes for performance
    __table_args__ = (
        Index("idx_legal_hold_resource_status", "resource_type", "status"),
        Index("idx_legal_hold_tenant_active", "tenant_id", "status"),
        Index("idx_legal_hold_end_date", "hold_end_date"),
        Index("idx_legal_hold_resource_id", "resource_type", "resource_id"),
    )

    def is_active(self) -> bool:
        """Check if the legal hold is currently active.

        Returns:
            bool: True if hold is active and not expired
        """
        if self.status != HoldStatus.ACTIVE:
            return False

        if self.hold_end_date is None:
            return True

        now = datetime.now(timezone.utc)
        return now <= self.hold_end_date

    def should_auto_release(self) -> bool:
        """Check if the hold should be automatically released.

        Returns:
            bool: True if hold should be auto-released
        """
        if not self.auto_release or self.status != HoldStatus.ACTIVE:
            return False

        if self.hold_end_date is None:
            return False

        now = datetime.now(timezone.utc)
        return now > self.hold_end_date

    def release_hold(self, released_by: Optional[str] = None) -> None:
        """Release the legal hold.

        Args:
            released_by: User ID who released the hold
        """
        now = datetime.now(timezone.utc)
        self.status = HoldStatus.RELEASED
        self.released_at = now

        if released_by:
            self.compliance_notes = (
                f"{self.compliance_notes or ''}"
                f"\nReleased by {released_by} at {now.isoformat()}"
            ).strip()

    def matches_resource(self, resource_type: str, resource_id: str) -> bool:
        """Check if this hold applies to a specific resource.

        Args:
            resource_type: Type of resource (e.g., 'clients')
            resource_id: ID of the specific resource

        Returns:
            bool: True if hold applies to this resource
        """
        if not self.is_active():
            return False

        if self.resource_type != resource_type:
            return False

        # If no specific resource ID, hold applies to all of this type
        if self.resource_id is None:
            return True

        return self.resource_id == resource_id

    def __repr__(self) -> str:
        """String representation without PHI."""
        return (
            f"<LegalHold("
            f"id={self.id}, "
            f"name={self.hold_name}, "
            f"resource_type={self.resource_type}, "
            f"status={self.status}"
            f")>"
        )

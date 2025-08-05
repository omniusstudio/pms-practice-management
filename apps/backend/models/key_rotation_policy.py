"""Key rotation policy model for automated encryption key management."""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from models.base import BaseModel
from models.encryption_key import JSONBType
from models.types import UUID


class RotationTrigger(str, Enum):
    """Enumeration of key rotation triggers."""

    TIME_BASED = "time_based"  # Rotate based on time intervals
    USAGE_BASED = "usage_based"  # Rotate based on usage count
    EVENT_BASED = "event_based"  # Rotate based on specific events
    MANUAL = "manual"  # Manual rotation only


class PolicyStatus(str, Enum):
    """Enumeration of rotation policy statuses."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class KeyRotationPolicy(BaseModel):
    """Model for key rotation policies.

    This model defines automated rotation policies for encryption keys,
    supporting various rotation triggers and compliance requirements.
    """

    __tablename__ = "key_rotation_policies"

    # Primary identification
    id: Column[UUID] = Column(UUID, primary_key=True, default=uuid4, nullable=False)
    tenant_id = Column(String(255), nullable=False, index=True)
    policy_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Policy configuration
    key_type = Column(String(50), nullable=False)  # KeyType enum value
    kms_provider = Column(String(50), nullable=False)  # KeyProvider enum
    rotation_trigger = Column(String(50), nullable=False)  # RotationTrigger enum
    status = Column(String(50), nullable=False, default=PolicyStatus.ACTIVE)

    # Time-based rotation settings
    rotation_interval_days = Column(Integer, nullable=True)
    rotation_time_of_day = Column(String(8), nullable=True)  # HH:MM:SS format
    timezone = Column(String(50), nullable=True, default="UTC")

    # Usage-based rotation settings
    max_usage_count = Column(Integer, nullable=True)
    usage_threshold_warning = Column(Integer, nullable=True)

    # Event-based rotation settings
    rotation_events = Column(JSONBType, nullable=True)  # List of event types

    # Rollback and retention settings
    enable_rollback = Column(Boolean, default=True)
    rollback_period_hours = Column(Integer, default=24)
    retain_old_keys_days = Column(Integer, default=30)

    # Notification settings
    notification_settings = Column(JSONBType, nullable=True)

    # Compliance and audit
    compliance_tags = Column(JSONBType, nullable=True)
    authorized_services = Column(JSONBType, nullable=True)

    # Metadata
    created_by_token_id: Column[UUID] = Column(
        UUID, ForeignKey("auth_tokens.id"), nullable=False
    )
    last_modified_by_token_id: Column[UUID] = Column(
        UUID, ForeignKey("auth_tokens.id"), nullable=False
    )
    correlation_id = Column(String(255), nullable=True)

    # Timestamps
    last_rotation_at = Column(DateTime(timezone=True), nullable=True)
    next_rotation_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    encryption_keys = relationship(
        "EncryptionKey", back_populates="rotation_policy", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation of the policy."""
        return (
            f"<KeyRotationPolicy(id={self.id}, "
            f"tenant_id='{self.tenant_id}', "
            f"policy_name='{self.policy_name}', "
            f"status='{self.status}')>"
        )

    def is_active(self) -> bool:
        """Check if the policy is currently active."""
        return str(self.status) == PolicyStatus.ACTIVE

    def should_rotate_now(self) -> bool:
        """Check if a key should be rotated based on this policy."""
        if not self.is_active():
            return False

        now = datetime.now(timezone.utc)

        # Time-based rotation
        if self.rotation_trigger == RotationTrigger.TIME_BASED:
            if self.next_rotation_at:
                # Ensure both datetimes are timezone-aware for comparison
                next_rotation = self.next_rotation_at
                if next_rotation.tzinfo is None:
                    next_rotation = next_rotation.replace(tzinfo=timezone.utc)
                if now >= next_rotation:
                    return True

        # Manual rotation only
        if self.rotation_trigger == RotationTrigger.MANUAL:
            return False

        return False

    def calculate_next_rotation(self) -> Optional[datetime]:
        """Calculate the next rotation time based on policy settings."""
        if self.rotation_trigger != RotationTrigger.TIME_BASED:
            return None

        if not self.rotation_interval_days:
            return None

        base_time = (
            self.last_rotation_at or self.created_at or datetime.now(timezone.utc)
        )

        # Ensure base_time is timezone-aware
        if base_time.tzinfo is None:
            base_time = base_time.replace(tzinfo=timezone.utc)
        interval_days = int(self.rotation_interval_days)
        next_rotation = base_time + timedelta(days=interval_days)

        # Adjust for specific time of day if configured
        if self.rotation_time_of_day:
            try:
                parts = self.rotation_time_of_day.split(":")
                hour, minute, second = map(int, parts)
                next_rotation = next_rotation.replace(
                    hour=hour, minute=minute, second=second, microsecond=0
                )
            except (ValueError, AttributeError):
                pass  # Use default time if parsing fails

        return next_rotation

    def update_rotation_schedule(self) -> None:
        """Update the next rotation time based on current settings."""
        next_time = self.calculate_next_rotation()
        if hasattr(self, "next_rotation_at") and next_time is not None:
            self.next_rotation_at = next_time

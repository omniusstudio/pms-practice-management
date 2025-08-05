"""Appointment model for scheduling."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import BaseModel
from .types import UUID


class AppointmentStatus(str, Enum):
    """Appointment status enumeration."""

    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class AppointmentType(str, Enum):
    """Appointment type enumeration."""

    INITIAL_CONSULTATION = "initial_consultation"
    FOLLOW_UP = "follow_up"
    THERAPY_SESSION = "therapy_session"
    MEDICATION_MANAGEMENT = "medication_management"
    GROUP_THERAPY = "group_therapy"
    FAMILY_THERAPY = "family_therapy"
    CRISIS_INTERVENTION = "crisis_intervention"
    ASSESSMENT = "assessment"
    OTHER = "other"


class Appointment(BaseModel):
    """Appointment model for client-provider scheduling."""

    __tablename__ = "appointments"

    # Foreign keys
    client_id: Column[UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_id: Column[UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Scheduling information
    scheduled_start = Column(DateTime(timezone=True), nullable=False)
    scheduled_end = Column(DateTime(timezone=True), nullable=False)
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_end = Column(DateTime(timezone=True), nullable=True)

    # Appointment details
    appointment_type: Column[AppointmentType] = Column(
        SQLEnum(AppointmentType), default=AppointmentType.FOLLOW_UP, nullable=False
    )
    status: Column[AppointmentStatus] = Column(
        SQLEnum(AppointmentStatus), default=AppointmentStatus.SCHEDULED, nullable=False
    )

    # Duration and billing
    duration_minutes = Column(Integer, default=50, nullable=False)
    billable_units = Column(Integer, default=1, nullable=False)

    # Location and format
    location = Column(String(255), nullable=True)  # Office, telehealth, etc.
    is_telehealth = Column(Boolean, default=False, nullable=False)
    meeting_link = Column(String(500), nullable=True)  # For telehealth

    # Notes and reasons
    reason_for_visit = Column(Text, nullable=True)
    appointment_notes = Column(Text, nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    # Reminders and notifications
    reminder_sent = Column(Boolean, default=False, nullable=False)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    confirmation_sent = Column(Boolean, default=False, nullable=False)
    confirmation_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Billing and insurance
    copay_amount = Column(
        String(10), nullable=True
    )  # Store as string to avoid float issues
    insurance_authorization = Column(String(100), nullable=True)

    # Relationships
    client = relationship("Client", back_populates="appointments")
    provider = relationship("Provider", back_populates="appointments")
    notes = relationship(
        "Note", back_populates="appointment", cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_appointment_client", "client_id"),
        Index("idx_appointment_provider", "provider_id"),
        Index("idx_appointment_scheduled_start", "scheduled_start"),
        Index("idx_appointment_status", "status"),
        Index("idx_appointment_type", "appointment_type"),
        Index("idx_appointment_date_range", "scheduled_start", "scheduled_end"),
        Index("idx_appointment_provider_date", "provider_id", "scheduled_start"),
        Index("idx_appointment_client_date", "client_id", "scheduled_start"),
    )

    def is_past(self) -> bool:
        """Check if appointment is in the past."""
        now = datetime.now(timezone.utc)
        scheduled_end = self.scheduled_end
        if scheduled_end.tzinfo is None:
            scheduled_end = scheduled_end.replace(tzinfo=timezone.utc)
        return scheduled_end < now

    def is_today(self) -> bool:
        """Check if appointment is today."""
        today = datetime.now(timezone.utc).date()
        scheduled_start = self.scheduled_start
        if scheduled_start.tzinfo is None:
            scheduled_start = scheduled_start.replace(tzinfo=timezone.utc)
        return scheduled_start.date() == today

    def is_upcoming(self) -> bool:
        """Check if appointment is upcoming (future)."""
        now = datetime.now(timezone.utc)
        scheduled_start = self.scheduled_start
        if scheduled_start.tzinfo is None:
            scheduled_start = scheduled_start.replace(tzinfo=timezone.utc)
        return scheduled_start > now

    @property
    def duration_actual_minutes(self) -> Optional[int]:
        """Get actual duration in minutes if appointment completed."""
        if not (self.actual_start and self.actual_end):
            return None

        delta = self.actual_end - self.actual_start
        return int(delta.total_seconds() / 60)

    def can_be_cancelled(self) -> bool:
        """Check if appointment can be cancelled."""
        return self.status in [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]

    def can_be_rescheduled(self) -> bool:
        """Check if appointment can be rescheduled."""
        return self.status in [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]

    def mark_completed(self, actual_end: Optional[datetime] = None) -> None:
        """Mark appointment as completed."""
        # Implementation would update status in service layer
        pass

    def mark_no_show(self) -> None:
        """Mark appointment as no-show."""
        # Implementation would update status in service layer
        pass

    def cancel(self, reason: Optional[str] = None) -> None:
        """Cancel the appointment."""
        # Implementation would update status in service layer
        pass

    def to_dict(self) -> dict:
        """Convert to dictionary with computed fields."""
        data = super().to_dict()

        # Add computed fields
        data["is_past"] = self.is_past
        data["is_today"] = self.is_today
        data["is_upcoming"] = self.is_upcoming
        data["duration_actual_minutes"] = self.duration_actual_minutes
        data["can_be_cancelled"] = self.can_be_cancelled()
        data["can_be_rescheduled"] = self.can_be_rescheduled()

        return data

    def __repr__(self) -> str:
        """String representation without PHI."""
        return (
            f"<Appointment(id={self.id}, "
            f"status={self.status}, "
            f"scheduled={self.scheduled_start.isoformat()})>"
        )

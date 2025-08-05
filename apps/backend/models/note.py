"""Note model for clinical and administrative notes."""

from enum import Enum

from sqlalchemy import Boolean, Column
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship

from .base import BaseModel
from .types import UUID


class NoteType(str, Enum):
    """Note type enumeration."""

    PROGRESS_NOTE = "progress_note"
    INTAKE_NOTE = "intake_note"
    ASSESSMENT = "assessment"
    TREATMENT_PLAN = "treatment_plan"
    DISCHARGE_SUMMARY = "discharge_summary"
    ADMINISTRATIVE = "administrative"
    BILLING = "billing"
    OTHER = "other"


class Note(BaseModel):
    """Clinical and administrative notes model."""

    __tablename__ = "notes"

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
    appointment_id: Column[UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Note details
    note_type: Column[NoteType] = Column(
        SQLEnum(NoteType), default=NoteType.PROGRESS_NOTE, nullable=False
    )

    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    # Clinical information
    diagnosis_codes = Column(Text, nullable=True)  # ICD-10 codes
    treatment_goals = Column(Text, nullable=True)
    interventions = Column(Text, nullable=True)
    client_response = Column(Text, nullable=True)
    plan = Column(Text, nullable=True)

    # Status and workflow
    is_signed = Column(Boolean, default=False, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    requires_review = Column(Boolean, default=False, nullable=False)

    # Billing and compliance
    billable = Column(Boolean, default=True, nullable=False)
    billing_code = Column(String(20), nullable=True)  # CPT code

    # Relationships
    client = relationship("Client", back_populates="notes")
    provider = relationship("Provider", back_populates="notes")
    appointment = relationship("Appointment", back_populates="notes")

    # Indexes for performance
    __table_args__ = (
        Index("idx_note_client", "client_id"),
        Index("idx_note_provider", "provider_id"),
        Index("idx_note_appointment", "appointment_id"),
        Index("idx_note_type", "note_type"),
        Index("idx_note_signed", "is_signed"),
        Index("idx_note_billable", "billable"),
        Index("idx_note_client_date", "client_id", "created_at"),
        Index("idx_note_provider_date", "provider_id", "created_at"),
    )

    def can_be_edited(self) -> bool:
        """Check if note can be edited."""
        return not (self.is_signed or self.is_locked)

    def can_be_signed(self) -> bool:
        """Check if note can be signed."""
        return not self.is_signed and not self.is_locked

    def sign_note(self) -> None:
        """Sign the note (implementation in service layer)."""
        pass

    def lock_note(self) -> None:
        """Lock the note (implementation in service layer)."""
        pass

    def to_dict(self) -> dict:
        """Convert to dictionary with computed fields."""
        data = super().to_dict()

        # Add computed fields
        data["can_be_edited"] = self.can_be_edited()
        data["can_be_signed"] = self.can_be_signed()

        return data

    def __repr__(self) -> str:
        """String representation without PHI."""
        return (
            f"<Note(id={self.id}, "
            f"type={self.note_type}, "
            f"signed={self.is_signed})>"
        )

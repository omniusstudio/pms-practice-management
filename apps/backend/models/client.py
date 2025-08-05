"""Client model for patient/client data."""

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Column, Date, Index, String, Text
from sqlalchemy.orm import relationship

from .base import BaseModel


class Client(BaseModel):
    """Client/Patient model with HIPAA-compliant data handling."""

    __tablename__ = "clients"

    # Basic demographic information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)

    # Contact information
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(20), nullable=True)

    # Address information
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(10), nullable=True)

    # Demographics
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)

    # Insurance and billing
    insurance_provider = Column(String(255), nullable=True)
    insurance_id = Column(String(100), nullable=True)

    # Emergency contact
    emergency_contact_name = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    emergency_contact_relationship = Column(String(100), nullable=True)

    # Clinical information
    primary_diagnosis = Column(Text, nullable=True)
    secondary_diagnoses = Column(Text, nullable=True)
    medications = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)

    # Status and preferences
    is_active = Column(Boolean, default=True, nullable=False)
    preferred_language = Column(String(50), default="English", nullable=False)
    communication_preferences = Column(Text, nullable=True)

    # Notes (non-clinical)
    intake_notes = Column(Text, nullable=True)
    administrative_notes = Column(Text, nullable=True)

    # Relationships
    appointments = relationship(
        "Appointment", back_populates="client", cascade="all, delete-orphan"
    )
    notes = relationship("Note", back_populates="client", cascade="all, delete-orphan")
    ledger_entries = relationship(
        "LedgerEntry", back_populates="client", cascade="all, delete-orphan"
    )

    # Indexes for performance and compliance
    __table_args__ = (
        Index("idx_client_name", "last_name", "first_name"),
        Index("idx_client_email", "email"),
        Index("idx_client_phone", "phone"),
        Index("idx_client_active", "is_active"),
        Index("idx_client_dob", "date_of_birth"),
    )

    @property
    def full_name(self) -> str:
        """Get client's full name."""
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return " ".join(parts)

    @property
    def display_name(self) -> str:
        """Get display name for UI (first + last)."""
        return f"{self.first_name} {self.last_name}"

    def get_age(self) -> Optional[int]:
        """Calculate client's age if date of birth is available."""
        if not self.date_of_birth:
            return None

        today = date.today()
        age = today.year - self.date_of_birth.year

        # Adjust if birthday hasn't occurred this year
        if today.month < self.date_of_birth.month or (
            today.month == self.date_of_birth.month
            and today.day < self.date_of_birth.day
        ):
            age -= 1

        return age

    def to_dict(self) -> dict:
        """Convert to dictionary with PHI handling."""
        data = super().to_dict()

        # Add computed fields
        data["full_name"] = self.full_name
        data["display_name"] = self.display_name
        data["age"] = self.get_age()

        return data

    def __repr__(self) -> str:
        """String representation without PHI."""
        return f"<Client(id={self.id}, active={self.is_active})>"

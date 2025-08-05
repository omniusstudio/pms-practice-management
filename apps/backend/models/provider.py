"""Provider model for healthcare providers."""

from typing import Optional

from sqlalchemy import Boolean, Column, Index, String, Text
from sqlalchemy.orm import relationship

from .base import BaseModel


class Provider(BaseModel):
    """Healthcare provider model."""

    __tablename__ = "providers"

    # Basic information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)

    # Professional information
    title = Column(String(50), nullable=True)  # Dr., LCSW, etc.
    credentials = Column(String(200), nullable=True)  # MD, PhD, LCSW, etc.
    specialty = Column(String(200), nullable=True)
    license_number = Column(String(100), nullable=True)
    license_state = Column(String(50), nullable=True)

    # Contact information
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone = Column(String(20), nullable=True)
    office_phone = Column(String(20), nullable=True)

    # Office information
    office_address_line1 = Column(String(255), nullable=True)
    office_address_line2 = Column(String(255), nullable=True)
    office_city = Column(String(100), nullable=True)
    office_state = Column(String(50), nullable=True)
    office_zip_code = Column(String(10), nullable=True)

    # Professional details
    npi_number = Column(
        String(20), nullable=True, unique=True
    )  # National Provider Identifier
    tax_id = Column(String(20), nullable=True)  # For billing

    # Scheduling and availability
    default_appointment_duration = Column(
        String(10), default="50", nullable=False
    )  # minutes
    accepts_new_patients = Column(Boolean, default=True, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Notes and bio
    bio = Column(Text, nullable=True)
    administrative_notes = Column(Text, nullable=True)

    # Relationships
    appointments = relationship(
        "Appointment", back_populates="provider", cascade="all, delete-orphan"
    )
    notes = relationship(
        "Note", back_populates="provider", cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_provider_name", "last_name", "first_name"),
        Index("idx_provider_email", "email"),
        Index("idx_provider_active", "is_active"),
        Index("idx_provider_specialty", "specialty"),
        Index("idx_provider_license", "license_number"),
        Index("idx_provider_npi", "npi_number"),
    )

    @property
    def full_name(self) -> str:
        """Get provider's full name."""
        parts = []
        if self.title:
            parts.append(self.title)
        parts.append(self.first_name)
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        name = " ".join(parts)
        if self.credentials:
            name += f", {self.credentials}"
        return name

    @property
    def display_name(self) -> str:
        """Get display name for UI."""
        name = f"{self.first_name} {self.last_name}"
        if self.credentials:
            name += f", {self.credentials}"
        return name

    @property
    def professional_name(self) -> str:
        """Get professional name with title and credentials."""
        parts = []
        if self.title:
            parts.append(self.title)
        parts.append(self.first_name)
        parts.append(self.last_name)
        if self.credentials:
            parts.append(f", {self.credentials}")
        return " ".join(parts)

    def get_office_address(self) -> Optional[str]:
        """Get formatted office address."""
        if not self.office_address_line1:
            return None

        address_parts = [self.office_address_line1]
        if self.office_address_line2:
            address_parts.append(self.office_address_line2)

        city_state_zip = []
        if self.office_city:
            city_state_zip.append(self.office_city)
        if self.office_state:
            city_state_zip.append(self.office_state)
        if self.office_zip_code:
            city_state_zip.append(self.office_zip_code)

        if city_state_zip:
            address_parts.append(", ".join(city_state_zip))

        return "\n".join(address_parts)

    def to_dict(self) -> dict:
        """Convert to dictionary with computed fields."""
        data = super().to_dict()

        # Add computed fields
        data["full_name"] = self.full_name
        data["display_name"] = self.display_name
        data["professional_name"] = self.professional_name
        data["office_address"] = self.get_office_address()

        return data

    def __repr__(self) -> str:
        """String representation without PHI."""
        return f"<Provider(id={self.id}, active={self.is_active})>"

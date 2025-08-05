"""Practice Profile model for healthcare practices."""

from sqlalchemy import Boolean, Column, Index, String, Text
from sqlalchemy.orm import relationship

from .base import BaseModel


class PracticeProfile(BaseModel):
    """Practice Profile model for healthcare practice management."""

    __tablename__ = "practice_profiles"

    def __init__(self, **kwargs):
        """Initialize practice profile with defaults."""
        # Set defaults if not provided
        kwargs.setdefault("country", "United States")
        kwargs.setdefault("timezone", "America/New_York")
        kwargs.setdefault("default_appointment_duration", "50")
        kwargs.setdefault("accepts_new_patients", True)
        kwargs.setdefault("is_active", True)
        super().__init__(**kwargs)

    # Basic practice information
    name = Column(String(255), nullable=False)
    legal_name = Column(String(255), nullable=True)
    tax_id = Column(String(20), nullable=True)  # EIN for billing
    npi_number = Column(String(20), nullable=True, unique=True)

    # Contact information
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(20), nullable=True)
    fax = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)

    # Primary address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(10), nullable=True)
    country = Column(String(100), default="United States", nullable=False)

    # Timezone and operational settings
    timezone = Column(String(50), default="America/New_York", nullable=False)
    default_appointment_duration = Column(
        String(10), default="50", nullable=False
    )  # minutes

    # Practice settings
    accepts_new_patients = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Billing and insurance
    billing_provider_name = Column(String(255), nullable=True)
    billing_contact_email = Column(String(255), nullable=True)
    billing_contact_phone = Column(String(20), nullable=True)

    # Administrative notes
    description = Column(Text, nullable=True)
    administrative_notes = Column(Text, nullable=True)

    # Relationships
    locations = relationship(
        "Location",
        back_populates="practice_profile",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_practice_name", "name"),
        Index("idx_practice_active", "is_active"),
        Index("idx_practice_tenant", "tenant_id"),
        Index("idx_practice_npi", "npi_number"),
        Index("idx_practice_email", "email"),
    )

    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = []
        if self.address_line1:
            parts.append(str(self.address_line1))
        if self.address_line2:
            parts.append(str(self.address_line2))
        if self.city and self.state:
            parts.append(f"{self.city}, {self.state}")
        if self.zip_code:
            parts.append(str(self.zip_code))
        return ", ".join(parts) if parts else ""

    @property
    def display_name(self) -> str:
        """Get display name for the practice."""
        return str(self.name) if self.name else "Unnamed Practice"

    def __repr__(self) -> str:
        """String representation without PHI."""
        return f"<PracticeProfile(id={self.id}, name='{self.name}')>"

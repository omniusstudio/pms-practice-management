"""Location model for practice locations."""

from sqlalchemy import Boolean, Column, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship

from .base import BaseModel
from .types import UUID


class Location(BaseModel):
    """Location model for practice office locations."""

    __tablename__ = "locations"

    def __init__(self, **kwargs):
        """Initialize location with defaults."""
        # Set defaults if not provided
        kwargs.setdefault("location_type", "office")
        kwargs.setdefault("country", "United States")
        kwargs.setdefault("timezone", "America/New_York")
        kwargs.setdefault("is_primary", False)
        kwargs.setdefault("is_active", True)
        kwargs.setdefault("accepts_appointments", True)
        kwargs.setdefault("wheelchair_accessible", False)
        kwargs.setdefault("parking_available", False)
        kwargs.setdefault("public_transport_accessible", False)
        super().__init__(**kwargs)

    # Foreign key to practice profile
    practice_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("practice_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Location identification
    name = Column(String(255), nullable=False)
    location_type = Column(
        String(50), default="office", nullable=False
    )  # office, clinic, telehealth, etc.

    # Contact information
    phone = Column(String(20), nullable=True)
    fax = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)

    # Address information
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)
    zip_code = Column(String(10), nullable=False)
    country = Column(String(100), default="United States", nullable=False)

    # Operational settings
    timezone = Column(String(50), default="America/New_York", nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    accepts_appointments = Column(Boolean, default=True, nullable=False)

    # Accessibility and features
    wheelchair_accessible = Column(Boolean, default=False, nullable=False)
    parking_available = Column(Boolean, default=False, nullable=False)
    public_transport_accessible = Column(Boolean, default=False, nullable=False)

    # Operating hours (stored as text for flexibility)
    operating_hours = Column(Text, nullable=True)
    special_instructions = Column(Text, nullable=True)

    # Administrative notes
    description = Column(Text, nullable=True)
    administrative_notes = Column(Text, nullable=True)

    # Relationships
    practice_profile = relationship("PracticeProfile", back_populates="locations")

    # Indexes for performance
    __table_args__ = (
        Index("idx_location_practice", "practice_profile_id"),
        Index("idx_location_name", "name"),
        Index("idx_location_active", "is_active"),
        Index("idx_location_primary", "is_primary"),
        Index("idx_location_tenant", "tenant_id"),
        Index("idx_location_city_state", "city", "state"),
    )

    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = [str(self.address_line1)]
        if self.address_line2:
            parts.append(str(self.address_line2))
        parts.append(f"{self.city}, {self.state} {self.zip_code}")
        if self.country != "United States":
            parts.append(str(self.country))
        return ", ".join(parts)

    @property
    def display_name(self) -> str:
        """Get display name for the location."""
        return str(self.name) if self.name else "Unnamed Location"

    @property
    def short_address(self) -> str:
        """Get short address (city, state)."""
        return f"{self.city}, {self.state}"

    def __repr__(self) -> str:
        """String representation without PHI."""
        return f"<Location(id={self.id}, name='{self.name}', " f"city='{self.city}')>"

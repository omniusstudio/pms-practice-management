"""Tests for practice profile and location models."""

import pytest
from sqlalchemy.exc import IntegrityError

from models.location import Location
from models.practice_profile import PracticeProfile


class TestPracticeProfile:
    """Test cases for PracticeProfile model."""

    def test_practice_profile_creation(self, test_session):
        """Test creating a practice profile."""
        practice = PracticeProfile(
            name="Test Practice",
            legal_name="Test Practice LLC",
            tax_id="12-3456789",
            npi_number="1234567890",
            email="test@practice.com",
            phone="555-0100",
            address_line1="123 Test St",
            city="Test City",
            state="CA",
            zip_code="12345",
            timezone="America/Los_Angeles",
            tenant_id="test_tenant",
        )

        test_session.add(practice)
        test_session.flush()

        assert practice.id is not None
        assert practice.name == "Test Practice"
        assert practice.legal_name == "Test Practice LLC"
        assert practice.tax_id == "12-3456789"
        assert practice.npi_number == "1234567890"
        assert practice.email == "test@practice.com"
        assert practice.phone == "555-0100"
        assert practice.timezone == "America/Los_Angeles"
        assert practice.tenant_id == "test_tenant"
        assert practice.is_active is True
        assert practice.accepts_new_patients is True
        assert practice.created_at is not None
        assert practice.updated_at is not None

    def test_practice_profile_display_name(self, test_session):
        """Test practice profile display name property."""
        practice = PracticeProfile(name="Test Practice")
        assert practice.display_name == "Test Practice"

        practice_no_name = PracticeProfile()
        assert practice_no_name.display_name == "Unnamed Practice"

    def test_practice_profile_full_address(self, test_session):
        """Test practice profile full address property."""
        practice = PracticeProfile(
            address_line1="123 Main St",
            address_line2="Suite 100",
            city="San Francisco",
            state="CA",
            zip_code="94102",
        )

        expected = "123 Main St, Suite 100, San Francisco, CA, 94102"
        assert practice.full_address == expected

        # Test with minimal address
        practice_minimal = PracticeProfile(
            address_line1="456 Oak Ave", city="Oakland", state="CA"
        )
        expected_minimal = "456 Oak Ave, Oakland, CA"
        assert practice_minimal.full_address == expected_minimal

        # Test with no address
        practice_no_address = PracticeProfile()
        assert practice_no_address.full_address == ""

    def test_practice_profile_unique_npi(self, test_session):
        """Test that NPI numbers must be unique."""
        practice1 = PracticeProfile(name="Practice 1", npi_number="1234567890")
        practice2 = PracticeProfile(
            name="Practice 2", npi_number="1234567890"  # Same NPI
        )

        test_session.add(practice1)
        test_session.flush()

        test_session.add(practice2)

        with pytest.raises(IntegrityError):
            test_session.flush()

    def test_practice_profile_defaults(self, test_session):
        """Test practice profile default values."""
        practice = PracticeProfile(name="Test Practice")

        assert practice.country == "United States"
        assert practice.timezone == "America/New_York"
        assert practice.default_appointment_duration == "50"
        assert practice.accepts_new_patients is True
        assert practice.is_active is True

    def test_practice_profile_repr(self, test_session):
        """Test practice profile string representation."""
        practice = PracticeProfile(name="Test Practice")
        test_session.add(practice)
        test_session.flush()

        repr_str = repr(practice)
        assert "PracticeProfile" in repr_str
        assert str(practice.id) in repr_str
        assert "Test Practice" in repr_str


class TestLocation:
    """Test cases for Location model."""

    def test_location_creation(self, test_session):
        """Test creating a location."""
        # First create a practice profile
        practice = PracticeProfile(name="Test Practice", tenant_id="test_tenant")
        test_session.add(practice)
        test_session.flush()

        location = Location(
            practice_profile_id=practice.id,
            name="Main Office",
            location_type="office",
            phone="555-0200",
            email="main@practice.com",
            address_line1="456 Business Ave",
            city="Business City",
            state="CA",
            zip_code="54321",
            timezone="America/Los_Angeles",
            is_primary=True,
            tenant_id="test_tenant",
        )

        test_session.add(location)
        test_session.flush()

        assert location.id is not None
        assert location.practice_profile_id == practice.id
        assert location.name == "Main Office"
        assert location.location_type == "office"
        assert location.phone == "555-0200"
        assert location.email == "main@practice.com"
        assert location.address_line1 == "456 Business Ave"
        assert location.city == "Business City"
        assert location.state == "CA"
        assert location.zip_code == "54321"
        assert location.timezone == "America/Los_Angeles"
        assert location.is_primary is True
        assert location.tenant_id == "test_tenant"
        assert location.is_active is True
        assert location.accepts_appointments is True
        assert location.created_at is not None
        assert location.updated_at is not None

    def test_location_display_name(self, test_session):
        """Test location display name property."""
        location = Location(name="Test Location")
        assert location.display_name == "Test Location"

        location_no_name = Location()
        assert location_no_name.display_name == "Unnamed Location"

    def test_location_full_address(self, test_session):
        """Test location full address property."""
        location = Location(
            address_line1="789 Location St",
            address_line2="Floor 2",
            city="Location City",
            state="NY",
            zip_code="10001",
            country="United States",
        )

        expected = "789 Location St, Floor 2, Location City, NY 10001"
        assert location.full_address == expected

        # Test with different country
        location_intl = Location(
            address_line1="123 International Blvd",
            city="Toronto",
            state="ON",
            zip_code="M5V 3A8",
            country="Canada",
        )

        expected_intl = "123 International Blvd, Toronto, ON M5V 3A8, Canada"
        assert location_intl.full_address == expected_intl

    def test_location_short_address(self, test_session):
        """Test location short address property."""
        location = Location(city="Short City", state="SC")

        assert location.short_address == "Short City, SC"

    def test_location_defaults(self, test_session):
        """Test location default values."""
        location = Location(
            name="Test Location",
            address_line1="123 Test St",
            city="Test City",
            state="CA",
            zip_code="12345",
        )

        assert location.location_type == "office"
        assert location.country == "United States"
        assert location.timezone == "America/New_York"
        assert location.is_primary is False
        assert location.is_active is True
        assert location.accepts_appointments is True
        assert location.wheelchair_accessible is False
        assert location.parking_available is False
        assert location.public_transport_accessible is False

    def test_location_practice_relationship(self, test_session):
        """Test location-practice relationship."""
        practice = PracticeProfile(name="Test Practice", tenant_id="test_tenant")
        test_session.add(practice)
        test_session.flush()

        location = Location(
            practice_profile_id=practice.id,
            name="Test Location",
            address_line1="123 Test St",
            city="Test City",
            state="CA",
            zip_code="12345",
            tenant_id="test_tenant",
        )

        test_session.add(location)
        test_session.flush()

        # Test forward relationship
        assert location.practice_profile == practice

        # Test reverse relationship
        assert location in practice.locations
        assert len(practice.locations) == 1

    def test_location_cascade_delete(self, test_session):
        """Test that locations are deleted when practice is deleted."""
        practice = PracticeProfile(name="Test Practice", tenant_id="test_tenant")
        test_session.add(practice)
        test_session.flush()

        location = Location(
            practice_profile_id=practice.id,
            name="Test Location",
            address_line1="123 Test St",
            city="Test City",
            state="CA",
            zip_code="12345",
            tenant_id="test_tenant",
        )

        test_session.add(location)
        test_session.flush()

        location_id = location.id

        # Delete the practice
        test_session.delete(practice)
        test_session.flush()

        # Location should be deleted due to cascade
        deleted_location = test_session.get(Location, location_id)
        assert deleted_location is None

    def test_location_repr(self, test_session):
        """Test location string representation."""
        practice = PracticeProfile(name="Test Practice", tenant_id="test_tenant")
        test_session.add(practice)
        test_session.flush()

        location = Location(
            name="Test Location",
            address_line1="123 Test St",
            city="Test City",
            state="CA",
            zip_code="12345",
            practice_profile_id=practice.id,
        )
        test_session.add(location)
        test_session.flush()

        repr_str = repr(location)
        assert "Location" in repr_str
        assert str(location.id) in repr_str
        assert "Test Location" in repr_str
        assert "Test City" in repr_str


class TestPracticeLocationIntegration:
    """Integration tests for practice and location models."""

    def test_multi_tenant_isolation(self, test_session):
        """Test that tenant isolation works correctly."""
        # Create practices for different tenants
        practice1 = PracticeProfile(name="Tenant 1 Practice", tenant_id="tenant_1")
        practice2 = PracticeProfile(name="Tenant 2 Practice", tenant_id="tenant_2")

        test_session.add_all([practice1, practice2])
        test_session.flush()

        # Create locations for each practice
        location1 = Location(
            practice_profile_id=practice1.id,
            name="Tenant 1 Location",
            address_line1="123 Tenant 1 St",
            city="City 1",
            state="CA",
            zip_code="12345",
            tenant_id="tenant_1",
        )

        location2 = Location(
            practice_profile_id=practice2.id,
            name="Tenant 2 Location",
            address_line1="456 Tenant 2 Ave",
            city="City 2",
            state="NY",
            zip_code="54321",
            tenant_id="tenant_2",
        )

        test_session.add_all([location1, location2])
        test_session.flush()

        # Verify tenant isolation
        assert practice1.tenant_id != practice2.tenant_id
        assert location1.tenant_id != location2.tenant_id
        assert location1.tenant_id == practice1.tenant_id
        assert location2.tenant_id == practice2.tenant_id

    def test_multiple_locations_per_practice(self, test_session):
        """Test that a practice can have multiple locations."""
        practice = PracticeProfile(
            name="Multi-Location Practice", tenant_id="test_tenant"
        )
        test_session.add(practice)
        test_session.flush()

        # Create multiple locations
        locations = [
            Location(
                practice_profile_id=practice.id,
                name="Main Office",
                address_line1="123 Main St",
                city="Main City",
                state="CA",
                zip_code="12345",
                is_primary=True,
                tenant_id="test_tenant",
            ),
            Location(
                practice_profile_id=practice.id,
                name="Satellite Office",
                address_line1="456 Satellite Ave",
                city="Satellite City",
                state="CA",
                zip_code="54321",
                is_primary=False,
                tenant_id="test_tenant",
            ),
            Location(
                practice_profile_id=practice.id,
                name="Telehealth Hub",
                address_line1="Virtual Location",
                city="Online",
                state="CA",
                zip_code="00000",
                location_type="telehealth",
                is_primary=False,
                tenant_id="test_tenant",
            ),
        ]

        test_session.add_all(locations)
        test_session.flush()

        # Verify relationships
        assert len(practice.locations) == 3

        # Check primary location
        primary_locations = [loc for loc in practice.locations if loc.is_primary]
        assert len(primary_locations) == 1
        assert primary_locations[0].name == "Main Office"

        # Check location types
        telehealth_locations = [
            loc for loc in practice.locations if loc.location_type == "telehealth"
        ]
        assert len(telehealth_locations) == 1
        assert telehealth_locations[0].name == "Telehealth Hub"

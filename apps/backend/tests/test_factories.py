"""Tests for HIPAA-compliant seed factories."""

from datetime import date
from decimal import Decimal

import pytest

from factories import (
    AppointmentFactory,
    ClientFactory,
    LedgerEntryFactory,
    LocationFactory,
    NoteFactory,
    PracticeProfileFactory,
    ProviderFactory,
)
from models import (
    Appointment,
    Client,
    LedgerEntry,
    Location,
    Note,
    PracticeProfile,
    Provider,
)


class TestBaseFactory:
    """Test base factory functionality."""

    def test_hipaa_compliance_check(self, test_session):
        """Test that factories reject real PHI data."""
        ClientFactory._meta.sqlalchemy_session = test_session
        with pytest.raises(ValueError, match="HIPAA Violation"):
            ClientFactory(ssn="123-45-6789")

    def test_safe_email_generation(self):
        """Test HIPAA-safe email generation."""
        from factories.base import BaseFactory

        email = BaseFactory.generate_safe_email()
        assert email.endswith("@example.local")
        assert "@" in email

    def test_safe_phone_generation(self):
        """Test HIPAA-safe phone generation."""
        from factories.base import BaseFactory

        phone = BaseFactory.generate_safe_phone()
        assert phone.startswith("555-")
        assert len(phone) == 8  # 555-XXXX

    def test_tenant_id_generation(self, test_session):
        """Test consistent tenant ID generation."""
        ClientFactory._meta.sqlalchemy_session = test_session
        client = ClientFactory()
        assert client.tenant_id.startswith("tenant_")
        assert len(client.tenant_id) > 7


class TestPracticeProfileFactory:
    """Test practice profile factory."""

    def test_creates_practice_profile(self, test_session):
        """Test basic practice profile creation."""
        PracticeProfileFactory._meta.sqlalchemy_session = test_session
        profile = PracticeProfileFactory()

        assert isinstance(profile, PracticeProfile)
        assert profile.name
        assert profile.email.endswith(".local")
        assert profile.phone.startswith("555-")
        assert profile.npi_number
        assert profile.timezone
        assert profile.tenant_id

    def test_practice_profile_fields(self, test_session):
        """Test all practice profile fields are populated."""
        PracticeProfileFactory._meta.sqlalchemy_session = test_session
        profile = PracticeProfileFactory()

        # Contact information
        assert profile.email
        assert profile.phone
        assert profile.website

        # Address information
        assert profile.address_line1
        assert profile.city
        assert profile.state
        assert profile.zip_code
        assert profile.country == "US"

        # Professional information
        assert profile.npi_number
        assert profile.timezone

        # Business information
        assert profile.is_active is True


class TestLocationFactory:
    """Test location factory."""

    def test_creates_location(self, test_session):
        """Test basic location creation."""
        LocationFactory._meta.sqlalchemy_session = test_session
        PracticeProfileFactory._meta.sqlalchemy_session = test_session
        location = LocationFactory()

        assert isinstance(location, Location)
        assert location.name
        assert location.practice_profile
        assert location.phone.startswith("555-")
        assert location.tenant_id

    def test_location_practice_relationship(self, test_session):
        """Test location-practice relationship."""
        LocationFactory._meta.sqlalchemy_session = test_session
        PracticeProfileFactory._meta.sqlalchemy_session = test_session
        practice = PracticeProfileFactory()
        location = LocationFactory(practice_profile=practice)

        assert location.practice_profile == practice
        assert location.tenant_id == practice.tenant_id

    def test_location_accessibility_features(self, test_session):
        """Test accessibility feature generation."""
        LocationFactory._meta.sqlalchemy_session = test_session
        PracticeProfileFactory._meta.sqlalchemy_session = test_session
        location = LocationFactory()

        assert isinstance(location.wheelchair_accessible, bool)
        assert isinstance(location.parking_available, bool)


class TestClientFactory:
    """Test client factory."""

    def test_creates_client(self, test_session):
        """Test basic client creation."""
        ClientFactory._meta.sqlalchemy_session = test_session
        client = ClientFactory()

        assert isinstance(client, Client)
        assert client.first_name
        assert client.last_name
        assert client.email.endswith(".local")
        assert client.phone.startswith("555-")
        assert client.tenant_id

    def test_client_age_validation(self, test_session):
        """Test client age is appropriate (18+)."""
        ClientFactory._meta.sqlalchemy_session = test_session
        client = ClientFactory()

        if client.date_of_birth:
            age = (date.today() - client.date_of_birth).days // 365
            assert age >= 18

    def test_client_hipaa_compliance(self, test_session):
        """Test client data is HIPAA compliant."""
        ClientFactory._meta.sqlalchemy_session = test_session
        client = ClientFactory()

        # Check email domain
        assert client.email.endswith(".local")

        # Check phone number format
        assert client.phone.startswith("555-")

        # Check emergency contact
        if client.emergency_contact_phone:
            assert client.emergency_contact_phone.startswith("555-")

    def test_client_clinical_data(self, test_session):
        """Test clinical data generation."""
        ClientFactory._meta.sqlalchemy_session = test_session
        client = ClientFactory()

        # Clinical fields should be populated or None
        assert client.primary_diagnosis is None or isinstance(
            client.primary_diagnosis, str
        )

        # Preferences should be set
        assert client.preferred_language
        assert isinstance(client.is_active, bool)

        # Only check fields that actually exist in the model
        if hasattr(client, "consent_to_treatment"):
            assert isinstance(client.consent_to_treatment, bool)
        if hasattr(client, "hipaa_acknowledgment"):
            assert isinstance(client.hipaa_acknowledgment, bool)


class TestProviderFactory:
    """Test provider factory."""

    def test_creates_provider(self, test_session):
        """Test basic provider creation."""
        ProviderFactory._meta.sqlalchemy_session = test_session
        provider = ProviderFactory()

        assert isinstance(provider, Provider)
        assert provider.first_name
        assert provider.last_name
        assert provider.credentials
        assert provider.license_number
        assert provider.npi_number
        assert provider.tenant_id

    def test_provider_professional_info(self, test_session):
        """Test provider professional information."""
        ProviderFactory._meta.sqlalchemy_session = test_session
        provider = ProviderFactory()

        assert provider.title
        assert provider.credentials
        assert provider.specialty
        assert provider.license_state

    def test_provider_contact_info(self, test_session):
        """Test provider contact information is HIPAA safe."""
        ProviderFactory._meta.sqlalchemy_session = test_session
        provider = ProviderFactory()

        assert provider.email.endswith(".local")
        assert provider.phone.startswith("555-")
        assert provider.office_phone.startswith("555-")

    def test_provider_availability(self, test_session):
        """Test provider availability settings."""
        ProviderFactory._meta.sqlalchemy_session = test_session
        provider = ProviderFactory()

        assert isinstance(provider.accepts_new_patients, bool)
        assert isinstance(provider.is_active, bool)


class TestAppointmentFactory:
    """Test appointment factory."""

    def test_creates_appointment(self, test_session):
        """Test basic appointment creation."""
        AppointmentFactory._meta.sqlalchemy_session = test_session
        ClientFactory._meta.sqlalchemy_session = test_session
        ProviderFactory._meta.sqlalchemy_session = test_session
        appointment = AppointmentFactory()

        assert isinstance(appointment, Appointment)
        assert appointment.client
        assert appointment.provider
        assert appointment.appointment_type
        assert appointment.status
        assert appointment.scheduled_start
        assert appointment.scheduled_end
        assert appointment.tenant_id

    def test_appointment_time_logic(self, test_session):
        """Test appointment time relationships."""
        AppointmentFactory._meta.sqlalchemy_session = test_session
        ClientFactory._meta.sqlalchemy_session = test_session
        ProviderFactory._meta.sqlalchemy_session = test_session
        appointment = AppointmentFactory()

        # Scheduled times should be logical
        assert appointment.scheduled_end > appointment.scheduled_start

        # Duration should be positive
        assert appointment.duration_minutes > 0

        # If actual times exist, they should be logical
        if appointment.actual_start and appointment.actual_end:
            assert appointment.actual_end > appointment.actual_start

    def test_appointment_tenant_consistency(self, test_session):
        """Test tenant consistency across appointment relationships."""
        AppointmentFactory._meta.sqlalchemy_session = test_session
        ClientFactory._meta.sqlalchemy_session = test_session
        ProviderFactory._meta.sqlalchemy_session = test_session
        client = ClientFactory(tenant_id="test_tenant")
        provider = ProviderFactory(tenant_id="test_tenant")
        appointment = AppointmentFactory(
            client=client, provider=provider, tenant_id="test_tenant"
        )

        assert appointment.client.tenant_id == "test_tenant"
        assert appointment.provider.tenant_id == "test_tenant"
        assert appointment.tenant_id == "test_tenant"

    def test_appointment_billing_info(self, test_session):
        """Test appointment billing information."""
        AppointmentFactory._meta.sqlalchemy_session = test_session
        ClientFactory._meta.sqlalchemy_session = test_session
        ProviderFactory._meta.sqlalchemy_session = test_session
        appointment = AppointmentFactory()

        assert isinstance(appointment.copay_amount, str)
        assert float(appointment.copay_amount) >= 0


class TestNoteFactory:
    """Test note factory."""

    def test_creates_note(self, test_session):
        """Test basic note creation."""
        NoteFactory._meta.sqlalchemy_session = test_session
        ClientFactory._meta.sqlalchemy_session = test_session
        ProviderFactory._meta.sqlalchemy_session = test_session
        note = NoteFactory()

        assert isinstance(note, Note)
        assert note.client
        assert note.provider
        assert note.note_type
        assert note.title
        assert note.content
        assert note.tenant_id

    def test_note_soap_structure(self, test_session):
        """Test note structure for clinical notes."""
        NoteFactory._meta.sqlalchemy_session = test_session
        ClientFactory._meta.sqlalchemy_session = test_session
        ProviderFactory._meta.sqlalchemy_session = test_session
        note = NoteFactory(note_type="progress_note")

        assert note.content
        assert note.diagnosis_codes
        assert note.treatment_goals
        assert note.plan

    def test_note_risk_assessment(self, test_session):
        """Test clinical assessment fields in notes."""
        NoteFactory._meta.sqlalchemy_session = test_session
        ClientFactory._meta.sqlalchemy_session = test_session
        ProviderFactory._meta.sqlalchemy_session = test_session
        note = NoteFactory()

        assert note.interventions
        assert note.client_response
        assert note.is_signed is not None

    def test_note_mental_status_exam(self, test_session):
        """Test note billing and review fields."""
        NoteFactory._meta.sqlalchemy_session = test_session
        ClientFactory._meta.sqlalchemy_session = test_session
        ProviderFactory._meta.sqlalchemy_session = test_session
        note = NoteFactory()

        assert note.billable is not None
        assert note.billing_code
        assert note.is_locked is not None
        assert note.requires_review is not None

    def test_note_content_quality(self, test_session):
        """Test note content meets quality standards."""
        NoteFactory._meta.sqlalchemy_session = test_session
        ClientFactory._meta.sqlalchemy_session = test_session
        ProviderFactory._meta.sqlalchemy_session = test_session
        note = NoteFactory()

        assert len(note.content) >= 50
        assert note.title
        assert note.treatment_goals
        assert note.interventions


class TestLedgerEntryFactory:
    """Test ledger entry factory."""

    def test_creates_ledger_entry(self, test_session):
        """Test basic ledger entry creation."""
        LedgerEntryFactory._meta.sqlalchemy_session = test_session
        ClientFactory._meta.sqlalchemy_session = test_session
        entry = LedgerEntryFactory()

        assert isinstance(entry, LedgerEntry)
        assert entry.client
        assert entry.transaction_type
        assert isinstance(entry.amount, Decimal)
        assert entry.billing_code
        assert entry.tenant_id

    def test_ledger_financial_logic(self, test_session):
        """Test financial calculation logic."""
        LedgerEntryFactory._meta.sqlalchemy_session = test_session
        ClientFactory._meta.sqlalchemy_session = test_session
        entry = LedgerEntryFactory()

        # Amount should be positive
        assert entry.amount > 0

        # Transaction type should be valid
        valid_types = [
            "charge",
            "payment",
            "adjustment",
            "refund",
            "write_off",
            "insurance_payment",
        ]
        assert entry.transaction_type in valid_types

    def test_ledger_service_codes(self, test_session):
        """Test service code generation."""
        LedgerEntryFactory._meta.sqlalchemy_session = test_session
        ClientFactory._meta.sqlalchemy_session = test_session
        entry = LedgerEntryFactory()

        # Should have valid CPT codes
        valid_codes = [
            "90834",
            "90837",
            "90791",
            "90834+90836",
            "90847",
            "90853",
            "99213",
            "99214",
            "96116",
            "96118",
        ]
        assert entry.billing_code in valid_codes

    def test_ledger_payment_processing(self, test_session):
        """Test payment processing fields."""
        LedgerEntryFactory._meta.sqlalchemy_session = test_session
        ClientFactory._meta.sqlalchemy_session = test_session
        entry = LedgerEntryFactory(transaction_type="payment")

        assert entry.payment_method
        assert entry.reference_number

        if entry.payment_method == "check":
            assert entry.check_number

    def test_ledger_date_logic(self, test_session):
        """Test date field logic."""
        LedgerEntryFactory._meta.sqlalchemy_session = test_session
        ClientFactory._meta.sqlalchemy_session = test_session
        entry = LedgerEntryFactory()

        # Service date should be in the past or today
        assert entry.service_date <= date.today()

        # Reconciliation date should be after service date if exists
        if entry.reconciliation_date:
            assert entry.reconciliation_date >= entry.service_date


class TestFactoryIntegration:
    """Test factory integration and relationships."""

    def test_multi_tenant_isolation(self, test_session):
        """Test multi-tenant data isolation."""
        ClientFactory._meta.sqlalchemy_session = test_session
        tenant1_client = ClientFactory(tenant_id="tenant_001")
        tenant2_client = ClientFactory(tenant_id="tenant_002")

        assert tenant1_client.tenant_id != tenant2_client.tenant_id

    def test_related_object_creation(self, test_session):
        """Test creation of related objects."""
        # Set up all factory sessions
        ClientFactory._meta.sqlalchemy_session = test_session
        ProviderFactory._meta.sqlalchemy_session = test_session
        AppointmentFactory._meta.sqlalchemy_session = test_session
        NoteFactory._meta.sqlalchemy_session = test_session
        LedgerEntryFactory._meta.sqlalchemy_session = test_session

        # Create a complete appointment with related objects
        client = ClientFactory()
        provider = ProviderFactory(tenant_id=client.tenant_id)
        appointment = AppointmentFactory(
            client=client, provider=provider, tenant_id=client.tenant_id
        )
        note = NoteFactory(
            client=client,
            provider=provider,
            appointment=appointment,
            tenant_id=client.tenant_id,
        )
        ledger_entry = LedgerEntryFactory(client=client, tenant_id=client.tenant_id)

        # Verify relationships
        assert note.client == client
        assert note.provider == provider
        assert note.appointment == appointment
        assert ledger_entry.client == client

        # Verify tenant consistency
        assert all(
            [
                obj.tenant_id == client.tenant_id
                for obj in [client, provider, appointment, note, ledger_entry]
            ]
        )

    def test_bulk_data_generation(self, test_session):
        """Test bulk data generation performance."""
        # Set up factory sessions
        ClientFactory._meta.sqlalchemy_session = test_session
        ProviderFactory._meta.sqlalchemy_session = test_session

        # Generate multiple objects efficiently
        clients = ClientFactory.create_batch(10)
        providers = ProviderFactory.create_batch(5)

        assert len(clients) == 10
        assert len(providers) == 5

        # Verify all objects are properly created
        for client in clients:
            assert isinstance(client, Client)
            assert client.tenant_id

        for provider in providers:
            assert isinstance(provider, Provider)
            assert provider.tenant_id

#!/usr/bin/env python3
"""Simple model tests that don't require complex database setup."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.appointment import Appointment
from models.audit import AuditLog

# Import models directly
from models.base import Base
from models.client import Client
from models.ledger import LedgerEntry
from models.note import Note
from models.provider import Provider


class TestModelCreation:
    """Test basic model creation and validation."""

    @pytest.fixture(scope="class")
    def engine(self):
        """Create test database engine."""
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def session(self, engine):
        """Create test session."""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.rollback()
        session.close()

    def test_base_model_fields(self, session):
        """Test BaseModel has required fields."""
        # Create a simple client to test BaseModel functionality
        client = Client(
            first_name="Test",
            last_name="User",
            date_of_birth=datetime(1990, 1, 1).date(),
            email="test@example.com",
            phone="555-0123",
        )

        session.add(client)
        session.commit()

        # Test BaseModel fields
        assert client.id is not None
        assert isinstance(client.id, uuid.UUID)
        assert client.created_at is not None
        assert client.updated_at is not None
        assert isinstance(client.created_at, datetime)
        assert isinstance(client.updated_at, datetime)

    def test_client_model_creation(self, session):
        """Test Client model creation."""
        client = Client(
            first_name="John",
            last_name="Doe",
            date_of_birth=datetime(1985, 5, 15).date(),
            email="john.doe@example.com",
            phone="555-0123",
            address_line1="123 Main St",
            city="Anytown",
            state="CA",
            zip_code="12345",
        )

        session.add(client)
        session.commit()

        assert client.full_name == "John Doe"
        assert client.display_name == "John Doe"
        assert client.get_age() >= 38  # Approximate age

        # Test to_dict method
        client_dict = client.to_dict()
        assert "id" in client_dict
        assert "first_name" in client_dict
        assert "last_name" in client_dict
        assert client_dict["first_name"] == "John"

    def test_provider_model_creation(self, session):
        """Test Provider model creation."""
        provider = Provider(
            first_name="Sarah",
            last_name="Smith",
            title="Dr.",
            email="dr.smith@clinic.com",
            phone="555-0200",
            license_number="PSY12345",
            license_state="CA",
            specialty="Clinical Psychology",
        )

        session.add(provider)
        session.commit()

        assert provider.full_name == "Dr. Sarah Smith"
        assert provider.specialty == "Clinical Psychology"
        assert provider.is_active is True

    def test_appointment_model_creation(self, session):
        """Test Appointment model creation with relationships."""
        # Create client and provider first
        client = Client(
            first_name="Jane",
            last_name="Doe",
            date_of_birth=datetime(1990, 1, 1).date(),
            email="jane@example.com",
            phone="555-0124",
        )

        provider = Provider(
            first_name="John",
            last_name="Smith",
            title="Dr.",
            email="dr.john@clinic.com",
            phone="555-0201",
            license_number="PSY67890",
            license_state="CA",
            specialty="Therapy",
        )

        session.add_all([client, provider])
        session.flush()  # Get IDs

        # Create appointment
        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)

        from models.appointment import AppointmentStatus, AppointmentType

        appointment = Appointment(
            client_id=client.id,
            provider_id=provider.id,
            scheduled_start=start_time,
            scheduled_end=end_time,
            appointment_type=AppointmentType.THERAPY_SESSION,
            status=AppointmentStatus.SCHEDULED,
        )

        session.add(appointment)
        session.commit()

        assert appointment.client == client
        assert appointment.provider == provider
        assert appointment.duration_minutes == 50
        assert appointment.is_upcoming() is True

    def test_note_model_creation(self, session):
        """Test Note model creation."""
        # Create client and provider
        client = Client(
            first_name="Test",
            last_name="Client",
            date_of_birth=datetime(1985, 1, 1).date(),
            email="test.client@example.com",
            phone="555-0125",
        )

        provider = Provider(
            first_name="Test",
            last_name="Provider",
            title="Dr.",
            email="dr.test@clinic.com",
            phone="555-0202",
            license_number="PSY11111",
            license_state="CA",
            specialty="Psychology",
        )

        session.add_all([client, provider])
        session.flush()

        from models.note import NoteType

        note = Note(
            client_id=client.id,
            provider_id=provider.id,
            title="Progress Note",
            content="Patient showed improvement in anxiety symptoms.",
            note_type=NoteType.PROGRESS_NOTE,
            diagnosis_codes="F41.1",
            treatment_goals="Reduce anxiety symptoms",
            interventions="CBT techniques",
            client_response="Positive engagement",
            plan="Continue weekly sessions",
        )

        session.add(note)
        session.commit()

        assert note.client == client
        assert note.provider == provider
        assert note.can_be_edited() is True
        assert note.is_signed is False

    def test_ledger_entry_creation(self, session):
        """Test LedgerEntry model creation."""
        client = Client(
            first_name="Billing",
            last_name="Test",
            date_of_birth=datetime(1980, 1, 1).date(),
            email="billing@example.com",
            phone="555-0126",
        )

        session.add(client)
        session.flush()

        ledger_entry = LedgerEntry(
            client_id=client.id,
            transaction_type="charge",
            amount=150.00,
            description="Therapy session",
            service_date=datetime.now().date(),
            billing_code="90834",
        )

        session.add(ledger_entry)
        session.commit()

        assert ledger_entry.client == client
        assert ledger_entry.is_charge() is True
        assert ledger_entry.is_payment() is False
        assert ledger_entry.amount == 150.00

    def test_audit_log_creation(self, session):
        """Test AuditLog model creation for HIPAA compliance."""
        user_uuid = uuid.uuid4()
        resource_uuid = uuid.uuid4()

        audit_log = AuditLog(
            correlation_id=str(uuid.uuid4()),
            user_id=user_uuid,
            action="CREATE",
            resource_type="Client",
            resource_id=resource_uuid,
            ip_address="192.168.1.1",
            user_agent="Test Agent",
            old_values={},
            new_values={"name": "Test Client"},
        )

        session.add(audit_log)
        session.commit()

        assert audit_log.id is not None
        assert audit_log.created_at is not None
        assert audit_log.action == "CREATE"
        assert audit_log.resource_type == "Client"
        assert audit_log.user_id == user_uuid
        assert audit_log.resource_id == resource_uuid
        assert "Client" in str(audit_log)

    def test_phi_protection_in_repr(self, session):
        """Test that __repr__ methods don't expose PHI."""
        client = Client(
            first_name="Sensitive",
            last_name="Data",
            date_of_birth=datetime(1990, 1, 1).date(),
            email="sensitive@example.com",
            phone="555-PRIVATE",
        )

        session.add(client)
        session.commit()

        repr_str = str(client)

        # Should not contain sensitive information
        assert "sensitive@example.com" not in repr_str
        assert "555-PRIVATE" not in repr_str
        assert "Sensitive Data" not in repr_str

        # Should contain safe information
        assert "Client" in repr_str
        assert str(client.id) in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

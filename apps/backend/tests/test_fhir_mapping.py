"""Tests for FHIR mapping functionality."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from models.fhir_mapping import FHIRMapping, FHIRMappingStatus, FHIRResourceType
from services.fhir_mapping_service import FHIRMappingService


class TestFHIRMappingModel:
    """Test FHIR mapping model functionality."""

    def test_create_fhir_mapping(self, test_session):
        """Test creating a FHIR mapping."""
        internal_id = uuid4()
        mapping = FHIRMapping(
            internal_id=internal_id,
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id="patient-123",
            fhir_server_url="https://fhir.example.com",
            tenant_id="tenant-1",
            status=FHIRMappingStatus.ACTIVE,
            is_active=True,
            error_count="0",
        )

        test_session.add(mapping)
        test_session.commit()

        assert mapping.id is not None
        assert mapping.internal_id == internal_id
        assert mapping.fhir_resource_type == FHIRResourceType.PATIENT
        assert mapping.fhir_resource_id == "patient-123"
        assert mapping.status == FHIRMappingStatus.ACTIVE
        assert mapping.is_active is True
        assert mapping.error_count == "0"

    def test_fhir_mapping_unique_constraints(self, test_session):
        """Test unique constraints on FHIR mappings."""
        internal_id = uuid4()

        # Create first mapping
        mapping1 = FHIRMapping(
            internal_id=internal_id,
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id="patient-123",
            tenant_id="tenant-1",
            status=FHIRMappingStatus.ACTIVE,
            is_active=True,
            error_count="0",
        )
        test_session.add(mapping1)
        test_session.commit()

        # Try to create duplicate mapping (same internal_id + resource_type +
        # tenant)
        mapping2 = FHIRMapping(
            internal_id=internal_id,
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id="patient-456",
            tenant_id="tenant-1",
            status=FHIRMappingStatus.ACTIVE,
            is_active=True,
            error_count="0",
        )
        test_session.add(mapping2)

        with pytest.raises(IntegrityError):
            test_session.commit()

    def test_fhir_mapping_is_sync_needed(self, test_session):
        """Test sync needed detection."""
        mapping = FHIRMapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id="patient-123",
            status=FHIRMappingStatus.ACTIVE,
            is_active=True,
            error_count="0",
        )

        # No last sync - should need sync
        assert mapping.is_sync_needed() is True

        # Recent sync - should not need sync
        mapping.last_sync_at = datetime.utcnow()
        assert mapping.is_sync_needed() is False

        # Old sync - should need sync
        mapping.last_sync_at = datetime.utcnow() - timedelta(hours=2)
        assert mapping.is_sync_needed() is True

    def test_fhir_mapping_error_handling(self, test_session):
        """Test error count and status handling."""
        mapping = FHIRMapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id="patient-123",
            status=FHIRMappingStatus.ACTIVE,
            is_active=True,
            error_count="0",
        )

        # Initially no errors
        assert mapping.has_errors() is False

        # Increment error count
        mapping.increment_error_count("Test error")
        assert mapping.has_errors() is True
        assert mapping.error_count == "1"
        assert mapping.last_error == "Test error"
        assert mapping.last_error_at is not None

        # Multiple errors should change status
        for i in range(5):
            mapping.increment_error_count(f"Error {i}")

        assert mapping.status == FHIRMappingStatus.ERROR

        # Reset errors
        mapping.reset_error_count()
        assert mapping.has_errors() is False
        assert mapping.error_count == "0"
        assert mapping.last_error is None
        assert mapping.status == FHIRMappingStatus.ACTIVE

    def test_fhir_mapping_mark_synced(self, test_session):
        """Test marking mapping as synced."""
        mapping = FHIRMapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id="patient-123",
            status=FHIRMappingStatus.ACTIVE,
            is_active=True,
            error_count="1",  # Has error initially
        )

        mapping.mark_synced("v1.0")

        assert mapping.last_sync_at is not None
        assert mapping.version == "v1.0"
        assert mapping.error_count == "0"

    def test_fhir_mapping_deactivate(self, test_session):
        """Test deactivating a mapping."""
        mapping = FHIRMapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id="patient-123",
            status=FHIRMappingStatus.ACTIVE,
            is_active=True,
            error_count="0",
        )

        mapping.deactivate("No longer needed")

        assert mapping.is_active is False
        assert mapping.status == FHIRMappingStatus.INACTIVE
        assert "Deactivated: No longer needed" in mapping.notes

    def test_fhir_mapping_to_dict(self, test_session):
        """Test converting mapping to dictionary."""
        internal_id = uuid4()
        mapping = FHIRMapping(
            internal_id=internal_id,
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id="patient-to-dict-123",
            fhir_server_url="https://fhir.example.com",
            tenant_id="tenant-1",
            status=FHIRMappingStatus.ACTIVE,
            is_active=True,
            error_count="0",
        )

        test_session.add(mapping)
        test_session.commit()

        result = mapping.to_dict()

        assert result["internal_id"] == str(internal_id)
        assert result["fhir_resource_type"] == "Patient"
        assert result["fhir_resource_id"] == "patient-to-dict-123"
        assert result["fhir_server_url"] == "https://fhir.example.com"
        assert result["status"] == "active"
        assert result["is_active"] is True
        assert result["tenant_id"] == "tenant-1"


class TestFHIRMappingService:
    """Test FHIR mapping service functionality."""

    def test_create_mapping(self, test_session):
        """Test creating a mapping through service."""
        service = FHIRMappingService(test_session)
        internal_id = uuid4()
        unique_resource_id = f"patient-create-{uuid4()}"
        unique_tenant = f"tenant-create-{uuid4()}"

        mapping = service.create_mapping(
            internal_id=internal_id,
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=unique_resource_id,
            tenant_id=unique_tenant,
            fhir_server_url="https://fhir.example.com",
            created_by="test-user",
        )

        assert mapping.internal_id == internal_id
        assert mapping.fhir_resource_type == FHIRResourceType.PATIENT
        assert mapping.fhir_resource_id == unique_resource_id
        assert mapping.tenant_id == unique_tenant
        assert mapping.created_by == "test-user"
        assert mapping.status == FHIRMappingStatus.ACTIVE

    def test_create_duplicate_mapping_raises_error(self, test_session):
        """Test that creating duplicate mapping raises error."""
        service = FHIRMappingService(test_session)
        internal_id = uuid4()
        unique_tenant = f"tenant-duplicate-{uuid4()}"

        # Create first mapping
        service.create_mapping(
            internal_id=internal_id,
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=f"patient-dup-1-{uuid4()}",
            tenant_id=unique_tenant,
        )

        # Try to create duplicate
        with pytest.raises(ValueError, match="Mapping already exists"):
            service.create_mapping(
                internal_id=internal_id,
                fhir_resource_type=FHIRResourceType.PATIENT,
                fhir_resource_id=f"patient-dup-2-{uuid4()}",
                tenant_id=unique_tenant,
            )

    def test_get_mapping_by_internal_id(self, test_session):
        """Test getting mapping by internal ID."""
        service = FHIRMappingService(test_session)
        internal_id = uuid4()
        unique_tenant = f"tenant-internal-{uuid4()}"

        # Create mapping
        created_mapping = service.create_mapping(
            internal_id=internal_id,
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=f"patient-internal-{uuid4()}",
            tenant_id=unique_tenant,
        )

        # Retrieve mapping
        retrieved_mapping = service.get_mapping_by_internal_id(
            internal_id=internal_id,
            fhir_resource_type=FHIRResourceType.PATIENT,
            tenant_id=unique_tenant,
        )

        assert retrieved_mapping is not None
        assert retrieved_mapping.id == created_mapping.id
        assert retrieved_mapping.internal_id == internal_id

    def test_get_mapping_by_fhir_id(self, test_session):
        """Test getting mapping by FHIR ID."""
        service = FHIRMappingService(test_session)
        internal_id = uuid4()
        unique_resource_id = f"patient-fhir-{uuid4()}"
        unique_tenant = f"tenant-fhir-{uuid4()}"

        # Create mapping
        created_mapping = service.create_mapping(
            internal_id=internal_id,
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=unique_resource_id,
            tenant_id=unique_tenant,
            fhir_server_url="https://fhir.example.com",
        )

        # Retrieve mapping
        retrieved_mapping = service.get_mapping_by_fhir_id(
            fhir_resource_id=unique_resource_id,
            fhir_resource_type=FHIRResourceType.PATIENT,
            tenant_id=unique_tenant,
            fhir_server_url="https://fhir.example.com",
        )

        assert retrieved_mapping is not None
        assert retrieved_mapping.id == created_mapping.id
        assert retrieved_mapping.fhir_resource_id == unique_resource_id

    def test_get_mappings_by_resource_type(self, test_session):
        """Test getting mappings by resource type."""
        service = FHIRMappingService(test_session)
        unique_tenant = f"tenant-resource-{uuid4()}"

        # Create multiple mappings
        for i in range(3):
            service.create_mapping(
                internal_id=uuid4(),
                fhir_resource_type=FHIRResourceType.PATIENT,
                fhir_resource_id=f"patient-resource-{i}-{uuid4()}",
                tenant_id=unique_tenant,
            )

        # Create mapping of different type
        service.create_mapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PRACTITIONER,
            fhir_resource_id=f"practitioner-resource-{uuid4()}",
            tenant_id=unique_tenant,
        )

        # Get patient mappings
        patient_mappings = service.get_mappings_by_resource_type(
            fhir_resource_type=FHIRResourceType.PATIENT,
            tenant_id=unique_tenant,
        )

        assert len(patient_mappings) == 3
        for mapping in patient_mappings:
            assert mapping.fhir_resource_type == FHIRResourceType.PATIENT

    def test_get_mappings_needing_sync(self, test_session):
        """Test getting mappings that need synchronization."""
        service = FHIRMappingService(test_session)
        unique_tenant = f"tenant-sync-{uuid4()}"

        # Create mapping that needs sync (no last_sync_at)
        sync_mapping1 = service.create_mapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=f"patient-sync-1-{uuid4()}",
            tenant_id=unique_tenant,
        )

        # Create mapping with old sync
        sync_mapping2 = service.create_mapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=f"patient-sync-2-{uuid4()}",
            tenant_id=unique_tenant,
        )
        sync_mapping2.last_sync_at = datetime.utcnow() - timedelta(hours=2)
        test_session.commit()

        # Create mapping with recent sync
        sync_mapping3 = service.create_mapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=f"patient-sync-3-{uuid4()}",
            tenant_id=unique_tenant,
        )
        sync_mapping3.last_sync_at = datetime.utcnow()
        test_session.commit()

        # Get mappings needing sync
        needing_sync = service.get_mappings_needing_sync(
            threshold_minutes=60,
            tenant_id=unique_tenant,
        )

        assert len(needing_sync) == 2
        sync_ids = {m.id for m in needing_sync}
        assert sync_mapping1.id in sync_ids
        assert sync_mapping2.id in sync_ids
        assert sync_mapping3.id not in sync_ids

    def test_get_mappings_with_errors(self, test_session):
        """Test getting mappings with errors."""
        service = FHIRMappingService(test_session)
        unique_tenant = f"tenant-errors-{uuid4()}"

        # Create mapping without errors
        mapping1 = service.create_mapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=f"patient-error-1-{uuid4()}",
            tenant_id=unique_tenant,
        )

        # Create mapping with errors
        mapping2 = service.create_mapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=f"patient-error-2-{uuid4()}",
            tenant_id=unique_tenant,
        )
        mapping2.increment_error_count("Test error")
        test_session.commit()

        # Get mappings with errors
        with_errors = service.get_mappings_with_errors(tenant_id=unique_tenant)

        assert len(with_errors) == 1
        assert with_errors[0].id == mapping2.id

    def test_update_mapping(self, test_session):
        """Test updating a mapping."""
        service = FHIRMappingService(test_session)
        unique_tenant = f"tenant-update-{uuid4()}"

        # Create mapping
        mapping = service.create_mapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=f"patient-update-1-{uuid4()}",
            tenant_id=unique_tenant,
        )

        # Update mapping
        new_resource_id = f"patient-update-2-{uuid4()}"
        updated_mapping = service.update_mapping(
            mapping_id=mapping.id,
            fhir_resource_id=new_resource_id,
            status=FHIRMappingStatus.PENDING,
            version="v2.0",
            updated_by="test-user",
        )

        assert updated_mapping is not None
        assert updated_mapping.fhir_resource_id == new_resource_id
        assert updated_mapping.status == FHIRMappingStatus.PENDING
        assert updated_mapping.version == "v2.0"
        assert updated_mapping.updated_by == "test-user"

    def test_mark_mapping_synced(self, test_session):
        """Test marking mapping as synced."""
        service = FHIRMappingService(test_session)
        unique_tenant = f"tenant-synced-{uuid4()}"

        # Create mapping with error
        mapping = service.create_mapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=f"patient-synced-{uuid4()}",
            tenant_id=unique_tenant,
        )
        mapping.increment_error_count("Test error")
        test_session.commit()

        # Mark as synced
        synced_mapping = service.mark_mapping_synced(
            mapping_id=mapping.id,
            version="v1.0",
            updated_by="sync-service",
        )

        assert synced_mapping is not None
        assert synced_mapping.last_sync_at is not None
        assert synced_mapping.version == "v1.0"
        assert synced_mapping.error_count == "0"
        assert synced_mapping.updated_by == "sync-service"

    def test_record_mapping_error(self, test_session):
        """Test recording an error for a mapping."""
        service = FHIRMappingService(test_session)
        unique_tenant = f"tenant-record-{uuid4()}"

        # Create mapping
        mapping = service.create_mapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=f"patient-record-{uuid4()}",
            tenant_id=unique_tenant,
        )

        # Record error
        error_mapping = service.record_mapping_error(
            mapping_id=mapping.id,
            error_message="Sync failed",
            updated_by="sync-service",
        )

        assert error_mapping is not None
        assert error_mapping.error_count == "1"
        assert error_mapping.last_error == "Sync failed"
        assert error_mapping.last_error_at is not None
        assert error_mapping.updated_by == "sync-service"

    def test_deactivate_mapping(self, test_session):
        """Test deactivating a mapping."""
        service = FHIRMappingService(test_session)
        tenant_id = f"tenant-deact-{uuid4()}"

        # Create mapping
        mapping = service.create_mapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=f"patient-deactivate-{uuid4()}",
            tenant_id=tenant_id,
        )

        # Deactivate mapping
        deactivated_mapping = service.deactivate_mapping(
            mapping_id=mapping.id,
            reason="Patient record deleted",
            updated_by="admin-user",
        )

        assert deactivated_mapping is not None
        assert deactivated_mapping.is_active is False
        assert deactivated_mapping.status == FHIRMappingStatus.INACTIVE
        assert "Deactivated: Patient record deleted" in deactivated_mapping.notes
        assert deactivated_mapping.updated_by == "admin-user"

    def test_get_mapping_stats(self, test_session):
        """Test getting mapping statistics."""
        service = FHIRMappingService(test_session)

        # Create various mappings with unique IDs
        unique_tenant = f"tenant-stats-{uuid4()}"

        # Active mapping
        service.create_mapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=f"patient-stats-1-{uuid4()}",
            tenant_id=unique_tenant,
        )

        # Mapping with error
        error_mapping = service.create_mapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=f"patient-stats-2-{uuid4()}",
            tenant_id=unique_tenant,
        )
        error_mapping.increment_error_count("Test error")
        test_session.commit()

        # Mapping needing sync
        sync_mapping = service.create_mapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=f"patient-stats-3-{uuid4()}",
            tenant_id=unique_tenant,
        )
        sync_mapping.last_sync_at = datetime.utcnow() - timedelta(hours=2)
        test_session.commit()

        # Get stats
        stats = service.get_mapping_stats(tenant_id=unique_tenant)

        assert stats["total"] == 3
        assert stats["active"] == 3
        assert stats["with_errors"] == 1
        # All mappings need sync (no last_sync_at set for first mapping)
        assert stats["needing_sync"] == 3

    def test_bulk_create_mappings(self, test_session):
        """Test bulk creating mappings."""
        service = FHIRMappingService(test_session)
        unique_tenant = f"tenant-bulk-{uuid4()}"

        mappings_data = [
            {
                "internal_id": uuid4(),
                "fhir_resource_type": FHIRResourceType.PATIENT,
                "fhir_resource_id": f"patient-bulk-1-{uuid4()}",
            },
            {
                "internal_id": uuid4(),
                "fhir_resource_type": FHIRResourceType.PATIENT,
                "fhir_resource_id": f"patient-bulk-2-{uuid4()}",
            },
            {
                "internal_id": uuid4(),
                "fhir_resource_type": FHIRResourceType.PRACTITIONER,
                "fhir_resource_id": f"practitioner-bulk-{uuid4()}",
            },
        ]

        created_mappings, error_messages = service.bulk_create_mappings(
            mappings_data=mappings_data,
            tenant_id=unique_tenant,
            created_by="bulk-import",
        )

        assert len(created_mappings) == 3
        assert len(error_messages) == 0

        for mapping in created_mappings:
            assert mapping.tenant_id == unique_tenant
            assert mapping.created_by == "bulk-import"
            assert mapping.status == FHIRMappingStatus.ACTIVE


class TestFHIRResourceTypes:
    """Test all supported FHIR resource types."""

    @pytest.mark.parametrize(
        "resource_type",
        [
            FHIRResourceType.PATIENT,
            FHIRResourceType.PRACTITIONER,
            FHIRResourceType.ENCOUNTER,
            FHIRResourceType.OBSERVATION,
            FHIRResourceType.APPOINTMENT,
            FHIRResourceType.ORGANIZATION,
            FHIRResourceType.LOCATION,
            FHIRResourceType.MEDICATION,
            FHIRResourceType.MEDICATION_REQUEST,
            FHIRResourceType.DIAGNOSTIC_REPORT,
            FHIRResourceType.CONDITION,
            FHIRResourceType.PROCEDURE,
            FHIRResourceType.CARE_PLAN,
            FHIRResourceType.DOCUMENT_REFERENCE,
            FHIRResourceType.COVERAGE,
            FHIRResourceType.CLAIM,
            FHIRResourceType.EXPLANATION_OF_BENEFIT,
        ],
    )
    def test_create_mapping_for_resource_type(self, test_session, resource_type):
        """Test creating mappings for all supported resource types."""
        service = FHIRMappingService(test_session)
        internal_id = uuid4()
        unique_tenant = f"tenant-type-{uuid4()}"
        unique_resource_id = f"{resource_type.value.lower()}-type-{uuid4()}"

        mapping = service.create_mapping(
            internal_id=internal_id,
            fhir_resource_type=resource_type,
            fhir_resource_id=unique_resource_id,
            tenant_id=unique_tenant,
        )

        assert mapping.internal_id == internal_id
        assert mapping.fhir_resource_type == resource_type
        assert mapping.fhir_resource_id == unique_resource_id
        assert mapping.status == FHIRMappingStatus.ACTIVE

    def test_resource_type_values(self):
        """Test that resource type values match FHIR specification."""
        assert FHIRResourceType.PATIENT.value == "Patient"
        assert FHIRResourceType.PRACTITIONER.value == "Practitioner"
        assert FHIRResourceType.ENCOUNTER.value == "Encounter"
        assert FHIRResourceType.OBSERVATION.value == "Observation"
        assert FHIRResourceType.APPOINTMENT.value == "Appointment"
        assert FHIRResourceType.ORGANIZATION.value == "Organization"
        assert FHIRResourceType.LOCATION.value == "Location"
        assert FHIRResourceType.MEDICATION.value == "Medication"
        assert FHIRResourceType.MEDICATION_REQUEST.value == "MedicationRequest"
        assert FHIRResourceType.DIAGNOSTIC_REPORT.value == "DiagnosticReport"
        assert FHIRResourceType.CONDITION.value == "Condition"
        assert FHIRResourceType.PROCEDURE.value == "Procedure"
        assert FHIRResourceType.CARE_PLAN.value == "CarePlan"
        assert FHIRResourceType.DOCUMENT_REFERENCE.value == "DocumentReference"
        assert FHIRResourceType.COVERAGE.value == "Coverage"
        assert FHIRResourceType.CLAIM.value == "Claim"
        assert FHIRResourceType.EXPLANATION_OF_BENEFIT.value == "ExplanationOfBenefit"


class TestFHIRMappingAuditLogging:
    """Test audit logging capabilities for FHIR mappings."""

    def test_mapping_tracks_creation_info(self, test_session):
        """Test that mappings track creation information."""
        service = FHIRMappingService(test_session)
        unique_tenant = f"tenant-creation-{uuid4()}"

        mapping = service.create_mapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=f"patient-creation-{uuid4()}",
            tenant_id=unique_tenant,
            correlation_id="req-123",
            created_by="test-user",
            notes="Initial mapping creation",
        )

        assert mapping.tenant_id == unique_tenant
        assert mapping.correlation_id == "req-123"
        assert mapping.created_by == "test-user"
        assert mapping.notes == "Initial mapping creation"
        assert mapping.created_at is not None
        assert mapping.updated_at is not None

    def test_mapping_tracks_update_info(self, test_session):
        """Test that mappings track update information."""
        service = FHIRMappingService(test_session)
        unique_tenant = f"tenant-update-info-{uuid4()}"

        # Create mapping
        mapping = service.create_mapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=f"patient-update-info-1-{uuid4()}",
            tenant_id=unique_tenant,
            created_by="test-user",
        )

        original_updated_at = mapping.updated_at

        # Update mapping
        updated_mapping = service.update_mapping(
            mapping_id=mapping.id,
            fhir_resource_id=f"patient-update-info-2-{uuid4()}",
            updated_by="admin-user",
            notes="Updated FHIR ID",
        )

        assert updated_mapping.updated_by == "admin-user"
        assert updated_mapping.notes == "Updated FHIR ID"
        assert updated_mapping.updated_at > original_updated_at

    def test_mapping_tracks_error_history(self, test_session):
        """Test that mappings track error history."""
        service = FHIRMappingService(test_session)
        unique_tenant = f"tenant-error-history-{uuid4()}"

        # Create mapping
        mapping = service.create_mapping(
            internal_id=uuid4(),
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=f"patient-error-history-{uuid4()}",
            tenant_id=unique_tenant,
        )

        # Record multiple errors
        service.record_mapping_error(
            mapping_id=mapping.id,
            error_message="First error",
            updated_by="sync-service",
        )

        service.record_mapping_error(
            mapping_id=mapping.id,
            error_message="Second error",
            updated_by="sync-service",
        )

        # Refresh mapping
        test_session.refresh(mapping)

        assert mapping.error_count == "2"
        assert mapping.last_error == "Second error"
        assert mapping.last_error_at is not None
        assert mapping.updated_by == "sync-service"

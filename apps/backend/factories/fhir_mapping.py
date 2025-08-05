"""FHIR mapping factory for HIPAA-compliant test data generation."""

from datetime import timezone
from uuid import uuid4

import factory
from faker import Faker

from models.fhir_mapping import FHIRMapping, FHIRMappingStatus, FHIRResourceType

from .base import BaseFactory

fake = Faker()


class FHIRMappingFactory(BaseFactory):
    """Factory for generating HIPAA-compliant FHIR mapping data."""

    class Meta:
        model = FHIRMapping

    # Internal system resource ID (will be linked to actual resources)
    internal_id = factory.LazyFunction(lambda: uuid4())

    # FHIR resource information
    fhir_resource_type = factory.LazyFunction(
        lambda: fake.random_element(
            [
                FHIRResourceType.PATIENT,
                FHIRResourceType.PRACTITIONER,
                FHIRResourceType.APPOINTMENT,
                FHIRResourceType.ENCOUNTER,
                FHIRResourceType.OBSERVATION,
                FHIRResourceType.ORGANIZATION,
                FHIRResourceType.LOCATION,
            ]
        )
    )

    fhir_resource_id = factory.LazyFunction(
        lambda: f"fhir-{fake.random_int(min=100000, max=999999)}"
    )

    fhir_server_url = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "https://fhir.test.local/R4",
                "https://staging-fhir.example.com/R4",
                "https://dev-fhir.example.com/R4",
            ]
        )
    )

    # Mapping metadata
    status = factory.LazyFunction(
        lambda: fake.random_element(
            [
                FHIRMappingStatus.ACTIVE,
                FHIRMappingStatus.PENDING,
                FHIRMappingStatus.INACTIVE,
            ]
        )
    )

    version = factory.LazyFunction(lambda: f"v{fake.random_int(min=1, max=10)}")

    last_sync_at = factory.LazyFunction(
        lambda: fake.date_time_between(
            start_date="-30d", end_date="now", tzinfo=timezone.utc
        )
    )

    last_error = factory.LazyFunction(
        lambda: fake.random_element(
            [
                None,
                "Connection timeout",
                "Resource not found",
                "Authentication failed",
                "Invalid resource format",
            ]
        )
    )

    last_error_at = factory.LazyAttribute(
        lambda obj: (
            fake.date_time_between(
                start_date="-7d", end_date="now", tzinfo=timezone.utc
            )
            if obj.last_error
            else None
        )
    )

    error_count = factory.LazyFunction(lambda: str(fake.random_int(min=0, max=5)))

    is_active = factory.LazyFunction(lambda: fake.boolean(chance_of_getting_true=85))

    notes = factory.LazyFunction(
        lambda: fake.random_element(
            [
                None,
                "Initial mapping created",
                "Migrated from legacy system",
                "Updated after resource modification",
                "Requires manual review",
            ]
        )
    )


class ActiveFHIRMappingFactory(FHIRMappingFactory):
    """Factory for active FHIR mappings."""

    status = FHIRMappingStatus.ACTIVE
    is_active = True
    last_error = None
    last_error_at = None
    error_count = "0"


class ErrorFHIRMappingFactory(FHIRMappingFactory):
    """Factory for FHIR mappings with errors."""

    status = FHIRMappingStatus.ERROR
    last_error = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "HTTP 404: Resource not found",
                "HTTP 401: Unauthorized access",
                "HTTP 500: Internal server error",
                "Connection timeout after 30s",
                "Invalid FHIR resource format",
            ]
        )
    )
    last_error_at = factory.LazyFunction(
        lambda: fake.date_time_between(
            start_date="-1d", end_date="now", tzinfo=timezone.utc
        )
    )
    error_count = factory.LazyFunction(lambda: str(fake.random_int(min=1, max=10)))


class PatientMappingFactory(FHIRMappingFactory):
    """Factory specifically for Patient FHIR mappings."""

    fhir_resource_type = FHIRResourceType.PATIENT
    fhir_resource_id = factory.LazyFunction(
        lambda: f"Patient/{fake.random_int(min=100000, max=999999)}"
    )


class PractitionerMappingFactory(FHIRMappingFactory):
    """Factory specifically for Practitioner FHIR mappings."""

    fhir_resource_type = FHIRResourceType.PRACTITIONER
    fhir_resource_id = factory.LazyFunction(
        lambda: f"Practitioner/{fake.random_int(min=100000, max=999999)}"
    )


class AppointmentMappingFactory(FHIRMappingFactory):
    """Factory specifically for Appointment FHIR mappings."""

    fhir_resource_type = FHIRResourceType.APPOINTMENT
    fhir_resource_id = factory.LazyFunction(
        lambda: f"Appointment/{fake.random_int(min=100000, max=999999)}"
    )

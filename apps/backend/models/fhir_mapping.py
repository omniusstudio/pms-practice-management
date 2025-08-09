"""FHIR mapping model for internal-to-FHIR resource mappings."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Index, String, Text, UniqueConstraint

from .base import BaseModel
from .types import UUID


class FHIRResourceType(str, Enum):
    """FHIR resource type enumeration."""

    PATIENT = "Patient"
    PRACTITIONER = "Practitioner"
    ENCOUNTER = "Encounter"
    OBSERVATION = "Observation"
    APPOINTMENT = "Appointment"
    ORGANIZATION = "Organization"
    LOCATION = "Location"
    MEDICATION = "Medication"
    MEDICATION_REQUEST = "MedicationRequest"
    DIAGNOSTIC_REPORT = "DiagnosticReport"
    CONDITION = "Condition"
    PROCEDURE = "Procedure"
    CARE_PLAN = "CarePlan"
    DOCUMENT_REFERENCE = "DocumentReference"
    COVERAGE = "Coverage"
    CLAIM = "Claim"
    EXPLANATION_OF_BENEFIT = "ExplanationOfBenefit"


class FHIRMappingStatus(str, Enum):
    """FHIR mapping status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ERROR = "error"
    DEPRECATED = "deprecated"


class FHIRMapping(BaseModel):
    """FHIR mapping model for internal-to-FHIR resource mappings.

    This table maintains one-to-one mappings between internal system IDs
    and FHIR resource IDs to ensure data portability and synchronization.
    """

    __tablename__ = "fhir_mappings"

    # Internal system resource ID (UUID)
    internal_id: Column[UUID] = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Internal system resource ID",
    )

    # FHIR resource information
    fhir_resource_type: Column[FHIRResourceType] = Column(
        SQLEnum(FHIRResourceType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
        comment="FHIR resource type (Patient, Practitioner, etc.)",
    )

    fhir_resource_id = Column(
        String(255),
        nullable=False,
        index=True,
        comment="FHIR resource ID from external FHIR server",
    )

    fhir_server_url = Column(
        String(500),
        nullable=True,
        comment="Base URL of FHIR server where resource is stored",
    )

    # Mapping metadata
    status: Column[FHIRMappingStatus] = Column(
        SQLEnum(FHIRMappingStatus, values_callable=lambda x: [e.value for e in x]),
        default=FHIRMappingStatus.ACTIVE,
        nullable=False,
        index=True,
        comment="Current status of the mapping",
    )

    version = Column(
        String(50),
        nullable=True,
        comment="FHIR resource version/etag for optimistic locking",
    )

    last_sync_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last successful synchronization",
    )

    # Error tracking
    last_error = Column(
        Text, nullable=True, comment="Last error message if sync failed"
    )

    last_error_at = Column(
        DateTime(timezone=True), nullable=True, comment="Timestamp of last error"
    )

    error_count = Column(
        String(10),  # Using string to avoid overflow issues
        default="0",
        nullable=False,
        comment="Number of consecutive errors",
    )

    # Audit and compliance fields
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether this mapping is currently active",
    )

    created_by = Column(
        String(255), nullable=True, comment="User or system that created this mapping"
    )

    updated_by = Column(
        String(255),
        nullable=True,
        comment="User or system that last updated this mapping",
    )

    notes = Column(Text, nullable=True, comment="Additional notes about this mapping")

    # Table constraints and indexes
    __table_args__ = (
        # Unique constraints for data integrity
        UniqueConstraint(
            "internal_id",
            "fhir_resource_type",
            "tenant_id",
            name="uq_fhir_mapping_internal_resource_tenant",
        ),
        UniqueConstraint(
            "fhir_resource_id",
            "fhir_resource_type",
            "fhir_server_url",
            "tenant_id",
            name="uq_fhir_mapping_fhir_resource_tenant",
        ),
        # Performance indexes
        Index("idx_fhir_mapping_internal_id", "internal_id"),
        Index("idx_fhir_mapping_fhir_id", "fhir_resource_id"),
        Index("idx_fhir_mapping_resource_type", "fhir_resource_type"),
        Index("idx_fhir_mapping_status", "status"),
        Index("idx_fhir_mapping_active", "is_active"),
        Index("idx_fhir_mapping_tenant", "tenant_id"),
        Index("idx_fhir_mapping_last_sync", "last_sync_at"),
        Index("idx_fhir_mapping_error_count", "error_count"),
        # Composite indexes for common queries
        Index(
            "idx_fhir_mapping_lookup", "internal_id", "fhir_resource_type", "tenant_id"
        ),
        Index(
            "idx_fhir_mapping_reverse_lookup",
            "fhir_resource_id",
            "fhir_resource_type",
            "tenant_id",
        ),
        Index("idx_fhir_mapping_sync_status", "status", "last_sync_at", "tenant_id"),
        Index(
            "idx_fhir_mapping_error_tracking", "status", "error_count", "last_error_at"
        ),
        Index(
            "idx_fhir_mappings_server_resource_type",
            "fhir_server_url",
            "fhir_resource_type",
            postgresql_where="(fhir_server_url IS NOT NULL)",
        ),
        Index(
            "idx_fhir_mappings_error_status_count",
            "error_count",
            "status",
            postgresql_where="((error_count)::integer > 0)",
        ),
    )

    def is_sync_needed(self, threshold_minutes: int = 60) -> bool:
        """Check if synchronization is needed based on last sync time.

        Args:
            threshold_minutes: Minutes since last sync to consider sync needed

        Returns:
            True if sync is needed, False otherwise
        """
        if not self.last_sync_at:
            return True

        from datetime import timedelta

        threshold = datetime.utcnow() - timedelta(minutes=threshold_minutes)
        return self.last_sync_at < threshold

    def has_errors(self) -> bool:
        """Check if this mapping has any errors.

        Returns:
            True if there are errors, False otherwise
        """
        try:
            return int(self.error_count) > 0
        except (ValueError, TypeError):
            return False

    def increment_error_count(self, error_message: str) -> None:
        """Increment error count and update error information.

        Args:
            error_message: Error message to record
        """
        try:
            current_count = int(self.error_count)
        except (ValueError, TypeError):
            current_count = 0

        self.error_count = str(current_count + 1)
        self.last_error = error_message
        self.last_error_at = datetime.utcnow()

        # Mark as error status if too many consecutive errors
        if current_count >= 5:
            self.status = FHIRMappingStatus.ERROR

    def reset_error_count(self) -> None:
        """Reset error count after successful operation."""
        self.error_count = "0"
        self.last_error = None
        self.last_error_at = None

        # Reset status to active if it was in error state
        if self.status == FHIRMappingStatus.ERROR:
            self.status = FHIRMappingStatus.ACTIVE

    def mark_synced(self, version: Optional[str] = None) -> None:
        """Mark mapping as successfully synced.

        Args:
            version: FHIR resource version/etag if available
        """
        self.last_sync_at = datetime.utcnow()
        if version:
            self.version = version
        self.reset_error_count()

    def deactivate(self, reason: Optional[str] = None) -> None:
        """Deactivate this mapping.

        Args:
            reason: Reason for deactivation
        """
        self.is_active = False
        self.status = FHIRMappingStatus.INACTIVE
        if reason:
            current_notes = self.notes or ""
            deactivation_note = f"\nDeactivated: {reason}"
            self.notes = f"{current_notes}{deactivation_note}".strip()

    def to_dict(self) -> dict:
        """Convert mapping to dictionary for API responses.

        Returns:
            Dictionary representation of the mapping
        """
        return {
            "id": str(self.id),
            "internal_id": str(self.internal_id),
            "fhir_resource_type": self.fhir_resource_type.value,
            "fhir_resource_id": self.fhir_resource_id,
            "fhir_server_url": self.fhir_server_url,
            "status": self.status.value,
            "version": self.version,
            "last_sync_at": (
                self.last_sync_at.isoformat() if self.last_sync_at else None
            ),
            "error_count": self.error_count,
            "is_active": self.is_active,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        """String representation of the mapping."""
        return (
            f"<FHIRMapping("
            f"internal_id={self.internal_id}, "
            f"fhir_resource_type={self.fhir_resource_type.value}, "
            f"fhir_resource_id={self.fhir_resource_id}, "
            f"status={self.status.value}"
            f")>"
        )

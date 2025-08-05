"""Add FHIR mapping table

Revision ID: add_fhir_mapping
Revises: add_key_rotation_policies
Create Date: 2025-01-05 10:00:00.000000

"""
import sqlalchemy as sa  # type: ignore
from sqlalchemy.dialects import postgresql

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision = "add_fhir_mapping"
down_revision = "add_encryption_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create FHIR resource type enum
    fhir_resource_type_enum = postgresql.ENUM(
        "Patient",
        "Practitioner",
        "Encounter",
        "Observation",
        "Appointment",
        "Organization",
        "Location",
        "Medication",
        "MedicationRequest",
        "DiagnosticReport",
        "Condition",
        "Procedure",
        "CarePlan",
        "DocumentReference",
        "Coverage",
        "Claim",
        "ExplanationOfBenefit",
        name="fhirresourcetype",
        create_type=False,
    )
    fhir_resource_type_enum.create(op.get_bind(), checkfirst=True)

    # Create FHIR mapping status enum
    fhir_mapping_status_enum = postgresql.ENUM(
        "active",
        "inactive",
        "pending",
        "error",
        "deprecated",
        name="fhirmappingstatus",
        create_type=False,
    )
    fhir_mapping_status_enum.create(op.get_bind(), checkfirst=True)

    # Create fhir_mappings table
    op.create_table(
        "fhir_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("tenant_id", sa.String(length=255), nullable=True),
        sa.Column(
            "internal_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Internal system resource ID",
        ),
        sa.Column(
            "fhir_resource_type",
            fhir_resource_type_enum,
            nullable=False,
            comment="FHIR resource type (Patient, Practitioner, etc.)",
        ),
        sa.Column(
            "fhir_resource_id",
            sa.String(length=255),
            nullable=False,
            comment="FHIR resource ID from external FHIR server",
        ),
        sa.Column(
            "fhir_server_url",
            sa.String(length=500),
            nullable=True,
            comment="Base URL of the FHIR server where resource is stored",
        ),
        sa.Column(
            "status",
            fhir_mapping_status_enum,
            nullable=False,
            comment="Current status of the mapping",
        ),
        sa.Column(
            "version",
            sa.String(length=50),
            nullable=True,
            comment="FHIR resource version/etag for optimistic locking",
        ),
        sa.Column(
            "last_sync_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of last successful synchronization",
        ),
        sa.Column(
            "last_error",
            sa.Text(),
            nullable=True,
            comment="Last error message if sync failed",
        ),
        sa.Column(
            "last_error_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of last error",
        ),
        sa.Column(
            "error_count",
            sa.String(length=10),
            nullable=False,
            comment="Number of consecutive errors",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            comment="Whether this mapping is currently active",
        ),
        sa.Column(
            "created_by",
            sa.String(length=255),
            nullable=True,
            comment="User or system that created this mapping",
        ),
        sa.Column(
            "updated_by",
            sa.String(length=255),
            nullable=True,
            comment="User or system that last updated this mapping",
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
            comment="Additional notes about this mapping",
        ),
        sa.PrimaryKeyConstraint("id"),
        # Unique constraints for data integrity
        sa.UniqueConstraint(
            "internal_id",
            "fhir_resource_type",
            "tenant_id",
            name="uq_fhir_mapping_internal_resource_tenant",
        ),
        sa.UniqueConstraint(
            "fhir_resource_id",
            "fhir_resource_type",
            "fhir_server_url",
            "tenant_id",
            name="uq_fhir_mapping_fhir_resource_tenant",
        ),
    )

    # Create indexes for performance
    op.create_index("idx_fhir_mapping_internal_id", "fhir_mappings", ["internal_id"])
    op.create_index("idx_fhir_mapping_fhir_id", "fhir_mappings", ["fhir_resource_id"])
    op.create_index(
        "idx_fhir_mapping_resource_type", "fhir_mappings", ["fhir_resource_type"]
    )
    op.create_index("idx_fhir_mapping_status", "fhir_mappings", ["status"])
    op.create_index("idx_fhir_mapping_active", "fhir_mappings", ["is_active"])
    op.create_index("idx_fhir_mapping_tenant", "fhir_mappings", ["tenant_id"])
    op.create_index("idx_fhir_mapping_last_sync", "fhir_mappings", ["last_sync_at"])
    op.create_index("idx_fhir_mapping_error_count", "fhir_mappings", ["error_count"])
    op.create_index(
        "idx_fhir_mapping_correlation_id", "fhir_mappings", ["correlation_id"]
    )

    # Composite indexes for common queries
    op.create_index(
        "idx_fhir_mapping_lookup",
        "fhir_mappings",
        ["internal_id", "fhir_resource_type", "tenant_id"],
    )
    op.create_index(
        "idx_fhir_mapping_reverse_lookup",
        "fhir_mappings",
        ["fhir_resource_id", "fhir_resource_type", "tenant_id"],
    )
    op.create_index(
        "idx_fhir_mapping_sync_status",
        "fhir_mappings",
        ["status", "last_sync_at", "tenant_id"],
    )
    op.create_index(
        "idx_fhir_mapping_error_tracking",
        "fhir_mappings",
        ["status", "error_count", "last_error_at"],
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop indexes
    op.drop_index("idx_fhir_mapping_error_tracking", table_name="fhir_mappings")
    op.drop_index("idx_fhir_mapping_sync_status", table_name="fhir_mappings")
    op.drop_index("idx_fhir_mapping_reverse_lookup", table_name="fhir_mappings")
    op.drop_index("idx_fhir_mapping_lookup", table_name="fhir_mappings")
    op.drop_index("idx_fhir_mapping_correlation_id", table_name="fhir_mappings")
    op.drop_index("idx_fhir_mapping_error_count", table_name="fhir_mappings")
    op.drop_index("idx_fhir_mapping_last_sync", table_name="fhir_mappings")
    op.drop_index("idx_fhir_mapping_tenant", table_name="fhir_mappings")
    op.drop_index("idx_fhir_mapping_active", table_name="fhir_mappings")
    op.drop_index("idx_fhir_mapping_status", table_name="fhir_mappings")
    op.drop_index("idx_fhir_mapping_resource_type", table_name="fhir_mappings")
    op.drop_index("idx_fhir_mapping_fhir_id", table_name="fhir_mappings")
    op.drop_index("idx_fhir_mapping_internal_id", table_name="fhir_mappings")

    # Drop table
    op.drop_table("fhir_mappings")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS fhirmappingstatus")
    op.execute("DROP TYPE IF EXISTS fhirresourcetype")

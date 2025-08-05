"""Schema cleanup and index audit

Revision ID: schema_cleanup_audit
Revises: add_fhir_mapping
Create Date: 2025-01-06 12:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision = "schema_cleanup_audit"
down_revision = "add_fhir_mapping"
branch_labels = None
depends_on = None


def upgrade():
    """Add missing foreign keys, constraints, and optimize indexes."""

    # 1. Add missing foreign key for auth_tokens.parent_token_id
    # This is a self-referential foreign key for token rotation tracking
    op.create_foreign_key(
        "auth_tokens_parent_token_id_fkey",
        "auth_tokens",
        "auth_tokens",
        ["parent_token_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 2. Add missing indexes for critical query patterns

    # Auth tokens - composite index for user token lookup with type/status
    op.create_index(
        "idx_auth_tokens_user_status_type",
        "auth_tokens",
        ["user_id", "status", "token_type"],
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )

    # Auth tokens - index for token cleanup operations
    op.create_index(
        "idx_auth_tokens_tenant_status_expires",
        "auth_tokens",
        ["tenant_id", "status", "expires_at"],
        postgresql_where=sa.text("tenant_id IS NOT NULL"),
    )

    # Encryption keys - composite index for tenant key lookup by name/version
    op.create_index(
        "idx_encryption_keys_tenant_name_version",
        "encryption_keys",
        ["tenant_id", "key_name", "version"],
        postgresql_where=sa.text("tenant_id IS NOT NULL"),
    )

    # Encryption keys - index for key expiration monitoring
    op.create_index(
        "idx_encryption_keys_expires_status",
        "encryption_keys",
        ["expires_at", "status"],
        postgresql_where=sa.text("expires_at IS NOT NULL"),
    )

    # FHIR mappings - index for reverse FHIR lookup with server
    op.create_index(
        "idx_fhir_mappings_server_resource_type",
        "fhir_mappings",
        ["fhir_server_url", "fhir_resource_type"],
        postgresql_where=sa.text("fhir_server_url IS NOT NULL"),
    )

    # FHIR mappings - index for error monitoring and cleanup
    op.create_index(
        "idx_fhir_mappings_error_status_count",
        "fhir_mappings",
        ["error_count", "status"],
        postgresql_where=sa.text("CAST(error_count AS INTEGER) > 0"),
    )

    # Practice profiles - composite index for tenant-based active lookup
    op.create_index(
        "idx_practice_profiles_tenant_active",
        "practice_profiles",
        ["tenant_id", "is_active"],
        postgresql_where=sa.text("tenant_id IS NOT NULL"),
    )

    # Locations - composite index for practice location lookup
    op.create_index(
        "idx_locations_practice_active",
        "locations",
        ["practice_profile_id", "is_active"],
    )

    # Locations - index for geographic queries
    op.create_index(
        "idx_locations_geography",
        "locations",
        ["city", "state", "zip_code"],
    )

    # FHIR mappings - partial index for active mappings
    op.create_index(
        "idx_fhir_mappings_active_internal",
        "fhir_mappings",
        ["internal_id"],
        postgresql_where=sa.text("is_active = true"),
    )

    # Practice profiles - partial index for active practices
    op.create_index(
        "idx_practice_profiles_active_name",
        "practice_profiles",
        ["name"],
        postgresql_where=sa.text("is_active = true"),
    )

    # Locations - partial index for active locations
    op.create_index(
        "idx_locations_active_name",
        "locations",
        ["name"],
        postgresql_where=sa.text("is_active = true"),
    )

    # 3. Add check constraints for data integrity

    # Auth tokens - ensure rotation count is non-negative
    op.create_check_constraint(
        "ck_auth_tokens_rotation_count_valid",
        "auth_tokens",
        sa.text("CAST(rotation_count AS INTEGER) >= 0"),
    )

    # Encryption keys - ensure version is valid
    op.create_check_constraint(
        "ck_encryption_keys_version_valid",
        "encryption_keys",
        sa.text("CAST(version AS INTEGER) > 0"),
    )

    # FHIR mappings - ensure error count is non-negative
    op.create_check_constraint(
        "ck_fhir_mappings_error_count_valid",
        "fhir_mappings",
        sa.text("CAST(error_count AS INTEGER) >= 0"),
    )

    # Practice profiles - ensure NPI number format (10 digits)
    op.create_check_constraint(
        "ck_practice_profiles_npi_format",
        "practice_profiles",
        sa.text("npi_number ~ '^[0-9]{10}$'"),
    )

    # Locations - ensure zip code format
    op.create_check_constraint(
        "ck_locations_zip_format",
        "locations",
        sa.text("zip_code ~ '^[0-9]{5}([0-9]{4})?$'"),
    )


def downgrade():
    """Remove added constraints and indexes."""

    # Drop indexes in reverse order
    op.drop_index("idx_locations_active_name", table_name="locations")
    op.drop_index("idx_locations_geography", table_name="locations")
    op.drop_index("idx_locations_practice_active", table_name="locations")
    op.drop_index("idx_practice_profiles_active_name", table_name="practice_profiles")
    op.drop_index("idx_practice_profiles_tenant_active", table_name="practice_profiles")
    op.drop_index("idx_fhir_mappings_active_internal", table_name="fhir_mappings")
    op.drop_index("idx_fhir_mappings_error_status_count", table_name="fhir_mappings")
    op.drop_index("idx_fhir_mappings_server_resource_type", table_name="fhir_mappings")
    op.drop_index(
        "idx_encryption_keys_active_tenant_type", table_name="encryption_keys"
    )
    op.drop_index("idx_encryption_keys_expires_status", table_name="encryption_keys")
    op.drop_index(
        "idx_encryption_keys_tenant_name_version", table_name="encryption_keys"
    )
    op.drop_index("idx_auth_tokens_active_hash", table_name="auth_tokens")
    op.drop_index("idx_auth_tokens_tenant_status_expires", table_name="auth_tokens")
    op.drop_index("idx_auth_tokens_user_status_type", table_name="auth_tokens")

    # Drop check constraints
    op.drop_constraint("ck_locations_zip_format", "locations", type_="check")
    op.drop_constraint(
        "ck_practice_profiles_npi_format", "practice_profiles", type_="check"
    )
    op.drop_constraint(
        "ck_fhir_mappings_error_count_valid", "fhir_mappings", type_="check"
    )
    op.drop_constraint(
        "ck_encryption_keys_version_valid", "encryption_keys", type_="check"
    )
    op.drop_constraint(
        "ck_auth_tokens_rotation_count_valid", "auth_tokens", type_="check"
    )

    # Remove foreign key
    op.drop_constraint(
        "auth_tokens_parent_token_id_fkey", "auth_tokens", type_="foreignkey"
    )

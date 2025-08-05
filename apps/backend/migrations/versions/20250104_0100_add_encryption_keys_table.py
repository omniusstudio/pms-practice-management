"""add_encryption_keys_table

Revision ID: add_encryption_keys
Revises: add_performance_indexes
Create Date: 2025-01-04 01:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision = "add_encryption_keys"
down_revision = "add_performance_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema to add encryption_keys table."""

    # Create KeyType enum
    key_type_enum = postgresql.ENUM(
        "PHI_DATA",
        "PII_DATA",
        "FINANCIAL",
        "CLINICAL",
        "AUDIT_LOG",
        "BACKUP",
        "COMMUNICATION",
        name="keytype",
    )
    key_type_enum.create(op.get_bind())  # type: ignore

    # Create KeyStatus enum
    key_status_enum = postgresql.ENUM(
        "ACTIVE",
        "INACTIVE",
        "ROTATED",
        "EXPIRED",
        "COMPROMISED",
        "PENDING",
        name="keystatus",
    )
    key_status_enum.create(op.get_bind())  # type: ignore

    # Create KeyProvider enum
    key_provider_enum = postgresql.ENUM(
        "AWS_KMS",
        "AZURE_KV",
        "HASHICORP_VAULT",
        "GCP_KMS",
        "LOCAL_HSM",
        name="keyprovider",
    )
    key_provider_enum.create(op.get_bind())  # type: ignore

    # Create encryption_keys table
    op.create_table(  # type: ignore
        "encryption_keys",
        # Primary key and base model fields
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("tenant_id", sa.String(length=255), nullable=True),
        # Key identification and metadata
        sa.Column("key_name", sa.String(length=255), nullable=False),
        sa.Column("key_type", key_type_enum, nullable=False),
        # External KMS reference (never store actual key material)
        sa.Column("kms_key_id", sa.String(length=512), nullable=False, unique=True),
        sa.Column("kms_provider", key_provider_enum, nullable=False),
        sa.Column("kms_region", sa.String(length=100), nullable=True),
        sa.Column("kms_endpoint", sa.String(length=512), nullable=True),
        # Key lifecycle management
        sa.Column("status", key_status_enum, nullable=False, server_default="PENDING"),
        sa.Column("version", sa.String(length=50), nullable=False, server_default="1"),
        # Key rotation and expiration
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        # Key relationships for rotation
        sa.Column(
            "parent_key_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("encryption_keys.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Rollback support
        sa.Column("can_rollback", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("rollback_expires_at", sa.DateTime(timezone=True), nullable=True),
        # Security and compliance
        sa.Column(
            "key_algorithm",
            sa.String(length=100),
            nullable=False,
            server_default="AES-256-GCM",
        ),
        sa.Column("key_purpose", sa.Text, nullable=True),
        sa.Column("compliance_tags", sa.Text, nullable=True),
        # Access control and audit
        sa.Column("authorized_services", sa.Text, nullable=True),
        sa.Column("access_policy", sa.Text, nullable=True),
        # Integration with auth system
        sa.Column(
            "created_by_token_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_tokens.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "rotated_by_token_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_tokens.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Create indexes for performance and query optimization

    # Basic indexes from model definition
    op.create_index(  # type: ignore
        "ix_encryption_keys_key_name", "encryption_keys", ["key_name"]
    )
    op.create_index(  # type: ignore
        "ix_encryption_keys_key_type", "encryption_keys", ["key_type"]
    )
    op.create_index(  # type: ignore
        "ix_encryption_keys_kms_key_id", "encryption_keys", ["kms_key_id"], unique=True
    )
    op.create_index(  # type: ignore
        "ix_encryption_keys_kms_provider", "encryption_keys", ["kms_provider"]
    )
    op.create_index(  # type: ignore
        "ix_encryption_keys_status", "encryption_keys", ["status"]
    )
    op.create_index(  # type: ignore
        "ix_encryption_keys_version", "encryption_keys", ["version"]
    )
    op.create_index(  # type: ignore
        "ix_encryption_keys_expires_at", "encryption_keys", ["expires_at"]
    )
    op.create_index(  # type: ignore
        "ix_encryption_keys_parent_key_id", "encryption_keys", ["parent_key_id"]
    )
    op.create_index(  # type: ignore
        "ix_encryption_keys_correlation_id", "encryption_keys", ["correlation_id"]
    )
    op.create_index(  # type: ignore
        "ix_encryption_keys_tenant_id", "encryption_keys", ["tenant_id"]
    )
    op.create_index(  # type: ignore
        "ix_encryption_keys_created_by_token_id",
        "encryption_keys",
        ["created_by_token_id"],
    )

    # Composite indexes for complex queries

    # Tenant isolation and key lookup
    op.create_index(  # type: ignore
        "idx_encryption_keys_tenant_type",
        "encryption_keys",
        ["tenant_id", "key_type", "status"],
    )
    op.create_index(  # type: ignore
        "idx_encryption_keys_tenant_name",
        "encryption_keys",
        ["tenant_id", "key_name", "version"],
    )

    # Key lifecycle management
    op.create_index(  # type: ignore
        "idx_encryption_keys_status_expires",
        "encryption_keys",
        ["status", "expires_at"],
    )
    op.create_index(  # type: ignore
        "idx_encryption_keys_rotation",
        "encryption_keys",
        ["parent_key_id", "rotated_at"],
    )

    # KMS integration
    op.create_index(  # type: ignore
        "idx_encryption_keys_kms", "encryption_keys", ["kms_provider", "kms_key_id"]
    )

    # Audit and compliance
    op.create_index(  # type: ignore
        "idx_encryption_keys_audit",
        "encryption_keys",
        ["created_at", "tenant_id", "key_type"],
    )
    op.create_index(  # type: ignore
        "idx_encryption_keys_usage", "encryption_keys", ["last_used_at", "status"]
    )

    # Rollback support
    op.create_index(  # type: ignore
        "idx_encryption_keys_rollback",
        "encryption_keys",
        ["can_rollback", "rollback_expires_at"],
    )


def downgrade() -> None:
    """Downgrade database schema to remove encryption_keys table."""

    # Drop all indexes
    op.drop_index(  # type: ignore
        "idx_encryption_keys_rollback", table_name="encryption_keys"
    )
    op.drop_index(  # type: ignore
        "idx_encryption_keys_usage", table_name="encryption_keys"
    )
    op.drop_index(  # type: ignore
        "idx_encryption_keys_audit", table_name="encryption_keys"
    )
    op.drop_index(  # type: ignore
        "idx_encryption_keys_kms", table_name="encryption_keys"
    )
    op.drop_index(  # type: ignore
        "idx_encryption_keys_rotation", table_name="encryption_keys"
    )
    op.drop_index(  # type: ignore
        "idx_encryption_keys_status_expires", table_name="encryption_keys"
    )
    op.drop_index(  # type: ignore
        "idx_encryption_keys_tenant_name", table_name="encryption_keys"
    )
    op.drop_index(  # type: ignore
        "idx_encryption_keys_tenant_type", table_name="encryption_keys"
    )

    # Drop basic indexes
    op.drop_index(  # type: ignore
        "ix_encryption_keys_created_by_token_id", table_name="encryption_keys"
    )
    op.drop_index(  # type: ignore
        "ix_encryption_keys_tenant_id", table_name="encryption_keys"
    )
    op.drop_index(  # type: ignore
        "ix_encryption_keys_correlation_id", table_name="encryption_keys"
    )
    op.drop_index(  # type: ignore
        "ix_encryption_keys_parent_key_id", table_name="encryption_keys"
    )
    op.drop_index(  # type: ignore
        "ix_encryption_keys_expires_at", table_name="encryption_keys"
    )
    op.drop_index(  # type: ignore
        "ix_encryption_keys_version", table_name="encryption_keys"
    )
    op.drop_index(  # type: ignore
        "ix_encryption_keys_status", table_name="encryption_keys"
    )
    op.drop_index(  # type: ignore
        "ix_encryption_keys_kms_provider", table_name="encryption_keys"
    )
    op.drop_index(  # type: ignore
        "ix_encryption_keys_kms_key_id", table_name="encryption_keys"
    )
    op.drop_index(  # type: ignore
        "ix_encryption_keys_key_type", table_name="encryption_keys"
    )
    op.drop_index(  # type: ignore
        "ix_encryption_keys_key_name", table_name="encryption_keys"
    )

    # Drop the table
    op.drop_table("encryption_keys")  # type: ignore

    # Drop enums
    op.execute("DROP TYPE IF EXISTS keyprovider")  # type: ignore
    op.execute("DROP TYPE IF EXISTS keystatus")  # type: ignore
    op.execute("DROP TYPE IF EXISTS keytype")  # type: ignore

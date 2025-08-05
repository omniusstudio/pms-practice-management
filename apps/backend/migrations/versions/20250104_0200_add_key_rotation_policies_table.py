"""Add key rotation policies table

Revision ID: add_key_rotation_policies
Revises: add_encryption_keys
Create Date: 2025-01-04 02:00:00.000000

"""
import sqlalchemy as sa  # type: ignore

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision = "add_key_rotation_policies"
down_revision = "add_encryption_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create key rotation policies table."""
    # Create key_rotation_policies table
    op.create_table(  # type: ignore
        "key_rotation_policies",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("policy_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("key_type", sa.String(length=50), nullable=False),
        sa.Column("kms_provider", sa.String(length=50), nullable=False),
        sa.Column("rotation_trigger", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("rotation_interval_days", sa.Integer(), nullable=True),
        sa.Column("rotation_time_of_day", sa.String(length=8), nullable=True),
        sa.Column("timezone", sa.String(length=50), nullable=True),
        sa.Column("max_usage_count", sa.Integer(), nullable=True),
        sa.Column("usage_threshold_warning", sa.Integer(), nullable=True),
        sa.Column("rotation_events", sa.JSON(), nullable=True),
        sa.Column("enable_rollback", sa.Boolean(), nullable=True),
        sa.Column("rollback_period_hours", sa.Integer(), nullable=True),
        sa.Column("retain_old_keys_days", sa.Integer(), nullable=True),
        sa.Column("notification_settings", sa.JSON(), nullable=True),
        sa.Column("compliance_tags", sa.JSON(), nullable=True),
        sa.Column("authorized_services", sa.JSON(), nullable=True),
        sa.Column("created_by_token_id", sa.String(36), nullable=True),
        sa.Column("last_modified_by_token_id", sa.String(36), nullable=True),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("last_rotation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_rotation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for performance
    op.create_index(  # type: ignore
        "idx_key_rotation_policies_tenant_id", "key_rotation_policies", ["tenant_id"]
    )
    op.create_index(  # type: ignore
        "idx_key_rotation_policies_status", "key_rotation_policies", ["status"]
    )
    op.create_index(  # type: ignore
        "idx_key_rotation_policies_next_rotation",
        "key_rotation_policies",
        ["next_rotation_at"],
    )
    op.create_index(  # type: ignore
        "idx_key_rotation_policies_tenant_type",
        "key_rotation_policies",
        ["tenant_id", "key_type", "kms_provider"],
    )

    # Add rotation_policy_id column to encryption_keys table
    op.add_column(  # type: ignore
        "encryption_keys", sa.Column("rotation_policy_id", sa.String(36), nullable=True)
    )

    # Create foreign key constraint
    op.create_foreign_key(  # type: ignore
        "fk_encryption_keys_rotation_policy_id",
        "encryption_keys",
        "key_rotation_policies",
        ["rotation_policy_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Create index on the foreign key
    op.create_index(  # type: ignore
        "idx_encryption_keys_rotation_policy_id",
        "encryption_keys",
        ["rotation_policy_id"],
    )


def downgrade() -> None:
    """Drop key rotation policies table and related changes."""
    # Drop foreign key constraint and index
    op.drop_index(  # type: ignore
        "idx_encryption_keys_rotation_policy_id", table_name="encryption_keys"
    )
    op.drop_constraint(  # type: ignore
        "fk_encryption_keys_rotation_policy_id", "encryption_keys", type_="foreignkey"
    )

    # Drop the rotation_policy_id column
    op.drop_column("encryption_keys", "rotation_policy_id")  # type: ignore

    # Drop indexes
    op.drop_index(  # type: ignore
        "idx_key_rotation_policies_tenant_type", table_name="key_rotation_policies"
    )
    op.drop_index(  # type: ignore
        "idx_key_rotation_policies_next_rotation", table_name="key_rotation_policies"
    )
    op.drop_index(  # type: ignore
        "idx_key_rotation_policies_status", table_name="key_rotation_policies"
    )
    op.drop_index(  # type: ignore
        "idx_key_rotation_policies_tenant_id", table_name="key_rotation_policies"
    )

    # Drop the table
    op.drop_table("key_rotation_policies")  # type: ignore

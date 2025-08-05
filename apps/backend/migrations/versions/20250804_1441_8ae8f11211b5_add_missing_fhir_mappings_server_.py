"""add_missing_fhir_mappings_server_resource_type_index

Revision ID: 8ae8f11211b5
Revises: d40ecb01ecd0
Create Date: 2025-08-04 14:41:22.199237

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "8ae8f11211b5"
down_revision = "d40ecb01ecd0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Add missing index for FHIR mappings server resource type lookup
    op.create_index(
        "idx_fhir_mappings_server_resource_type",
        "fhir_mappings",
        ["fhir_server_url", "fhir_resource_type"],
        unique=False,
        postgresql_where="(fhir_server_url IS NOT NULL)",
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Remove the index
    op.drop_index(
        "idx_fhir_mappings_server_resource_type",
        table_name="fhir_mappings",
        postgresql_where="(fhir_server_url IS NOT NULL)",
    )

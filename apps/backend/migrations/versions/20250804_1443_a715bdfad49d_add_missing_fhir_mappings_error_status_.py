"""add_missing_fhir_mappings_error_status_count_index

Revision ID: a715bdfad49d
Revises: 8ae8f11211b5
Create Date: 2025-08-04 14:43:15.739681

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a715bdfad49d"
down_revision = "8ae8f11211b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Add missing index for FHIR mappings error status count
    op.create_index(
        "idx_fhir_mappings_error_status_count",
        "fhir_mappings",
        ["error_count", "status"],
        unique=False,
        postgresql_where="((error_count)::integer > 0)",
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Remove the index
    op.drop_index(
        "idx_fhir_mappings_error_status_count",
        table_name="fhir_mappings",
        postgresql_where="((error_count)::integer > 0)",
    )

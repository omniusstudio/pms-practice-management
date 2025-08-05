"""merge_encryption_and_fhir_branches

Revision ID: c8c1872a99cf
Revises: add_key_rotation_policies, add_fhir_mapping
Create Date: 2025-08-04 02:03:49.037125

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c8c1872a99cf"
down_revision = ("add_key_rotation_policies", "add_fhir_mapping")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    pass


def downgrade() -> None:
    """Downgrade database schema."""
    pass

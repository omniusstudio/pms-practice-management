"""merge_all_branches

Revision ID: 2b8812283e69
Revises: c8c1872a99cf, schema_cleanup_audit
Create Date: 2025-08-04 12:19:00.395503

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "2b8812283e69"
down_revision = ("c8c1872a99cf", "schema_cleanup_audit")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    pass


def downgrade() -> None:
    """Downgrade database schema."""
    pass

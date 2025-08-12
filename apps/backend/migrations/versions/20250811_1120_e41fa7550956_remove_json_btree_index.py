"""remove_json_btree_index

Revision ID: e41fa7550956
Revises: 68ff0d0c4da2
Create Date: 2025-08-11 11:20:00.188676

"""
from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision = "e41fa7550956"
down_revision = "68ff0d0c4da2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop the problematic btree index on JSON column."""
    # Use connection.execute to avoid linter issues
    connection = op.get_bind()
    connection.execute("DROP INDEX IF EXISTS idx_users_active_roles")


def downgrade() -> None:
    """Downgrade database schema."""
    # Do not recreate the problematic index
    # PostgreSQL doesn't support btree indexes on JSON columns
    pass
"""add_parent_token_id_foreign_key_constraint

Revision ID: 68ff0d0c4da2
Revises: a715bdfad49d
Create Date: 2025-08-04 14:44:35.255989

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "68ff0d0c4da2"
down_revision = "a715bdfad49d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Add foreign key constraint for parent_token_id
    op.create_foreign_key(
        "auth_tokens_parent_token_id_fkey",
        "auth_tokens",
        "auth_tokens",
        ["parent_token_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Remove the foreign key constraint
    op.drop_constraint(
        "auth_tokens_parent_token_id_fkey", "auth_tokens", type_="foreignkey"
    )

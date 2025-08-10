"""Add access review tables

Revision ID: add_access_review_tables
Revises:
Create Date: 2024-01-15 10:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_access_review_tables"
down_revision = None  # Update this with the latest revision
branch_labels = None
depends_on = None


def upgrade():
    """Create access review tables."""
    # Create access_review_logs table
    op.create_table(
        "access_review_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource", sa.String(length=255), nullable=True),
        sa.Column("method", sa.String(length=10), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, default=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for access_review_logs
    op.create_index(
        op.f("ix_access_review_logs_id"), "access_review_logs", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_access_review_logs_user_id"),
        "access_review_logs",
        ["user_id"],
        unique=False,
    )

    # Create quarterly_access_reviews table
    op.create_table(
        "quarterly_access_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.String(length=7), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("quarter_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, default="pending"),
        sa.Column("reviewer_id", sa.String(length=255), nullable=True),
        sa.Column("total_users", sa.Integer(), nullable=False, default=0),
        sa.Column("reviewed_users", sa.Integer(), nullable=False, default=0),
        sa.Column("findings", sa.JSON(), nullable=True),
        sa.Column("recommendations", sa.JSON(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create access_review_checklists table
    op.create_table(
        "access_review_checklists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("item_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, default="pending"),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("completed_by", sa.String(length=255), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for access_review_checklists
    op.create_index(
        op.f("ix_access_review_checklists_review_id"),
        "access_review_checklists",
        ["review_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_access_review_checklists_user_id"),
        "access_review_checklists",
        ["user_id"],
        unique=False,
    )


def downgrade():
    """Drop access review tables."""
    # Drop indexes first
    op.drop_index(
        op.f("ix_access_review_checklists_user_id"),
        table_name="access_review_checklists",
    )
    op.drop_index(
        op.f("ix_access_review_checklists_review_id"),
        table_name="access_review_checklists",
    )
    op.drop_index(
        op.f("ix_access_review_logs_user_id"), table_name="access_review_logs"
    )
    op.drop_index(op.f("ix_access_review_logs_id"), table_name="access_review_logs")

    # Drop tables
    op.drop_table("access_review_checklists")
    op.drop_table("quarterly_access_reviews")
    op.drop_table("access_review_logs")

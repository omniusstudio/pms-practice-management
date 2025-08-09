"""Add performance indexes for query optimization.

Revision ID: 20250103_1200_add_performance_indexes
Revises: 20250803_1441_e8d4947f3106_add_practice_tables
Create Date: 2025-01-03 12:00:00.000000

"""
import sqlalchemy as sa

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision = "add_performance_indexes"
down_revision = "36e149658444"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes for common query patterns."""

    # Client indexes for search and filtering
    op.create_index(
        "idx_clients_name_search",
        "clients",
        ["last_name", "first_name", "is_active"],
        unique=False,
    )
    op.create_index(
        "idx_clients_email_active", "clients", ["email", "is_active"], unique=False
    )
    op.create_index(
        "idx_clients_phone_active", "clients", ["phone", "is_active"], unique=False
    )

    # Provider indexes for scheduling queries
    op.create_index(
        "idx_providers_specialty_active",
        "providers",
        ["specialty", "is_active"],
        unique=False,
    )
    op.create_index(
        "idx_providers_license_state",
        "providers",
        ["license_state", "license_number"],
        unique=False,
    )

    # Appointment indexes for calendar and scheduling queries
    op.create_index(
        "idx_appointments_provider_date_status",
        "appointments",
        ["provider_id", "scheduled_start", "status"],
        unique=False,
    )
    op.create_index(
        "idx_appointments_client_date_status",
        "appointments",
        ["client_id", "scheduled_start", "status"],
        unique=False,
    )
    op.create_index(
        "idx_appointments_date_range",
        "appointments",
        ["scheduled_start", "scheduled_end"],
        unique=False,
    )
    op.create_index(
        "idx_appointments_status_date",
        "appointments",
        ["status", "scheduled_start"],
        unique=False,
    )
    op.create_index(
        "idx_appointments_type_date",
        "appointments",
        ["appointment_type", "scheduled_start"],
        unique=False,
    )

    # Note indexes for clinical queries
    op.create_index(
        "idx_notes_client_type_date",
        "notes",
        ["client_id", "note_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_notes_provider_type_date",
        "notes",
        ["provider_id", "note_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_notes_signed_date", "notes", ["is_signed", "created_at"], unique=False
    )
    op.create_index(
        "idx_notes_billable_date", "notes", ["billable", "created_at"], unique=False
    )
    op.create_index(
        "idx_notes_appointment_signed",
        "notes",
        ["appointment_id", "is_signed"],
        unique=False,
    )

    # Ledger indexes for financial queries
    op.create_index(
        "idx_ledger_client_type_date",
        "ledger",
        ["client_id", "transaction_type", "service_date"],
        unique=False,
    )
    op.create_index(
        "idx_ledger_service_date_posted",
        "ledger",
        ["service_date", "is_posted"],
        unique=False,
    )
    op.create_index(
        "idx_ledger_posted_reconciled",
        "ledger",
        ["is_posted", "is_reconciled"],
        unique=False,
    )
    op.create_index(
        "idx_ledger_billing_code_date",
        "ledger",
        ["billing_code", "service_date"],
        unique=False,
    )
    op.create_index(
        "idx_ledger_amount_date", "ledger", ["amount", "service_date"], unique=False
    )

    # Audit log indexes for compliance queries
    op.create_index(
        "idx_audit_log_user_action_date",
        "audit_log",
        ["user_id", "action", "created_at"],
    )
    op.create_index(
        "idx_audit_log_resource_action",
        "audit_log",
        ["resource_type", "action", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_audit_log_correlation_date",
        "audit_log",
        ["correlation_id", "created_at"],
        unique=False,
    )

    # Composite indexes for common multi-table queries
    op.create_index(
        "idx_clients_active_created",
        "clients",
        ["is_active", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_providers_active_created",
        "providers",
        ["is_active", "created_at"],
        unique=False,
    )

    # Partial indexes for active records (PostgreSQL specific)
    # These will be ignored on other databases
    # Temporarily commented out to debug migration issues
    # try:
    #     op.create_index(
    #         "idx_clients_active_only",
    #         "clients",
    #         ["last_name", "first_name"],
    #         unique=False,
    #         postgresql_where=sa.text("is_active = true"),
    #     )
    #     op.create_index(
    #         "idx_providers_active_only",
    #         "providers",
    #         ["last_name", "first_name"],
    #         unique=False,
    #         postgresql_where=sa.text("is_active = true"),
    #     )
    #     op.create_index(
    #         "idx_appointments_upcoming",
    #         "appointments",
    #         ["provider_id", "scheduled_start"],
    #         unique=False,
    #         postgresql_where=sa.text(
    #             "status IN ('scheduled', 'confirmed', 'in_progress')"
    #         ),
    #     )
    # except Exception:
    #     # Ignore if database doesn't support partial indexes
    #     pass


def downgrade() -> None:
    """Remove performance indexes."""

    # Drop partial indexes first (if they exist)
    try:
        op.drop_index("idx_appointments_upcoming", table_name="appointments")
        op.drop_index("idx_providers_active_only", table_name="providers")
        op.drop_index("idx_clients_active_only", table_name="clients")
    except Exception:
        pass

    # Drop composite indexes
    op.drop_index("idx_providers_active_created", table_name="providers")
    op.drop_index("idx_clients_active_created", table_name="clients")

    # Drop audit log indexes
    op.drop_index("idx_audit_log_correlation_date", table_name="audit_log")
    op.drop_index("idx_audit_log_resource_action", table_name="audit_log")
    op.drop_index("idx_audit_log_user_action_date", table_name="audit_log")

    # Drop ledger indexes
    op.drop_index("idx_ledger_amount_date", table_name="ledger")
    op.drop_index("idx_ledger_billing_code_date", table_name="ledger")
    op.drop_index("idx_ledger_posted_reconciled", table_name="ledger")
    op.drop_index("idx_ledger_service_date_posted", table_name="ledger")
    op.drop_index("idx_ledger_client_type_date", table_name="ledger")

    # Drop note indexes
    op.drop_index("idx_notes_appointment_signed", table_name="notes")
    op.drop_index("idx_notes_billable_date", table_name="notes")
    op.drop_index("idx_notes_signed_date", table_name="notes")
    op.drop_index("idx_notes_provider_type_date", table_name="notes")
    op.drop_index("idx_notes_client_type_date", table_name="notes")

    # Drop appointment indexes
    op.drop_index("idx_appointments_type_date", table_name="appointments")
    op.drop_index("idx_appointments_status_date", table_name="appointments")
    op.drop_index("idx_appointments_date_range", table_name="appointments")
    op.drop_index("idx_appointments_client_date_status", table_name="appointments")
    op.drop_index("idx_appointments_provider_date_status", table_name="appointments")

    # Drop provider indexes
    op.drop_index("idx_providers_license_state", table_name="providers")
    op.drop_index("idx_providers_specialty_active", table_name="providers")

    # Drop client indexes
    op.drop_index("idx_clients_phone_active", table_name="clients")
    op.drop_index("idx_clients_email_active", table_name="clients")
    op.drop_index("idx_clients_name_search", table_name="clients")

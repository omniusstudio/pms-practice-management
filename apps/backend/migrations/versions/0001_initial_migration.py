"""Initial migration - baseline schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""

    # Create audit_log table first (no dependencies)
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("old_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for audit_log
    op.create_index("idx_audit_action", "audit_log", ["action"])
    op.create_index("idx_audit_correlation_id", "audit_log", ["correlation_id"])
    op.create_index("idx_audit_created_at", "audit_log", ["created_at"])
    op.create_index("idx_audit_resource", "audit_log", ["resource_type", "resource_id"])
    op.create_index("idx_audit_user_date", "audit_log", ["user_id", "created_at"])
    op.create_index("idx_audit_user_id", "audit_log", ["user_id"])

    # Create providers table
    op.create_table(
        "providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("middle_name", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=50), nullable=True),
        sa.Column("credentials", sa.String(length=200), nullable=True),
        sa.Column("specialty", sa.String(length=200), nullable=True),
        sa.Column("license_number", sa.String(length=100), nullable=True),
        sa.Column("license_state", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("office_phone", sa.String(length=20), nullable=True),
        sa.Column("office_address_line1", sa.String(length=255), nullable=True),
        sa.Column("office_address_line2", sa.String(length=255), nullable=True),
        sa.Column("office_city", sa.String(length=100), nullable=True),
        sa.Column("office_state", sa.String(length=50), nullable=True),
        sa.Column("office_zip_code", sa.String(length=10), nullable=True),
        sa.Column("npi_number", sa.String(length=20), nullable=True),
        sa.Column("tax_id", sa.String(length=20), nullable=True),
        sa.Column("default_appointment_duration", sa.String(length=10), nullable=False),
        sa.Column("accepts_new_patients", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("administrative_notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("npi_number"),
    )

    # Create indexes for providers
    op.create_index("idx_provider_active", "providers", ["is_active"])
    op.create_index("idx_provider_email", "providers", ["email"])
    op.create_index("idx_provider_license", "providers", ["license_number"])
    op.create_index("idx_provider_name", "providers", ["last_name", "first_name"])
    op.create_index("idx_provider_npi", "providers", ["npi_number"])
    op.create_index("idx_provider_specialty", "providers", ["specialty"])

    # Create clients table
    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("middle_name", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("address_line1", sa.String(length=255), nullable=True),
        sa.Column("address_line2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=50), nullable=True),
        sa.Column("zip_code", sa.String(length=10), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(length=20), nullable=True),
        sa.Column("insurance_provider", sa.String(length=255), nullable=True),
        sa.Column("insurance_id", sa.String(length=100), nullable=True),
        sa.Column("emergency_contact_name", sa.String(length=200), nullable=True),
        sa.Column("emergency_contact_phone", sa.String(length=20), nullable=True),
        sa.Column(
            "emergency_contact_relationship", sa.String(length=100), nullable=True
        ),
        sa.Column("primary_diagnosis", sa.Text(), nullable=True),
        sa.Column("secondary_diagnoses", sa.Text(), nullable=True),
        sa.Column("medications", sa.Text(), nullable=True),
        sa.Column("allergies", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("preferred_language", sa.String(length=50), nullable=False),
        sa.Column("communication_preferences", sa.Text(), nullable=True),
        sa.Column("intake_notes", sa.Text(), nullable=True),
        sa.Column("administrative_notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for clients
    op.create_index("idx_client_active", "clients", ["is_active"])
    op.create_index("idx_client_dob", "clients", ["date_of_birth"])
    op.create_index("idx_client_email", "clients", ["email"])
    op.create_index("idx_client_name", "clients", ["last_name", "first_name"])
    op.create_index("idx_client_phone", "clients", ["phone"])

    # Create appointments table
    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "appointment_type",
            sa.Enum(
                "INITIAL_CONSULTATION",
                "FOLLOW_UP",
                "THERAPY_SESSION",
                "MEDICATION_MANAGEMENT",
                "GROUP_THERAPY",
                "FAMILY_THERAPY",
                "CRISIS_INTERVENTION",
                "ASSESSMENT",
                "OTHER",
                name="appointmenttype",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "SCHEDULED",
                "CONFIRMED",
                "IN_PROGRESS",
                "COMPLETED",
                "CANCELLED",
                "NO_SHOW",
                "RESCHEDULED",
                name="appointmentstatus",
            ),
            nullable=False,
        ),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("billable_units", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("is_telehealth", sa.Boolean(), nullable=False),
        sa.Column("meeting_link", sa.String(length=500), nullable=True),
        sa.Column("reason_for_visit", sa.Text(), nullable=True),
        sa.Column("appointment_notes", sa.Text(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("reminder_sent", sa.Boolean(), nullable=False),
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmation_sent", sa.Boolean(), nullable=False),
        sa.Column("confirmation_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("copay_amount", sa.String(length=10), nullable=True),
        sa.Column("insurance_authorization", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for appointments
    op.create_index("idx_appointment_client", "appointments", ["client_id"])
    op.create_index(
        "idx_appointment_client_date", "appointments", ["client_id", "scheduled_start"]
    )
    op.create_index(
        "idx_appointment_date_range",
        "appointments",
        ["scheduled_start", "scheduled_end"],
    )
    op.create_index("idx_appointment_provider", "appointments", ["provider_id"])
    op.create_index(
        "idx_appointment_provider_date",
        "appointments",
        ["provider_id", "scheduled_start"],
    )
    op.create_index(
        "idx_appointment_scheduled_start", "appointments", ["scheduled_start"]
    )
    op.create_index("idx_appointment_status", "appointments", ["status"])
    op.create_index("idx_appointment_type", "appointments", ["appointment_type"])

    # Create notes table
    op.create_table(
        "notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "note_type",
            sa.Enum(
                "PROGRESS_NOTE",
                "INTAKE_NOTE",
                "ASSESSMENT",
                "TREATMENT_PLAN",
                "DISCHARGE_SUMMARY",
                "ADMINISTRATIVE",
                "BILLING",
                "OTHER",
                name="notetype",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("diagnosis_codes", sa.Text(), nullable=True),
        sa.Column("treatment_goals", sa.Text(), nullable=True),
        sa.Column("interventions", sa.Text(), nullable=True),
        sa.Column("client_response", sa.Text(), nullable=True),
        sa.Column("plan", sa.Text(), nullable=True),
        sa.Column("is_signed", sa.Boolean(), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False),
        sa.Column("requires_review", sa.Boolean(), nullable=False),
        sa.Column("billable", sa.Boolean(), nullable=False),
        sa.Column("billing_code", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(
            ["appointment_id"], ["appointments.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for notes
    op.create_index("idx_note_appointment", "notes", ["appointment_id"])
    op.create_index("idx_note_billable", "notes", ["billable"])
    op.create_index("idx_note_client", "notes", ["client_id"])
    op.create_index("idx_note_client_date", "notes", ["client_id", "created_at"])
    op.create_index("idx_note_provider", "notes", ["provider_id"])
    op.create_index("idx_note_provider_date", "notes", ["provider_id", "created_at"])
    op.create_index("idx_note_signed", "notes", ["is_signed"])
    op.create_index("idx_note_type", "notes", ["note_type"])

    # Create ledger table
    op.create_table(
        "ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "transaction_type",
            sa.Enum(
                "CHARGE",
                "PAYMENT",
                "ADJUSTMENT",
                "REFUND",
                "WRITE_OFF",
                "INSURANCE_PAYMENT",
                "COPAY",
                "DEDUCTIBLE",
                name="transactiontype",
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=True),
        sa.Column("billing_code", sa.String(length=20), nullable=True),
        sa.Column("diagnosis_code", sa.String(length=20), nullable=True),
        sa.Column(
            "payment_method",
            sa.Enum(
                "CASH",
                "CHECK",
                "CREDIT_CARD",
                "DEBIT_CARD",
                "BANK_TRANSFER",
                "INSURANCE",
                "OTHER",
                name="paymentmethod",
            ),
            nullable=True,
        ),
        sa.Column("reference_number", sa.String(length=100), nullable=True),
        sa.Column("check_number", sa.String(length=50), nullable=True),
        sa.Column("insurance_claim_number", sa.String(length=100), nullable=True),
        sa.Column("insurance_authorization", sa.String(length=100), nullable=True),
        sa.Column("is_posted", sa.Boolean(), nullable=False),
        sa.Column("is_reconciled", sa.Boolean(), nullable=False),
        sa.Column("reconciliation_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for ledger
    op.create_index("idx_ledger_amount", "ledger", ["amount"])
    op.create_index("idx_ledger_billing_code", "ledger", ["billing_code"])
    op.create_index("idx_ledger_client", "ledger", ["client_id"])
    op.create_index("idx_ledger_client_date", "ledger", ["client_id", "service_date"])
    op.create_index("idx_ledger_posted", "ledger", ["is_posted"])
    op.create_index("idx_ledger_reconciled", "ledger", ["is_reconciled"])
    op.create_index("idx_ledger_service_date", "ledger", ["service_date"])
    op.create_index("idx_ledger_transaction_type", "ledger", ["transaction_type"])


def downgrade() -> None:
    """Downgrade database schema."""

    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table("ledger")
    op.drop_table("notes")
    op.drop_table("appointments")
    op.drop_table("clients")
    op.drop_table("providers")
    op.drop_table("audit_log")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS paymentmethod")
    op.execute("DROP TYPE IF EXISTS transactiontype")
    op.execute("DROP TYPE IF EXISTS notetype")
    op.execute("DROP TYPE IF EXISTS appointmentstatus")
    op.execute("DROP TYPE IF EXISTS appointmenttype")

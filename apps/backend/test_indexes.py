#!/usr/bin/env python3

import os
import sys

from sqlalchemy import create_engine, text

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import get_settings  # noqa: E402


def test_index_creation():
    settings = get_settings()
    engine = create_engine(settings.database_url)

    # List of index creation statements from the migration
    index_statements = [
        (
            "CREATE INDEX idx_clients_name_search ON clients "
            "(last_name, first_name, is_active)"
        ),
        "CREATE INDEX idx_clients_email_active ON clients (email, is_active)",
        "CREATE INDEX idx_clients_phone_active ON clients (phone, is_active)",
        (
            "CREATE INDEX idx_providers_specialty_active ON providers "
            "(specialty, is_active)"
        ),
        (
            "CREATE INDEX idx_providers_license_state ON providers "
            "(license_state, license_number)"
        ),
        (
            "CREATE INDEX idx_appointments_provider_date_status ON appointments "
            "(provider_id, scheduled_start, status)"
        ),
        (
            "CREATE INDEX idx_appointments_client_date_status ON appointments "
            "(client_id, scheduled_start, status)"
        ),
        (
            "CREATE INDEX idx_appointments_date_range ON appointments "
            "(scheduled_start, scheduled_end)"
        ),
        (
            "CREATE INDEX idx_appointments_status_date ON appointments "
            "(status, scheduled_start)"
        ),
        (
            "CREATE INDEX idx_appointments_type_date ON appointments "
            "(appointment_type, scheduled_start)"
        ),
        (
            "CREATE INDEX idx_notes_client_type_date ON notes "
            "(client_id, note_type, created_at)"
        ),
        (
            "CREATE INDEX idx_notes_provider_type_date ON notes "
            "(provider_id, note_type, created_at)"
        ),
        "CREATE INDEX idx_notes_signed_date ON notes (is_signed, created_at)",
        "CREATE INDEX idx_notes_billable_date ON notes (billable, created_at)",
        (
            "CREATE INDEX idx_notes_appointment_signed ON notes "
            "(appointment_id, is_signed)"
        ),
        (
            "CREATE INDEX idx_ledger_client_type_date ON ledger "
            "(client_id, transaction_type, service_date)"
        ),
        (
            "CREATE INDEX idx_ledger_service_date_posted ON ledger "
            "(service_date, is_posted)"
        ),
        (
            "CREATE INDEX idx_ledger_posted_reconciled ON ledger "
            "(is_posted, is_reconciled)"
        ),
        (
            "CREATE INDEX idx_ledger_billing_code_date ON ledger "
            "(billing_code, service_date)"
        ),
        "CREATE INDEX idx_ledger_amount_date ON ledger (amount, service_date)",
        (
            "CREATE INDEX idx_audit_log_user_action_date ON audit_log "
            "(user_id, action, created_at)"
        ),
        (
            "CREATE INDEX idx_audit_log_resource_action ON audit_log "
            "(resource_type, action, created_at)"
        ),
        (
            "CREATE INDEX idx_audit_log_correlation_date ON audit_log "
            "(correlation_id, created_at)"
        ),
        (
            "CREATE INDEX idx_clients_active_created ON clients "
            "(is_active, created_at)"
        ),
        (
            "CREATE INDEX idx_providers_active_created ON providers "
            "(is_active, created_at)"
        ),
    ]

    with engine.connect() as conn:
        for i, stmt in enumerate(index_statements, 1):
            try:
                stmt_preview = stmt[:50] if len(stmt) > 50 else stmt
                total = len(index_statements)
                print(f"Creating index {i}/{total}: {stmt_preview}...")
                conn.execute(text(stmt))
                conn.commit()
                print("✓ Success")
            except Exception as e:
                print(f"✗ Failed: {e}")
                print(f"Statement: {stmt}")
                return False

    print("All indexes created successfully!")
    return True


if __name__ == "__main__":
    test_index_creation()

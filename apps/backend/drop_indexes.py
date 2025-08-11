#!/usr/bin/env python3

import os
import sys

from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.config import get_settings  # noqa: E402


def drop_indexes():
    settings = get_settings()
    engine = create_engine(settings.database_url)

    index_names = [
        "idx_clients_name_search",
        "idx_clients_email_active",
        "idx_clients_phone_active",
        "idx_providers_specialty_active",
        "idx_providers_license_state",
        "idx_appointments_provider_date_status",
        "idx_appointments_client_date_status",
        "idx_appointments_date_range",
        "idx_appointments_status_date",
        "idx_appointments_type_date",
        "idx_notes_client_type_date",
        "idx_notes_provider_type_date",
        "idx_notes_signed_date",
        "idx_notes_billable_date",
        "idx_notes_appointment_signed",
        "idx_ledger_client_type_date",
        "idx_ledger_service_date_posted",
        "idx_ledger_posted_reconciled",
        "idx_ledger_billing_code_date",
        "idx_ledger_amount_date",
        "idx_audit_log_user_action_date",
        "idx_audit_log_resource_action",
        "idx_audit_log_correlation_date",
        "idx_clients_active_created",
        "idx_providers_active_created",
    ]

    with engine.connect() as conn:
        for idx_name in index_names:
            try:
                print(f"Dropping index: {idx_name}")
                conn.execute(text(f"DROP INDEX IF EXISTS {idx_name}"))
                conn.commit()
                print(f"✓ Dropped {idx_name}")
            except Exception as e:
                print(f"✗ Failed to drop {idx_name}: {e}")

    print("Finished dropping indexes")


if __name__ == "__main__":
    drop_indexes()

#!/usr/bin/env python3
"""Check table record counts."""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))

from database import SessionLocal
from sqlalchemy import text

def main():
    session = SessionLocal()
    tables = [
        'practice_profiles', 'locations', 'clients', 'providers',
        'appointments', 'notes', 'ledger', 'encryption_keys',
        'fhir_mappings', 'auth_tokens', 'users', 'audit_log',
        'key_rotation_policies'
    ]

    print("Database Table Record Counts:")
    print("=" * 40)

    for table in tables:
        try:
            result = session.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar()
            print(f'{table:20}: {result:>6} records')
        except Exception as e:
            print(f'{table:20}: Error - {str(e)[:50]}')

    session.close()

if __name__ == "__main__":
    main()

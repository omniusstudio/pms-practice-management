#!/usr/bin/env python3

import sqlalchemy as sa

from database import engine


def enum_exists(enum_name: str) -> bool:
    conn = engine.connect()
    try:
        result = conn.execute(
            sa.text("SELECT EXISTS(SELECT 1 FROM pg_type WHERE typname = :name)"),
            {"name": enum_name},
        )
        exists = result.scalar()
        print(f"Enum '{enum_name}' exists: {exists}")
        return exists
    finally:
        conn.close()


if __name__ == "__main__":
    print("Testing enum existence:")
    enum_exists("keytype")
    enum_exists("keystatus")
    enum_exists("keyprovider")
    enum_exists("appointmenttype")  # This should exist

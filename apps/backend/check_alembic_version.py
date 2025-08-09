#!/usr/bin/env python3

from sqlalchemy import text

from database import engine


def check_alembic_version():
    conn = engine.connect()
    try:
        result = conn.execute(text("SELECT * FROM alembic_version;"))
        for row in result:
            print(f"Alembic version in DB: {row[0]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    check_alembic_version()

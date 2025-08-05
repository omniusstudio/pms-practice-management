#!/usr/bin/env python3
"""Database setup script for PMS application."""

import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError as e:
    logger.error(f"psycopg2 not available: {e}")
    logger.error("Please install psycopg2-binary: pip install psycopg2-binary")
    sys.exit(1)

# Database configuration - Use environment variables for security
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "pmsdb")
DB_USER = os.getenv("DB_USER", "omniusstudio")
DB_PASSWORD = os.getenv("DB_PASSWORD")
ADMIN_USER = os.getenv("POSTGRES_USER", "postgres")
ADMIN_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

# Validate required environment variables
if not DB_PASSWORD:
    logger.error("DB_PASSWORD environment variable is required")
    logger.error("Please set: export DB_PASSWORD='your_database_password'")
    sys.exit(1)


def create_database_and_user():
    """Create database and user if they don't exist."""
    logger.info(f"Connecting to PostgreSQL server at {DB_HOST}:{DB_PORT}")

    # Try different connection approaches
    connection_attempts = [
        {"user": ADMIN_USER, "password": ADMIN_PASSWORD, "database": "postgres"},
        {"user": "postgres", "password": "postgres", "database": "postgres"},
        {"user": "postgres", "password": "password", "database": "postgres"},
        {"user": "root", "password": "password", "database": "postgres"},
    ]

    conn = None
    for attempt in connection_attempts:
        try:
            logger.info(f"Trying connection with user: {attempt['user']}")
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=attempt["user"],
                password=attempt["password"],
                database=attempt["database"],
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            logger.info(f"Successfully connected with user: {attempt['user']}")
            break
        except psycopg2.Error as e:
            logger.warning(f"Failed to connect with {attempt['user']}: {e}")
            if conn:
                conn.close()
            conn = None
            continue

    if not conn:
        logger.error("Failed to connect to PostgreSQL with any credentials.")
        return False

    try:
        cursor = conn.cursor()

        # Create database if it doesn't exist
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        if not cursor.fetchone():
            logger.info(f"Creating database {DB_NAME}")
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            logger.info(f"Database {DB_NAME} created successfully")
        else:
            logger.info(f"Database {DB_NAME} already exists")

        # Create user if it doesn't exist
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (DB_USER,))
        if not cursor.fetchone():
            logger.info(f"Creating user {DB_USER}")
            cursor.execute(f"CREATE USER {DB_USER} WITH PASSWORD '{DB_PASSWORD}'")
            logger.info(f"User {DB_USER} created successfully")
        else:
            logger.info(f"User {DB_USER} already exists")

        # Grant privileges
        logger.info(f"Granting privileges to {DB_USER}")
        cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER}")
        logger.info("Privileges granted successfully")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        logger.error(f"Error creating database and user: {e}")
        if conn:
            conn.close()
        return False


def run_init_script():
    """Run the database initialization script."""
    init_script_path = (
        Path(__file__).parent.parent.parent / "scripts" / "db" / "init.sql"
    )

    if not init_script_path.exists():
        logger.warning(f"Init script not found at {init_script_path}")
        return False

    try:
        # Connect to the new database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
        )
        cursor = conn.cursor()

        # Read and execute init script
        logger.info("Running database initialization script")
        with open(init_script_path, "r") as f:
            init_sql = f.read()

        cursor.execute(init_sql)
        conn.commit()

        cursor.close()
        conn.close()

        logger.info("Database initialization completed successfully")
        return True

    except psycopg2.Error as e:
        logger.error(f"Error running init script: {e}")
        return False


def run_migrations():
    """Run Alembic migrations."""
    try:
        import subprocess

        logger.info("Running Alembic migrations")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            logger.info("Migrations completed successfully")
            return True
        else:
            logger.error(f"Migration failed: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        return False


def main():
    """Main setup function."""
    logger.info("=== PMS Database Setup ===")

    # Step 1: Create database and user
    if not create_database_and_user():
        logger.error("Failed to create database and user")
        sys.exit(1)

    # Step 2: Run initialization script
    if not run_init_script():
        logger.error("Failed to run initialization script")
        sys.exit(1)

    # Step 3: Run migrations
    if not run_migrations():
        logger.error("Failed to run migrations")
        sys.exit(1)

    logger.info("=== Database setup completed successfully! ===")
    logger.info(f"Database: {DB_NAME}")
    logger.info(f"Host: {DB_HOST}:{DB_PORT}")
    logger.info(f"User: {DB_USER}")


if __name__ == "__main__":
    main()

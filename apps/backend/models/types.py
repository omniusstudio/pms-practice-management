"""Custom database types for cross-database compatibility."""

import uuid

from sqlalchemy import String, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.engine import Dialect


class UUID(TypeDecorator):
    """Cross-database UUID type that works with both PostgreSQL and SQLite."""

    impl = String
    cache_ok = True

    def __init__(self, as_uuid=False):
        """Initialize UUID type."""
        self.as_uuid = as_uuid
        super().__init__()

    def load_dialect_impl(self, dialect: Dialect):
        """Load appropriate implementation based on database dialect."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PostgresUUID(as_uuid=self.as_uuid))
        else:
            # For SQLite and other databases, use String(36)
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect: Dialect):
        """Process values being sent to the database."""
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return value
        else:
            # For SQLite, convert UUID to string
            if isinstance(value, uuid.UUID):
                return str(value)
            return value

    def process_result_value(self, value, dialect: Dialect):
        """Process values coming from the database."""
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return value
        else:
            # For SQLite, convert string back to UUID
            if isinstance(value, str):
                return uuid.UUID(value)
            return value

"""Common JSON types for SQLAlchemy models."""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import sqltypes


class JSONBType(sqltypes.TypeDecorator):
    """A type that uses JSONB for PostgreSQL and JSON for other databases."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())

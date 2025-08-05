"""Base model class for all database models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import DeclarativeBase

from .types import UUID


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class BaseModel(Base):
    """Abstract base model with common fields."""

    __abstract__ = True

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )

    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Correlation ID for request tracking (HIPAA audit requirement)
    correlation_id = Column(String(255), nullable=True, index=True)

    # Tenant ID for multi-tenancy support
    tenant_id = Column(String(255), nullable=True, index=True)

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary, excluding sensitive fields."""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            elif isinstance(value, uuid.UUID):
                result[column.name] = str(value)
            else:
                result[column.name] = value
        return result

    def __repr__(self) -> str:
        """String representation without PHI."""
        return f"<{self.__class__.__name__}(id={self.id})>"

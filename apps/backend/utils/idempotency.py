"""Idempotency key utilities for HIPAA-compliant API operations.

This module provides utilities for handling idempotency keys to ensure
safe retry of operations without duplicate side effects.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import Header, HTTPException, status
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.ext.declarative import declarative_base

from utils.phi_scrubber import scrub_phi

Base = declarative_base()


class IdempotencyRecord(Base):
    """Database model for storing idempotency records."""

    __tablename__ = "idempotency_records"

    key = Column(String(255), primary_key=True)
    request_hash = Column(String(64), nullable=False)
    response_data = Column(Text, nullable=True)
    status_code = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


class IdempotencyManager:
    """Manager for handling idempotency operations."""

    def __init__(self, db_session, ttl_hours: int = 24):
        """Initialize idempotency manager.

        Args:
            db_session: Database session
            ttl_hours: Time-to-live for idempotency records in hours
        """
        self.db_session = db_session
        self.ttl_hours = ttl_hours

    def _generate_request_hash(self, request_data: Dict[str, Any]) -> str:
        """Generate a hash of the request data for comparison.

        Args:
            request_data: Request data to hash

        Returns:
            str: SHA-256 hash of the request data
        """
        # Scrub PHI before hashing
        scrubbed_data = scrub_phi(json.dumps(request_data, sort_keys=True))
        return hashlib.sha256(scrubbed_data.encode()).hexdigest()

    def check_idempotency(
        self, idempotency_key: str, request_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if an idempotent request has been processed before.

        Args:
            idempotency_key: Unique idempotency key
            request_data: Current request data

        Returns:
            Optional[Dict]: Previous response if found, None otherwise

        Raises:
            HTTPException: If key exists but request data differs
        """
        # Clean up expired records
        self._cleanup_expired_records()

        # Look for existing record
        record = (
            self.db_session.query(IdempotencyRecord)
            .filter(IdempotencyRecord.key == idempotency_key)
            .first()
        )

        if not record:
            return None

        # Check if request data matches
        current_hash = self._generate_request_hash(request_data)
        if record.request_hash != current_hash:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "IDEMPOTENCY_KEY_MISMATCH",
                    "message": ("Idempotency key used with different request data"),
                    "idempotency_key": idempotency_key,
                },
            )

        # Return cached response
        if record.response_data:
            return {
                "data": json.loads(record.response_data),
                "status_code": int(record.status_code),
                "from_cache": True,
            }

        return None

    def store_response(
        self,
        idempotency_key: str,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        status_code: int,
    ) -> None:
        """Store the response for an idempotent operation.

        Args:
            idempotency_key: Unique idempotency key
            request_data: Request data
            response_data: Response data to cache
            status_code: HTTP status code
        """
        request_hash = self._generate_request_hash(request_data)
        expires_at = datetime.utcnow() + timedelta(hours=self.ttl_hours)

        # Scrub PHI from response before storing
        scrubbed_response = scrub_phi(json.dumps(response_data))

        record = IdempotencyRecord(
            key=idempotency_key,
            request_hash=request_hash,
            response_data=scrubbed_response,
            status_code=str(status_code),
            expires_at=expires_at,
        )

        self.db_session.merge(record)
        self.db_session.commit()

    def _cleanup_expired_records(self) -> None:
        """Clean up expired idempotency records."""
        now = datetime.utcnow()
        self.db_session.query(IdempotencyRecord).filter(
            IdempotencyRecord.expires_at < now
        ).delete()
        self.db_session.commit()


def get_idempotency_key(
    idempotency_key: Optional[str] = Header(
        None,
        alias="Idempotency-Key",
        description="Unique key for idempotent operations",
    )
) -> Optional[str]:
    """FastAPI dependency for extracting idempotency key from headers.

    Args:
        idempotency_key: Idempotency key from header

    Returns:
        Optional[str]: Idempotency key if provided

    Raises:
        HTTPException: If idempotency key format is invalid
    """
    if idempotency_key is not None:
        # Validate key format (UUID-like or alphanumeric)
        if not idempotency_key or len(idempotency_key) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_IDEMPOTENCY_KEY",
                    "message": "Idempotency key must be 1-255 characters",
                },
            )

    return idempotency_key


def require_idempotency_key(
    idempotency_key: Optional[str] = Header(
        ...,
        alias="Idempotency-Key",
        description="Required unique key for idempotent operations",
    )
) -> str:
    """FastAPI dependency that requires an idempotency key.

    Args:
        idempotency_key: Required idempotency key from header

    Returns:
        str: Validated idempotency key

    Raises:
        HTTPException: If idempotency key is missing or invalid
    """
    if not idempotency_key or len(idempotency_key) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "MISSING_IDEMPOTENCY_KEY",
                "message": "Idempotency-Key header is required for this operation",
            },
        )

    return idempotency_key

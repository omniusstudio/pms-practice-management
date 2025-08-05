"""Event schemas for HIPAA-compliant event bus system."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventType(str, Enum):
    """Standardized event types for the PMS system."""

    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"

    # Appointment events
    APPOINTMENT_SCHEDULED = "appointment.scheduled"
    APPOINTMENT_UPDATED = "appointment.updated"
    APPOINTMENT_CANCELLED = "appointment.cancelled"
    APPOINTMENT_COMPLETED = "appointment.completed"

    # Payment events
    PAYMENT_PROCESSED = "payment.processed"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_REFUNDED = "payment.refunded"

    # Audit events
    AUDIT_LOG = "audit.log"
    SECURITY_EVENT = "security.event"
    DATA_ACCESS = "data.access"

    # System events
    SYSTEM_ERROR = "system.error"
    SYSTEM_MAINTENANCE = "system.maintenance"


class EventSeverity(str, Enum):
    """Event severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BaseEvent(BaseModel):
    """Base event schema with HIPAA compliance."""

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique event identifier"
    )
    event_type: EventType = Field(..., description="Type of event")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp in UTC"
    )
    correlation_id: str = Field(..., description="Request correlation ID")
    user_id: Optional[str] = Field(
        None, description="User ID (scrubbed if contains PHI)"
    )
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: str = Field(
        ..., description="Resource identifier (scrubbed if contains PHI)"
    )
    environment: str = Field(
        default="development", description="Environment where event occurred"
    )
    version: str = Field(default="1.0", description="Event schema version")
    severity: EventSeverity = Field(
        default=EventSeverity.LOW, description="Event severity level"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional event metadata (PHI-scrubbed)"
    )

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, v):
        """Ensure event_id is a valid UUID string."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("event_id must be a valid UUID")

    @field_validator("correlation_id")
    @classmethod
    def validate_correlation_id(cls, v):
        """Ensure correlation_id is not empty."""
        if not v or not v.strip():
            raise ValueError("correlation_id cannot be empty")
        return v.strip()

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment values."""
        valid_envs = {"development", "staging", "production"}
        if v not in valid_envs:
            raise ValueError(f"environment must be one of {valid_envs}")
        return v

    model_config = ConfigDict(use_enum_values=True)

    def model_dump_json(self, **kwargs):
        """Custom JSON serialization with datetime handling."""
        data = self.model_dump(**kwargs)
        # Convert datetime objects to ISO format
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        import json

        return json.dumps(data)


class CRUDEvent(BaseEvent):
    """Event for CRUD operations."""

    operation: str = Field(
        ..., description="CRUD operation (CREATE, READ, UPDATE, DELETE)"
    )
    changes: Optional[Dict[str, Any]] = Field(
        None, description="Changes made (before/after values, PHI-scrubbed)"
    )

    @field_validator("operation")
    @classmethod
    def validate_operation(cls, v):
        """Validate CRUD operation."""
        valid_ops = {"CREATE", "READ", "UPDATE", "DELETE"}
        if v.upper() not in valid_ops:
            raise ValueError(f"operation must be one of {valid_ops}")
        return v.upper()


class AuthEvent(BaseEvent):
    """Event for authentication operations."""

    auth_type: str = Field(..., description="Authentication type (LOGIN, LOGOUT, etc.)")
    success: bool = Field(..., description="Whether authentication was successful")
    ip_address: Optional[str] = Field(
        None, description="Client IP address (anonymized)"
    )
    user_agent: Optional[str] = Field(None, description="Client user agent (scrubbed)")

    @field_validator("auth_type")
    @classmethod
    def validate_auth_type(cls, v):
        """Validate authentication type."""
        valid_types = {"LOGIN", "LOGOUT", "REFRESH", "RESET_PASSWORD"}
        if v.upper() not in valid_types:
            raise ValueError(f"auth_type must be one of {valid_types}")
        return v.upper()


class SystemEvent(BaseEvent):
    """Event for system-level operations."""

    component: str = Field(..., description="System component that generated event")
    error_code: Optional[str] = Field(None, description="Error code if applicable")
    stack_trace: Optional[str] = Field(None, description="Stack trace (PHI-scrubbed)")

    @field_validator("component")
    @classmethod
    def validate_component(cls, v):
        """Ensure component name is not empty."""
        if not v or not v.strip():
            raise ValueError("component cannot be empty")
        return v.strip()


class BusinessEvent(BaseEvent):
    """Event for business logic operations."""

    business_process: str = Field(..., description="Business process name")
    outcome: str = Field(..., description="Process outcome (SUCCESS, FAILURE, PARTIAL)")
    duration_ms: Optional[int] = Field(
        None, description="Process duration in milliseconds"
    )

    @field_validator("outcome")
    @classmethod
    def validate_outcome(cls, v):
        """Validate business process outcome."""
        valid_outcomes = {"SUCCESS", "FAILURE", "PARTIAL"}
        if v.upper() not in valid_outcomes:
            raise ValueError(f"outcome must be one of {valid_outcomes}")
        return v.upper()

    @field_validator("duration_ms")
    @classmethod
    def validate_duration(cls, v):
        """Ensure duration is non-negative."""
        if v is not None and v < 0:
            raise ValueError("duration_ms must be non-negative")
        return v


# Event type mapping for deserialization
EVENT_TYPE_MAPPING = {
    "crud": CRUDEvent,
    "auth": AuthEvent,
    "system": SystemEvent,
    "business": BusinessEvent,
}


def create_event_from_dict(event_data: Dict[str, Any]) -> BaseEvent:
    """Create appropriate event instance from dictionary.

    Args:
        event_data: Event data dictionary

    Returns:
        Appropriate event instance based on event type

    Raises:
        ValueError: If event type is not recognized
    """
    event_category = event_data.get("metadata", {}).get("category", "base")
    event_class = EVENT_TYPE_MAPPING.get(event_category, BaseEvent)

    return event_class(**event_data)

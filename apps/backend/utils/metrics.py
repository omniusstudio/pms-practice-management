"""Metrics utilities for business logic and custom metrics collection."""

import os
from typing import Optional

from middleware.metrics import (
    record_audit_event,
    record_auth_event,
    record_phi_scrub,
    record_user_action,
)

# Get environment from environment variable
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


def track_crud_operation(
    operation: str, resource_type: str, user_id: Optional[str] = None
):
    """Track CRUD operations for audit and metrics.

    Args:
        operation: CRUD operation (CREATE, READ, UPDATE, DELETE)
        resource_type: Type of resource being operated on
        user_id: ID of user performing operation (optional)
    """
    # Record audit event
    record_audit_event(
        event_type=f"crud_{operation.lower()}",
        resource_type=resource_type,
        environment=ENVIRONMENT,
    )

    # Record user action if user_id provided
    if user_id:
        record_user_action(
            action_type=operation.upper(),
            resource_type=resource_type,
            environment=ENVIRONMENT,
        )


def track_authentication(event_type: str, success: bool, user_id: Optional[str] = None):
    """Track authentication events.

    Args:
        event_type: Type of auth event (LOGIN, LOGOUT, PASSWORD_CHANGE)
        success: Whether the authentication was successful
        user_id: ID of user (optional)
    """
    record_auth_event(event_type=event_type, success=success, environment=ENVIRONMENT)


def track_phi_scrubbing(scrub_type: str, count: int = 1):
    """Track PHI scrubbing operations.

    Args:
        scrub_type: Type of PHI that was scrubbed
        count: Number of scrubbing operations (default: 1)
    """
    for _ in range(count):
        record_phi_scrub(scrub_type=scrub_type, environment=ENVIRONMENT)


def track_business_event(event_type: str, resource_type: str = "system"):
    """Track custom business events.

    Args:
        event_type: Type of business event
        resource_type: Resource type associated with event
    """
    record_user_action(
        action_type=event_type, resource_type=resource_type, environment=ENVIRONMENT
    )


# Decorator for automatic CRUD tracking
def track_crud(operation: str, resource_type: str):
    """Decorator to automatically track CRUD operations.

    Args:
        operation: CRUD operation type
        resource_type: Resource type being operated on
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Execute the function
            result = func(*args, **kwargs)

            # Track the operation
            track_crud_operation(operation, resource_type)

            return result

        return wrapper

    return decorator


# Context manager for tracking operations
class MetricsContext:
    """Context manager for tracking operations with automatic cleanup."""

    def __init__(self, operation: str, resource_type: str):
        self.operation = operation
        self.resource_type = resource_type
        self.start_time = None

    def __enter__(self):
        import time

        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Track the operation
        if exc_type is None:
            # Success
            track_crud_operation(self.operation, self.resource_type)
        else:
            # Error occurred
            track_business_event(f"{self.operation.lower()}_error", self.resource_type)

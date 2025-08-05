"""Centralized logging configuration with PHI scrubbing."""

import logging
from typing import Any, Dict, Optional

import structlog

from utils.phi_scrubber import scrub_phi


def phi_scrubbing_processor(
    logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Processor to scrub PHI from all log entries.

    Args:
        logger: The logger instance
        method_name: The logging method name (info, error, etc.)
        event_dict: The event dictionary to process

    Returns:
        Event dictionary with PHI scrubbed
    """
    # Scrub PHI from all log data using centralized config
    for key, value in event_dict.items():
        if isinstance(value, (str, dict, list)):
            event_dict[key] = scrub_phi(value, use_centralized_config=True)

    return event_dict


def correlation_id_processor(
    logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Processor to ensure correlation_id is present in log entries.

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary to process

    Returns:
        Event dictionary with correlation_id added if missing
    """
    if "correlation_id" not in event_dict:
        # Try to get correlation_id from context or generate one
        try:
            from middleware.correlation import get_correlation_id

            event_dict["correlation_id"] = get_correlation_id()
        except Exception:
            # Fallback to None if correlation_id cannot be determined
            event_dict["correlation_id"] = None

    return event_dict


def immutable_audit_processor(
    logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Processor to mark audit logs as immutable.

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary to process

    Returns:
        Event dictionary with immutable flag for audit events
    """
    # Mark audit logs as immutable for compliance
    audit_events = ["audit_log", "security_audit", "data_access_audit"]
    if event_dict.get("event") in audit_events:
        event_dict["immutable"] = True

    return event_dict


def configure_structured_logging(
    environment: str = "development",
    log_level: str = "INFO",
    enable_json_output: bool = True,
) -> None:
    """Configure structured logging with PHI scrubbing and compliance.

    Args:
        environment: The deployment environment
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR)
        enable_json_output: Whether to output logs in JSON format
    """
    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s",
    )

    # Build processor chain
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        correlation_id_processor,
        phi_scrubbing_processor,
        immutable_audit_processor,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Add appropriate renderer based on environment
    if enable_json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,  # type: ignore
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured structured logger instance.

    Args:
        name: The logger name (typically __name__)

    Returns:
        Configured structured logger
    """
    return structlog.get_logger(name)


class StandardizedLogger:
    """Standardized logger wrapper with common logging patterns."""

    def __init__(self, name: str):
        """Initialize standardized logger.

        Args:
            name: The logger name
        """
        self.logger = get_logger(name)
        self.name = name

    def log_operation_start(
        self, operation: str, correlation_id: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Log the start of an operation.

        Args:
            operation: The operation name
            correlation_id: Request correlation ID
            **kwargs: Additional context data
        """
        self.logger.info(
            f"{operation} started",
            event="operation_start",
            operation=operation,
            correlation_id=correlation_id,
            **kwargs,
        )

    def log_operation_success(
        self,
        operation: str,
        correlation_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        """Log successful completion of an operation.

        Args:
            operation: The operation name
            correlation_id: Request correlation ID
            duration_ms: Operation duration in milliseconds
            **kwargs: Additional context data
        """
        self.logger.info(
            f"{operation} completed successfully",
            event="operation_success",
            operation=operation,
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            **kwargs,
        )

    def log_operation_error(
        self,
        operation: str,
        error: Exception,
        correlation_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        """Log operation failure.

        Args:
            operation: The operation name
            error: The exception that occurred
            correlation_id: Request correlation ID
            duration_ms: Operation duration in milliseconds
            **kwargs: Additional context data
        """
        self.logger.error(
            f"{operation} failed",
            event="operation_error",
            operation=operation,
            error=str(error),
            error_type=type(error).__name__,
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            **kwargs,
        )

    def log_user_action(
        self,
        action: str,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Log user action for audit trail.

        Args:
            action: The user action
            user_id: The user ID
            correlation_id: Request correlation ID
            **kwargs: Additional context data
        """
        self.logger.info(
            f"User action: {action}",
            event="user_action",
            action=action,
            user_id=user_id,
            correlation_id=correlation_id,
            **kwargs,
        )

    def log_security_event(
        self,
        event_type: str,
        success: bool,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Log security-related events.

        Args:
            event_type: The type of security event
            success: Whether the event was successful
            user_id: The user ID
            correlation_id: Request correlation ID
            **kwargs: Additional context data
        """
        level = "info" if success else "warning"
        getattr(self.logger, level)(
            f"Security event: {event_type}",
            event="security_audit",
            event_type=event_type,
            success=success,
            user_id=user_id,
            correlation_id=correlation_id,
            **kwargs,
        )


# Initialize logging configuration on module import
# This can be overridden by calling configure_structured_logging() explicitly
configure_structured_logging()

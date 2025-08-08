"""Sentry error tracking service with HIPAA-compliant PHI scrubbing."""

import logging
import os
from typing import Any, Dict, Optional

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from utils.phi_scrubber import scrub_phi

logger = logging.getLogger(__name__)


class PHIScrubberProcessor:
    """Sentry processor to scrub PHI from error data before sending."""

    @staticmethod
    def scrub_event(
        event: Dict[str, Any], hint: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Scrub PHI from Sentry event data.

        Args:
            event: Sentry event data
            hint: Additional context from Sentry

        Returns:
            Scrubbed event data or None to drop the event
        """
        try:
            # Scrub exception messages
            if "exception" in event and "values" in event["exception"]:
                for exception in event["exception"]["values"]:
                    if "value" in exception:
                        exception["value"] = scrub_phi(exception["value"])

                    # Scrub stack trace frames
                    if (
                        "stacktrace" in exception
                        and "frames" in exception["stacktrace"]
                    ):
                        for frame in exception["stacktrace"]["frames"]:
                            if "vars" in frame:
                                frame["vars"] = scrub_phi(frame["vars"])
                            if "context_line" in frame:
                                frame["context_line"] = scrub_phi(frame["context_line"])
                            if "pre_context" in frame:
                                frame["pre_context"] = [
                                    scrub_phi(line) for line in frame["pre_context"]
                                ]
                            if "post_context" in frame:
                                frame["post_context"] = [
                                    scrub_phi(line) for line in frame["post_context"]
                                ]

            # Scrub request data
            if "request" in event:
                request_data = event["request"]
                if "data" in request_data:
                    request_data["data"] = scrub_phi(request_data["data"])
                if "query_string" in request_data:
                    request_data["query_string"] = scrub_phi(
                        request_data["query_string"]
                    )
                if "headers" in request_data:
                    # Remove sensitive headers
                    sensitive_headers = ["authorization", "cookie", "x-api-key"]
                    for header in sensitive_headers:
                        request_data["headers"].pop(header, None)

            # Scrub user context (anonymize while keeping session tracking)
            if "user" in event:
                user_data = event["user"]
                if "id" in user_data:
                    # Keep user ID for session tracking but anonymize
                    user_data["id"] = f"user_{hash(user_data['id']) % 10000:04d}"
                # Remove other potentially identifying user data
                user_data.pop("email", None)
                user_data.pop("username", None)
                user_data.pop("name", None)

            # Scrub extra context data
            if "extra" in event:
                event["extra"] = scrub_phi(event["extra"])

            # Scrub breadcrumbs
            if "breadcrumbs" in event and "values" in event["breadcrumbs"]:
                for breadcrumb in event["breadcrumbs"]["values"]:
                    if "message" in breadcrumb:
                        breadcrumb["message"] = scrub_phi(breadcrumb["message"])
                    if "data" in breadcrumb:
                        breadcrumb["data"] = scrub_phi(breadcrumb["data"])

            return event

        except Exception as e:
            logger.error(f"Error scrubbing PHI from Sentry event: {e}")
            # Return None to drop the event if scrubbing fails
            return None


class SentryService:
    """Service for configuring and managing Sentry error tracking."""

    def __init__(self):
        self.dsn = os.getenv("SENTRY_DSN")
        self.environment = os.getenv("SENTRY_ENVIRONMENT", "development")
        self.release = os.getenv("SENTRY_RELEASE", "unknown")
        self.traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
        self.profiles_sample_rate = float(
            os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")
        )
        self.initialized = False

    def initialize(self) -> bool:
        """Initialize Sentry with HIPAA-compliant configuration.

        Returns:
            True if initialization successful, False otherwise
        """
        if not self.dsn:
            logger.warning("Sentry DSN not configured, error tracking disabled")
            return False

        try:
            sentry_sdk.init(
                dsn=self.dsn,
                environment=self.environment,
                release=self.release,
                traces_sample_rate=self.traces_sample_rate,
                profiles_sample_rate=self.profiles_sample_rate,
                integrations=[
                    FastApiIntegration(),
                    LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
                    SqlalchemyIntegration(),
                ],
                before_send=PHIScrubberProcessor.scrub_event,
                # Additional HIPAA compliance settings
                send_default_pii=False,  # Never send PII
                attach_stacktrace=True,
                max_breadcrumbs=50,
                debug=self.environment == "development",
            )

            # Set global tags
            sentry_sdk.set_tag("service", "pms-backend")
            sentry_sdk.set_tag("compliance", "hipaa")

            self.initialized = True
            logger.info(f"Sentry initialized for environment: {self.environment}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
            return False

    def capture_exception(
        self,
        exception: Exception,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Capture an exception with additional context.

        Args:
            exception: The exception to capture
            user_id: Anonymous user identifier
            correlation_id: Request correlation ID
            extra_context: Additional context (will be PHI-scrubbed)

        Returns:
            Sentry event ID if captured, None otherwise
        """
        if not self.initialized:
            logger.error("Sentry not initialized, cannot capture exception")
            return None

        try:
            with sentry_sdk.push_scope() as scope:
                # Set user context (anonymized)
                if user_id:
                    scope.set_user({"id": f"user_{hash(user_id) % 10000:04d}"})

                # Set correlation ID for request tracking
                if correlation_id:
                    scope.set_tag("correlation_id", correlation_id)

                # Add extra context (will be scrubbed by processor)
                if extra_context:
                    for key, value in extra_context.items():
                        scope.set_extra(key, value)

                # Capture the exception
                event_id = sentry_sdk.capture_exception(exception)
                logger.info(f"Exception captured by Sentry: {event_id}")
                return event_id

        except Exception as e:
            logger.error(f"Failed to capture exception in Sentry: {e}")
            return None

    def capture_message(
        self,
        message: str,
        level: str = "info",
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Capture a message with additional context.

        Args:
            message: The message to capture (will be PHI-scrubbed)
            level: Message level (debug, info, warning, error, fatal)
            user_id: Anonymous user identifier
            correlation_id: Request correlation ID
            extra_context: Additional context (will be PHI-scrubbed)

        Returns:
            Sentry event ID if captured, None otherwise
        """
        if not self.initialized:
            return None

        try:
            with sentry_sdk.push_scope() as scope:
                # Set user context (anonymized)
                if user_id:
                    scope.set_user({"id": f"user_{hash(user_id) % 10000:04d}"})

                # Set correlation ID
                if correlation_id:
                    scope.set_tag("correlation_id", correlation_id)

                # Add extra context
                if extra_context:
                    for key, value in extra_context.items():
                        scope.set_extra(key, value)

                # Capture the message (will be scrubbed by processor)
                event_id = sentry_sdk.capture_message(scrub_phi(message), level)
                return event_id

        except Exception as e:
            logger.error(f"Failed to capture message in Sentry: {e}")
            return None

    def create_test_event(self) -> Optional[str]:
        """Create a test event for validation.

        Returns:
            Sentry event ID if successful, None otherwise
        """
        try:
            test_exception = Exception(
                "Test exception for Sentry validation - PHI scrubbing test: "
                "John Doe SSN 123-45-6789"
            )
            return self.capture_exception(
                test_exception,
                user_id="test_user_123",
                correlation_id="test_correlation_id",
                extra_context={
                    "test_data": "Patient: Jane Smith, DOB: 1990-01-01",
                    "environment": self.environment,
                    "test_type": "validation",
                },
            )
        except Exception as e:
            logger.error(f"Failed to create test event: {e}")
            return None


# Global Sentry service instance
sentry_service = SentryService()


def get_sentry_service() -> SentryService:
    """Get the global Sentry service instance."""
    return sentry_service

"""Tests for logging configuration utilities."""

import logging
from unittest.mock import Mock, patch

from utils.logging_config import (
    StandardizedLogger,
    configure_structured_logging,
    correlation_id_processor,
    get_logger,
    immutable_audit_processor,
    phi_scrubbing_processor,
)


class TestPhiScrubbingProcessor:
    """Test PHI scrubbing processor."""

    def test_phi_scrubbing_processor_returns_event_dict(self):
        """Test that processor returns the event dictionary."""
        logger = Mock()
        event_dict = {"message": "test", "count": 42}

        result = phi_scrubbing_processor(logger, "info", event_dict)

        assert isinstance(result, dict)
        assert "message" in result
        assert "count" in result

    def test_phi_scrubbing_processor_ignores_non_scrubable_types(self):
        """Test that non-scrubable types are ignored."""
        logger = Mock()
        event_dict = {"count": 42, "active": True, "rate": 3.14}

        result = phi_scrubbing_processor(logger, "info", event_dict)

        assert result["count"] == 42
        assert result["active"] is True
        assert result["rate"] == 3.14


class TestCorrelationIdProcessor:
    """Test correlation ID processor."""

    def test_correlation_id_processor_preserves_existing_id(self):
        """Test that existing correlation_id is preserved."""
        logger = Mock()
        event_dict = {"correlation_id": "existing-id", "message": "test"}

        result = correlation_id_processor(logger, "info", event_dict)

        assert result["correlation_id"] == "existing-id"

    @patch("middleware.correlation.get_correlation_id")
    def test_correlation_id_processor_adds_id_from_context(
        self, mock_get_correlation_id
    ):
        """Test that correlation_id is added from context."""
        mock_get_correlation_id.return_value = "context-id"
        logger = Mock()
        event_dict = {"message": "test"}

        result = correlation_id_processor(logger, "info", event_dict)

        assert result["correlation_id"] == "context-id"

    @patch("middleware.correlation.get_correlation_id")
    def test_correlation_id_processor_handles_exception(self, mock_get_correlation_id):
        """Test that exceptions are handled gracefully."""
        mock_get_correlation_id.side_effect = Exception("Context error")
        logger = Mock()
        event_dict = {"message": "test"}

        result = correlation_id_processor(logger, "info", event_dict)

        assert result["correlation_id"] is None


class TestImmutableAuditProcessor:
    """Test immutable audit processor."""

    def test_immutable_audit_processor_marks_audit_events(self):
        """Test that audit events are marked as immutable."""
        logger = Mock()
        event_dict = {"event": "audit_log", "message": "test"}

        result = immutable_audit_processor(logger, "info", event_dict)

        assert result["immutable"] is True

    def test_immutable_audit_processor_marks_security_audit(self):
        """Test that security audit events are marked as immutable."""
        logger = Mock()
        event_dict = {"event": "security_audit", "message": "test"}

        result = immutable_audit_processor(logger, "info", event_dict)

        assert result["immutable"] is True

    def test_immutable_audit_processor_marks_data_access_audit(self):
        """Test that data access audit events are marked as immutable."""
        logger = Mock()
        event_dict = {"event": "data_access_audit", "message": "test"}

        result = immutable_audit_processor(logger, "info", event_dict)

        assert result["immutable"] is True

    def test_immutable_audit_processor_ignores_non_audit_events(self):
        """Test that non-audit events are not marked as immutable."""
        logger = Mock()
        event_dict = {"event": "regular_log", "message": "test"}

        result = immutable_audit_processor(logger, "info", event_dict)

        assert "immutable" not in result


class TestConfigureStructuredLogging:
    """Test structured logging configuration."""

    @patch("utils.logging_config.logging.basicConfig")
    @patch("utils.logging_config.structlog.configure")
    def test_configure_structured_logging_default_params(
        self, mock_structlog_configure, mock_basic_config
    ):
        """Test configuration with default parameters."""
        configure_structured_logging()

        mock_basic_config.assert_called_once_with(
            level=logging.INFO, format="%(message)s"
        )
        mock_structlog_configure.assert_called_once()

    @patch("utils.logging_config.logging.basicConfig")
    @patch("utils.logging_config.structlog.configure")
    def test_configure_structured_logging_custom_params(
        self, mock_structlog_configure, mock_basic_config
    ):
        """Test configuration with custom parameters."""
        configure_structured_logging(
            environment="production", log_level="ERROR", enable_json_output=False
        )

        mock_basic_config.assert_called_once_with(
            level=logging.ERROR, format="%(message)s"
        )
        mock_structlog_configure.assert_called_once()


class TestGetLogger:
    """Test get_logger function."""

    @patch("utils.logging_config.structlog.get_logger")
    def test_get_logger_returns_structlog_logger(self, mock_structlog_get_logger):
        """Test that get_logger returns a structlog logger."""
        mock_logger = Mock()
        mock_structlog_get_logger.return_value = mock_logger

        result = get_logger("test_logger")

        mock_structlog_get_logger.assert_called_once_with("test_logger")
        assert result == mock_logger


class TestStandardizedLogger:
    """Test StandardizedLogger class."""

    @patch("utils.logging_config.get_logger")
    def test_standardized_logger_initialization(self, mock_get_logger):
        """Test StandardizedLogger initialization."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        std_logger = StandardizedLogger("test_logger")

        mock_get_logger.assert_called_once_with("test_logger")
        assert std_logger.logger == mock_logger
        assert std_logger.name == "test_logger"

    @patch("utils.logging_config.get_logger")
    def test_log_operation_start(self, mock_get_logger):
        """Test log_operation_start method."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        std_logger = StandardizedLogger("test")

        std_logger.log_operation_start(
            "create_patient", correlation_id="123", user_id="user1"
        )

        mock_logger.info.assert_called_once_with(
            "create_patient started",
            event="operation_start",
            operation="create_patient",
            correlation_id="123",
            user_id="user1",
        )

    @patch("utils.logging_config.get_logger")
    def test_log_operation_success(self, mock_get_logger):
        """Test log_operation_success method."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        std_logger = StandardizedLogger("test")

        std_logger.log_operation_success(
            "create_patient", correlation_id="123", duration_ms=150.5
        )

        mock_logger.info.assert_called_once_with(
            "create_patient completed successfully",
            event="operation_success",
            operation="create_patient",
            correlation_id="123",
            duration_ms=150.5,
        )

    @patch("utils.logging_config.get_logger")
    def test_log_operation_error(self, mock_get_logger):
        """Test log_operation_error method."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        std_logger = StandardizedLogger("test")
        error = ValueError("Test error")

        std_logger.log_operation_error(
            "create_patient", error, correlation_id="123", duration_ms=50.0
        )

        mock_logger.error.assert_called_once_with(
            "create_patient failed",
            event="operation_error",
            operation="create_patient",
            error="Test error",
            error_type="ValueError",
            correlation_id="123",
            duration_ms=50.0,
        )

    @patch("utils.logging_config.get_logger")
    def test_log_user_action(self, mock_get_logger):
        """Test log_user_action method."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        std_logger = StandardizedLogger("test")

        std_logger.log_user_action("login", user_id="user1", correlation_id="123")

        mock_logger.info.assert_called_once_with(
            "User action: login",
            event="user_action",
            action="login",
            user_id="user1",
            correlation_id="123",
        )

    @patch("utils.logging_config.get_logger")
    def test_log_security_event_success(self, mock_get_logger):
        """Test log_security_event method for successful events."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        std_logger = StandardizedLogger("test")

        std_logger.log_security_event(
            "authentication", success=True, user_id="user1", correlation_id="123"
        )

        mock_logger.info.assert_called_once_with(
            "Security event: authentication",
            event="security_audit",
            event_type="authentication",
            success=True,
            user_id="user1",
            correlation_id="123",
        )

    @patch("utils.logging_config.get_logger")
    def test_log_security_event_failure(self, mock_get_logger):
        """Test log_security_event method for failed events."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        std_logger = StandardizedLogger("test")

        std_logger.log_security_event(
            "authentication", success=False, user_id="user1", correlation_id="123"
        )

        mock_logger.warning.assert_called_once_with(
            "Security event: authentication",
            event="security_audit",
            event_type="authentication",
            success=False,
            user_id="user1",
            correlation_id="123",
        )

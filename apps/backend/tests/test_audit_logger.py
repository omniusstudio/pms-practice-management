"""Tests for audit logging utilities."""

from unittest.mock import patch

from utils.audit_logger import (
    log_authentication_event,
    log_crud_action,
    log_data_access,
    log_system_event,
)


class TestLogCrudAction:
    """Test CRUD action logging."""

    @patch("utils.audit_logger.logger")
    @patch("utils.audit_logger.scrub_phi")
    @patch("utils.audit_logger.datetime")
    def test_log_crud_action_basic(self, mock_datetime, mock_scrub_phi, mock_logger):
        """Test basic CRUD action logging."""
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00Z"
        mock_scrub_phi.return_value = "scrubbed_data"

        log_crud_action(
            action="create",
            resource="patient",
            user_id="user123",
            correlation_id="corr456",
        )

        mock_logger.info.assert_called_once_with(
            "Audit: CREATE patient",
            event="audit_log",
            audit_action="CREATE",
            resource_type="patient",
            user_id="user123",
            correlation_id="corr456",
            timestamp="2023-01-01T00:00:00Z",
            immutable=True,
        )

    @patch("utils.audit_logger.logger")
    @patch("utils.audit_logger.scrub_phi")
    @patch("utils.audit_logger.datetime")
    def test_log_crud_action_with_resource_id(
        self, mock_datetime, mock_scrub_phi, mock_logger
    ):
        """Test CRUD action logging with resource ID."""
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00Z"
        mock_scrub_phi.return_value = "scrubbed_data"

        log_crud_action(
            action="update",
            resource="patient",
            user_id="user123",
            correlation_id="corr456",
            resource_id="patient789",
        )

        mock_logger.info.assert_called_once_with(
            "Audit: UPDATE patient",
            event="audit_log",
            audit_action="UPDATE",
            resource_type="patient",
            user_id="user123",
            correlation_id="corr456",
            timestamp="2023-01-01T00:00:00Z",
            immutable=True,
            resource_id="patient789",
        )

    @patch("utils.audit_logger.logger")
    @patch("utils.audit_logger.scrub_phi")
    @patch("utils.audit_logger.datetime")
    def test_log_crud_action_with_changes_and_metadata(
        self, mock_datetime, mock_scrub_phi, mock_logger
    ):
        """Test CRUD action logging with changes and metadata."""
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00Z"
        mock_scrub_phi.return_value = "scrubbed_data"

        changes = {"name": "John Doe"}
        metadata = {"source": "web_app"}

        log_crud_action(
            action="update",
            resource="patient",
            user_id="user123",
            correlation_id="corr456",
            changes=changes,
            metadata=metadata,
        )

        # Verify scrub_phi was called for changes and metadata
        assert mock_scrub_phi.call_count == 2
        mock_scrub_phi.assert_any_call(changes)
        mock_scrub_phi.assert_any_call(metadata)

        mock_logger.info.assert_called_once_with(
            "Audit: UPDATE patient",
            event="audit_log",
            audit_action="UPDATE",
            resource_type="patient",
            user_id="user123",
            correlation_id="corr456",
            timestamp="2023-01-01T00:00:00Z",
            immutable=True,
            changes="scrubbed_data",
            metadata="scrubbed_data",
        )


class TestLogAuthenticationEvent:
    """Test authentication event logging."""

    @patch("utils.audit_logger.logger")
    @patch("utils.audit_logger.datetime")
    def test_log_authentication_event_success(self, mock_datetime, mock_logger):
        """Test successful authentication event logging."""
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00Z"

        log_authentication_event(
            event_type="login",
            user_id="user123",
            correlation_id="corr456",
            success=True,
        )

        mock_logger.info.assert_called_once_with(
            "Security: LOGIN SUCCESS",
            auth_event="LOGIN",
            user_id="user123",
            correlation_id="corr456",
            success=True,
            timestamp="2023-01-01T00:00:00Z",
            immutable=True,
        )

    @patch("utils.audit_logger.logger")
    @patch("utils.audit_logger.scrub_phi")
    @patch("utils.audit_logger.datetime")
    def test_log_authentication_event_failure_with_details(
        self, mock_datetime, mock_scrub_phi, mock_logger
    ):
        """Test failed authentication event with details."""
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00Z"
        mock_scrub_phi.return_value = "scrubbed_data"

        log_authentication_event(
            event_type="login",
            user_id="user123",
            correlation_id="corr456",
            success=False,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            failure_reason="Invalid password",
        )

        # Verify scrub_phi was called for sensitive data
        assert mock_scrub_phi.call_count == 3
        mock_scrub_phi.assert_any_call("192.168.1.1")
        mock_scrub_phi.assert_any_call("Mozilla/5.0")
        mock_scrub_phi.assert_any_call("Invalid password")

        mock_logger.info.assert_called_once_with(
            "Security: LOGIN FAILED",
            auth_event="LOGIN",
            user_id="user123",
            correlation_id="corr456",
            success=False,
            timestamp="2023-01-01T00:00:00Z",
            immutable=True,
            client_ip="scrubbed_data",
            user_agent="scrubbed_data",
            failure_reason="scrubbed_data",
        )

    @patch("utils.audit_logger.logger")
    @patch("utils.audit_logger.scrub_phi")
    @patch("utils.audit_logger.datetime")
    def test_log_authentication_event_success_with_client_info(
        self, mock_datetime, mock_scrub_phi, mock_logger
    ):
        """Test successful authentication with client info."""
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00Z"
        mock_scrub_phi.return_value = "scrubbed_data"

        log_authentication_event(
            event_type="logout",
            user_id="user123",
            correlation_id="corr456",
            success=True,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Verify scrub_phi was called for client info
        assert mock_scrub_phi.call_count == 2
        mock_scrub_phi.assert_any_call("192.168.1.1")
        mock_scrub_phi.assert_any_call("Mozilla/5.0")

        mock_logger.info.assert_called_once_with(
            "Security: LOGOUT SUCCESS",
            auth_event="LOGOUT",
            user_id="user123",
            correlation_id="corr456",
            success=True,
            timestamp="2023-01-01T00:00:00Z",
            immutable=True,
            client_ip="scrubbed_data",
            user_agent="scrubbed_data",
        )


class TestLogDataAccess:
    """Test data access logging."""

    @patch("utils.audit_logger.logger")
    @patch("utils.audit_logger.datetime")
    def test_log_data_access_basic(self, mock_datetime, mock_logger):
        """Test basic data access logging."""
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00Z"

        log_data_access(
            user_id="user123",
            correlation_id="corr456",
            resource_type="patient",
            resource_id="patient789",
        )

        mock_logger.info.assert_called_once_with(
            "Data Access: READ patient",
            event="data_access_audit",
            user_id="user123",
            correlation_id="corr456",
            resource_type="patient",
            resource_id="patient789",
            access_type="READ",
            timestamp="2023-01-01T00:00:00Z",
            immutable=True,
        )

    @patch("utils.audit_logger.logger")
    @patch("utils.audit_logger.scrub_phi")
    @patch("utils.audit_logger.datetime")
    def test_log_data_access_with_query_params(
        self, mock_datetime, mock_scrub_phi, mock_logger
    ):
        """Test data access logging with query parameters."""
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00Z"
        mock_scrub_phi.return_value = "scrubbed_params"

        query_params = {"filter": "name=John", "limit": 10}

        log_data_access(
            user_id="user123",
            correlation_id="corr456",
            resource_type="patient",
            resource_id="patient789",
            access_type="search",
            query_params=query_params,
        )

        mock_scrub_phi.assert_called_once_with(query_params)

        mock_logger.info.assert_called_once_with(
            "Data Access: SEARCH patient",
            event="data_access_audit",
            user_id="user123",
            correlation_id="corr456",
            resource_type="patient",
            resource_id="patient789",
            access_type="SEARCH",
            timestamp="2023-01-01T00:00:00Z",
            immutable=True,
            query_params="scrubbed_params",
        )


class TestLogSystemEvent:
    """Test system event logging."""

    @patch("utils.audit_logger.logger")
    @patch("utils.audit_logger.datetime")
    def test_log_system_event_basic(self, mock_datetime, mock_logger):
        """Test basic system event logging."""
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00Z"

        log_system_event(event_type="database_backup", correlation_id="corr456")

        mock_logger.info.assert_called_once_with(
            "System: DATABASE_BACKUP",
            event="system_audit",
            system_event="DATABASE_BACKUP",
            correlation_id="corr456",
            severity="INFO",
            timestamp="2023-01-01T00:00:00Z",
            immutable=True,
        )

    @patch("utils.audit_logger.logger")
    @patch("utils.audit_logger.scrub_phi")
    @patch("utils.audit_logger.datetime")
    def test_log_system_event_with_details_and_severity(
        self, mock_datetime, mock_scrub_phi, mock_logger
    ):
        """Test system event logging with details and custom severity."""
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00Z"
        mock_scrub_phi.return_value = "scrubbed_details"

        details = {"error_code": "DB001", "message": "Connection failed"}

        log_system_event(
            event_type="database_error",
            correlation_id="corr456",
            severity="error",
            details=details,
        )

        mock_scrub_phi.assert_called_once_with(details)

        mock_logger.error.assert_called_once_with(
            "System: DATABASE_ERROR",
            event="system_audit",
            system_event="DATABASE_ERROR",
            correlation_id="corr456",
            severity="ERROR",
            timestamp="2023-01-01T00:00:00Z",
            immutable=True,
            details="scrubbed_details",
        )

    @patch("utils.audit_logger.logger")
    @patch("utils.audit_logger.datetime")
    def test_log_system_event_warning_severity(self, mock_datetime, mock_logger):
        """Test system event logging with warning severity."""
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00Z"

        log_system_event(
            event_type="high_memory_usage", correlation_id="corr456", severity="warning"
        )

        mock_logger.warning.assert_called_once_with(
            "System: HIGH_MEMORY_USAGE",
            event="system_audit",
            system_event="HIGH_MEMORY_USAGE",
            correlation_id="corr456",
            severity="WARNING",
            timestamp="2023-01-01T00:00:00Z",
            immutable=True,
        )

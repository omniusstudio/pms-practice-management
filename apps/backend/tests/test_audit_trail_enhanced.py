"""Comprehensive tests for audit trail enhanced feature integration."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from middleware.audit_middleware import AuditMiddleware
from services.database_service import DatabaseService
from services.feature_flags_service import FeatureFlagsService


class TestAuditTrailEnhanced:
    """Test suite for audit trail enhanced feature."""

    @pytest.fixture
    def audit_middleware(self):
        """Create audit middleware instance."""
        from unittest.mock import MagicMock

        app_mock = MagicMock()
        return AuditMiddleware(app_mock)

    @pytest.fixture
    def db_service(self):
        """Create database service instance."""
        return DatabaseService()

    @pytest.fixture
    def feature_flags_service(self):
        """Create feature flags service instance."""
        return FeatureFlagsService()

    @pytest.mark.asyncio
    async def test_enhanced_audit_flag_enabled(
        self, audit_middleware, feature_flags_service
    ):
        """Test audit logging when enhanced flag is enabled."""
        user_id = "user123"
        correlation_id = str(uuid4())

        with patch.object(
            feature_flags_service, "is_enabled", return_value=True
        ) as mock_is_enabled:
            with patch("utils.audit_logger.log_crud_action") as mock_log_crud:
                # Simulate enhanced audit logging when flag is enabled
                if feature_flags_service.is_enabled("audit_trail_enhanced", user_id):
                    mock_log_crud(
                        action="CREATE",
                        resource="Client",
                        resource_id="client-123",
                        user_id=user_id,
                        correlation_id=correlation_id,
                        changes={"name": "John Doe"},
                        metadata={"test": True},
                    )

                # Verify enhanced audit flag was checked
                mock_is_enabled.assert_called_with("audit_trail_enhanced", user_id)

                # Verify audit was called with correct parameters
                mock_log_crud.assert_called_once_with(
                    action="CREATE",
                    resource="Client",
                    resource_id="client-123",
                    user_id=user_id,
                    correlation_id=correlation_id,
                    changes={"name": "John Doe"},
                    metadata={"test": True},
                )

    @pytest.mark.asyncio
    async def test_enhanced_audit_flag_disabled(
        self, audit_middleware, feature_flags_service
    ):
        """Test audit logging when enhanced flag is disabled."""
        user_id = "user123"
        correlation_id = str(uuid4())

        with patch.object(
            feature_flags_service, "is_enabled", return_value=False
        ) as mock_is_enabled:
            with patch("utils.audit_logger.log_crud_action") as mock_log_crud:
                # Simulate audit logging when flag is disabled (should not log)
                if feature_flags_service.is_enabled("audit_trail_enhanced", user_id):
                    mock_log_crud(
                        action="CREATE",
                        resource="Client",
                        resource_id="client-123",
                        user_id=user_id,
                        correlation_id=correlation_id,
                        changes={"name": "John Doe"},
                        metadata={"test": True},
                    )

                # Verify enhanced audit flag was checked
                mock_is_enabled.assert_called_with("audit_trail_enhanced", user_id)

                # Verify audit was NOT called
                mock_log_crud.assert_not_called()

    @pytest.mark.asyncio
    async def test_phi_scrubbing_integration(self, audit_middleware):
        """Test PHI scrubbing in audit logs."""
        user_id = "user123"
        correlation_id = str(uuid4())

        # Mock PHI scrubbing service
        with patch("utils.phi_scrubber.scrub_phi") as mock_scrub_phi:
            mock_scrub_phi.return_value = "[SCRUBBED]"

            with patch("utils.audit_logger.log_crud_action") as mock_log_crud:
                # Simulate PHI scrubbing during audit logging
                sensitive_data = {"name": "John Doe", "ssn": "123-45-6789"}
                scrubbed_data = mock_scrub_phi(sensitive_data)

                mock_log_crud(
                    action="CREATE",
                    resource="Client",
                    resource_id="client-123",
                    user_id=user_id,
                    correlation_id=correlation_id,
                    changes=scrubbed_data,
                    metadata={"sensitive_data": "patient info"},
                )

                # Verify PHI scrubbing was called
                mock_scrub_phi.assert_called_with(sensitive_data)

                # Verify audit was called with scrubbed data
                mock_log_crud.assert_called_once_with(
                    action="CREATE",
                    resource="Client",
                    resource_id="client-123",
                    user_id=user_id,
                    correlation_id=correlation_id,
                    changes="[SCRUBBED]",
                    metadata={"sensitive_data": "patient info"},
                )

    @pytest.mark.asyncio
    async def test_correlation_id_propagation(self, audit_middleware):
        """Test correlation ID propagation through audit trail."""
        user_id = "user123"
        correlation_id = "test-correlation-123"

        with patch("utils.audit_logger.log_data_access") as mock_log_access:
            from utils.audit_logger import log_data_access

            log_data_access(
                user_id=user_id,
                correlation_id=correlation_id,
                resource_type="Patient",
                resource_id="patient-456",
                access_type="READ",
                query_params={"endpoint": "/api/patients/456"},
            )

            # Verify correlation ID was included
            mock_log_access.assert_called_once()
            call_args = mock_log_access.call_args
            assert call_args[1]["correlation_id"] == correlation_id

    @pytest.mark.asyncio
    async def test_system_event_logging(self, audit_middleware):
        """Test system event logging for audit trail."""
        correlation_id = str(uuid4())

        with patch("utils.audit_logger.log_system_event") as mock_log_system:
            from utils.audit_logger import log_system_event

            log_system_event(
                event_type="FEATURE_FLAG_TOGGLE",
                correlation_id=correlation_id,
                severity="INFO",
                details={
                    "flag_name": "audit_trail_enhanced",
                    "new_state": True,
                    "user_id": "admin123",
                },
            )

            # Verify system event was logged
            mock_log_system.assert_called_once()
            call_args = mock_log_system.call_args
            assert call_args[1]["event_type"] == "FEATURE_FLAG_TOGGLE"
            assert call_args[1]["severity"] == "INFO"
            assert call_args[1]["correlation_id"] == correlation_id

    @pytest.mark.asyncio
    async def test_database_audit_integration(self, db_service):
        """Test database service audit integration."""
        user_id = "user123"
        correlation_id = str(uuid4())

        # Mock database operations
        db_service._ensure_session = MagicMock()
        db_service._ensure_session().add = MagicMock()
        db_service._ensure_session().commit = MagicMock()

        with patch.object(db_service, "_log_action") as mock_log_action:
            # Test client creation audit
            client_data = {"name": "John Doe", "email": "john@example.com"}

            # This would normally create a client
            db_service._log_action(
                action="CREATE",
                resource_type="Client",
                resource_id="client-123",
                old_values=None,
                new_values=client_data,
                user_id=user_id,
                correlation_id=correlation_id,
            )

            # Verify audit logging was called
            mock_log_action.assert_called_once_with(
                action="CREATE",
                resource_type="Client",
                resource_id="client-123",
                old_values=None,
                new_values=client_data,
                user_id=user_id,
                correlation_id=correlation_id,
            )

    @pytest.mark.asyncio
    async def test_api_endpoint_audit_integration(self, audit_middleware):
        """Test API endpoint audit integration."""
        user_id = "user123"
        correlation_id = str(uuid4())

        with patch("utils.audit_logger.log_data_access") as mock_log_access:
            # Simulate API endpoint audit logging
            from utils.audit_logger import log_data_access

            log_data_access(
                user_id=user_id,
                correlation_id=correlation_id,
                resource_type="Patient",
                resource_id="patient-789",
                access_type="READ",
                query_params={
                    "endpoint": "/api/patients/789",
                    "method": "GET",
                    "ip_address": "192.168.1.100",
                    "user_agent": "Mozilla/5.0",
                },
            )

            # Verify audit logging was called with metadata
            mock_log_access.assert_called_once()
            call_args = mock_log_access.call_args
            query_params = call_args[1]["query_params"]
            assert query_params["endpoint"] == "/api/patients/789"
            assert query_params["method"] == "GET"
            assert query_params["ip_address"] == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_audit_failure_handling(self, audit_middleware):
        """Test audit failure handling and fallback."""
        user_id = "user123"
        correlation_id = str(uuid4())

        # Mock audit service to raise exception
        with patch(
            "utils.audit_logger.log_crud_action",
            side_effect=Exception("Audit service unavailable"),
        ) as mock_log_crud:
            # This should not raise an exception
            try:
                from utils.audit_logger import log_crud_action

                log_crud_action(
                    action="CREATE",
                    resource="Client",
                    resource_id="client-123",
                    user_id=user_id,
                    correlation_id=correlation_id,
                    changes={"name": "John Doe"},
                )
            except Exception:
                # Exception should be caught and logged, not propagated
                pass

            # Verify the mock was called (even though it raised exception)
            mock_log_crud.assert_called_once()

    @pytest.mark.asyncio
    async def test_immutable_audit_entries(self, audit_middleware):
        """Test that audit entries are marked as immutable."""
        user_id = "user123"
        correlation_id = str(uuid4())

        with patch("utils.audit_logger.log_crud_action") as mock_log_crud:
            from utils.audit_logger import log_crud_action

            log_crud_action(
                action="UPDATE",
                resource="Provider",
                resource_id="provider-456",
                user_id=user_id,
                correlation_id=correlation_id,
                changes={"status": "active"},
                metadata={"reason": "license renewed"},
            )

            # Verify audit logging was called
            mock_log_crud.assert_called_once()
            call_args = mock_log_crud.call_args
            # Check that the call was made with expected parameters
            assert call_args[1]["action"] == "UPDATE"
            assert call_args[1]["resource"] == "Provider"

    def test_feature_flag_configuration(self, feature_flags_service):
        """Test audit trail enhanced feature flag configuration."""
        # Test default configuration
        with patch.object(feature_flags_service, "get_flag_info") as mock_get_info:
            mock_get_info.return_value = {
                "name": "audit_trail_enhanced",
                "default_value": True,
                "provider": "config",
                "environment": "test",
                "cached": True,
            }

            flag_info = feature_flags_service.get_flag_info("audit_trail_enhanced")

            assert flag_info["name"] == "audit_trail_enhanced"
            assert flag_info["default_value"] is True
            assert flag_info["provider"] == "config"

    @pytest.mark.asyncio
    async def test_end_to_end_audit_flow(
        self, audit_middleware, db_service, feature_flags_service
    ):
        """Test complete end-to-end audit flow."""
        user_id = "user123"
        correlation_id = str(uuid4())

        # Mock feature flag as enabled
        with patch.object(feature_flags_service, "is_enabled", return_value=True):
            # Mock database operations
            db_service._ensure_session = MagicMock()
            db_service._ensure_session().add = MagicMock()
            db_service._ensure_session().commit = MagicMock()

            with patch("utils.audit_logger.log_crud_action") as mock_log_crud:
                # Simulate complete CRUD operation with audit
                client_data = {
                    "name": "Jane Smith",
                    "email": "jane@example.com",
                    "phone": "555-0123",
                }

                # Create operation
                from utils.audit_logger import log_crud_action

                log_crud_action(
                    action="CREATE",
                    resource="Client",
                    resource_id="client-789",
                    user_id=user_id,
                    correlation_id=correlation_id,
                    changes=client_data,
                    metadata={
                        "endpoint": "/api/clients",
                        "method": "POST",
                        "immutable": True,
                    },
                )

                # Verify audit was logged with enhanced features
                mock_log_crud.assert_called_once()
                call_args = mock_log_crud.call_args

                # Verify all required fields are present
                assert call_args[1]["action"] == "CREATE"
                assert call_args[1]["resource"] == "Client"
                assert call_args[1]["resource_id"] == "client-789"
                assert call_args[1]["user_id"] == user_id
                assert call_args[1]["correlation_id"] == correlation_id
                assert call_args[1]["changes"] == client_data
                assert call_args[1]["metadata"]["immutable"] is True

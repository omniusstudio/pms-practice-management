"""Tests for audit middleware functionality."""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.audit_middleware import AuditMiddleware


@pytest.fixture
def app():
    """Create test FastAPI app with audit middleware."""
    app = FastAPI()
    app.add_middleware(AuditMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    @app.post("/patients")
    async def create_patient(data: dict):
        return {"id": "123", "name": data.get("name")}

    @app.get("/patients/{patient_id}")
    async def get_patient(patient_id: str):
        return {"id": patient_id, "name": "Test Patient"}

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestAuditMiddleware:
    """Test cases for audit middleware."""

    @patch("middleware.audit_middleware.log_crud_action")
    @patch("middleware.audit_middleware.is_enabled")
    def test_crud_operation_logging(self, mock_is_enabled, mock_log_crud, client):
        """Test CRUD operations are logged when enhanced audit is enabled."""
        mock_is_enabled.return_value = True

        # Test POST (CREATE)
        response = client.post("/patients", json={"name": "John Doe"})
        assert response.status_code == 200

        # Verify audit logging was called
        mock_log_crud.assert_called()
        call_args = mock_log_crud.call_args
        assert call_args[1]["action"] == "CREATE"
        assert call_args[1]["resource"] == "Patient"
        assert "correlation_id" in call_args[1]

    @patch("middleware.audit_middleware.log_data_access")
    @patch("middleware.audit_middleware.is_enabled")
    def test_data_access_logging(self, mock_is_enabled, mock_log_access, client):
        """Test that data access is logged for GET requests."""
        mock_is_enabled.return_value = True

        # Test GET request
        response = client.get("/patients/123")
        assert response.status_code == 200

        # Verify data access logging was called
        mock_log_access.assert_called()
        call_args = mock_log_access.call_args
        assert call_args[1]["resource_type"] == "Patient"
        assert call_args[1]["resource_id"] == "123"

    @patch("middleware.audit_middleware.log_crud_action")
    @patch("middleware.audit_middleware.is_enabled")
    def test_audit_disabled_no_logging(self, mock_is_enabled, mock_log_crud, client):
        """Test no logging occurs when audit trail is disabled."""
        mock_is_enabled.return_value = False

        # Test POST request
        response = client.post("/patients", json={"name": "John Doe"})
        assert response.status_code == 200

        # Verify no audit logging occurred
        mock_log_crud.assert_not_called()

    @patch("middleware.audit_middleware.log_system_event")
    @patch("middleware.audit_middleware.log_crud_action")
    @patch("middleware.audit_middleware.is_enabled")
    def test_audit_failure_handling(
        self, mock_is_enabled, mock_log_crud, mock_log_system, client
    ):
        """Test audit failures are handled gracefully."""
        mock_is_enabled.return_value = True
        mock_log_crud.side_effect = Exception("Audit failure")

        # Test POST request
        response = client.post("/patients", json={"name": "John Doe"})
        # Request should still succeed
        assert response.status_code == 200

        # Verify system event was logged for the failure
        mock_log_system.assert_called()
        call_args = mock_log_system.call_args
        assert call_args[1]["event_type"] == "AUDIT_FAILURE"
        assert call_args[1]["severity"] == "ERROR"

    @patch("middleware.audit_middleware.log_data_access")
    @patch("middleware.audit_middleware.is_enabled")
    def test_successful_get_requests_skipped(
        self, mock_is_enabled, mock_log_access, client
    ):
        """Test successful GET requests are skipped unless enhanced audit."""
        mock_is_enabled.return_value = False

        # Test GET request
        response = client.get("/test")
        assert response.status_code == 200

        # Verify no data access logging occurred
        mock_log_access.assert_not_called()

    @patch("middleware.audit_middleware.get_correlation_id")
    @patch("middleware.audit_middleware.log_crud_action")
    @patch("middleware.audit_middleware.is_enabled")
    def test_correlation_id_integration(
        self, mock_is_enabled, mock_log_crud, mock_get_correlation, client
    ):
        """Test correlation IDs are properly integrated."""
        mock_is_enabled.return_value = True
        mock_get_correlation.return_value = "test-correlation-123"

        # Test POST request
        response = client.post("/patients", json={"name": "John Doe"})
        assert response.status_code == 200

        # Verify correlation ID was used
        mock_log_crud.assert_called()
        call_args = mock_log_crud.call_args
        assert call_args[1]["correlation_id"] == "test-correlation-123"

    def test_resource_extraction_from_path(self):
        """Test resource extraction from different path patterns."""
        from unittest.mock import Mock

        middleware = AuditMiddleware(None)

        # Create mock request for /patients
        mock_request = Mock()
        mock_request.url.path = "/patients"
        mock_request.method = "GET"
        result = middleware._extract_resource_info(mock_request)
        assert result["resource_type"] == "Patient"
        assert result["is_sensitive"] is True
        assert result["action"] == "read"

        # Create mock request for /patients/123
        mock_request = Mock()
        mock_request.url.path = "/patients/123"
        mock_request.method = "GET"
        result = middleware._extract_resource_info(mock_request)
        assert result["resource_type"] == "Patient"
        assert result["resource_id"] == "123"
        assert result["is_sensitive"] is True

        # Create mock request for unknown path
        mock_request = Mock()
        mock_request.url.path = "/unknown/path"
        mock_request.method = "GET"
        result = middleware._extract_resource_info(mock_request)
        assert result["resource_type"] is None
        assert result["is_sensitive"] is False

    @patch("middleware.audit_middleware.log_crud_action")
    @patch("middleware.audit_middleware.is_enabled")
    def test_immutable_flag_set(self, mock_is_enabled, mock_log_crud, client):
        """Test immutable flag is properly set in audit logs."""
        mock_is_enabled.return_value = True

        # Test POST request
        response = client.post("/patients", json={"name": "John Doe"})
        assert response.status_code == 200

        # Verify immutable flag is set
        mock_log_crud.assert_called()
        call_args = mock_log_crud.call_args
        metadata = call_args[1].get("metadata", {})
        assert metadata.get("immutable") is True

    @patch("middleware.audit_middleware.scrub_phi")
    @patch("middleware.audit_middleware.log_crud_action")
    @patch("middleware.audit_middleware.is_enabled")
    def test_phi_scrubbing_integration(
        self, mock_is_enabled, mock_log_crud, mock_scrub_phi, client
    ):
        """Test PHI scrubbing is integrated into audit logging."""
        mock_is_enabled.return_value = True
        mock_scrub_phi.return_value = {"name": "[SCRUBBED]"}

        # Test POST request with sensitive data
        response = client.post(
            "/patients",
            json={
                "name": "John Doe",
                "ssn": "123-45-6789",
                "email": "john@example.com",
            },
        )
        assert response.status_code == 200

        # Verify PHI scrubbing was called
        mock_scrub_phi.assert_called()

        # Verify audit logging used scrubbed data
        mock_log_crud.assert_called()
        call_args = mock_log_crud.call_args
        assert "changes" in call_args[1]

"""Tests for logging functionality and PHI scrubbing."""

import json
import os
import sys
from unittest.mock import patch

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import after path setup to avoid import errors
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from utils.audit_logger import (  # noqa: E402
    log_authentication_event,
    log_crud_action,
    log_data_access,
)
from utils.phi_scrubber import (  # noqa: E402
    scrub_phi,
    scrub_phi_from_dict,
    scrub_phi_from_string,
)

client = TestClient(app)


class TestCorrelationID:
    """Test correlation ID functionality."""

    def test_correlation_id_generated_for_requests(self):
        """Test that correlation IDs are generated for requests."""
        response = client.get("/")
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        assert "correlation_id" in response.json()

    def test_correlation_id_preserved_from_header(self):
        """Test that existing correlation IDs are preserved."""
        test_correlation_id = "test-12345-abcdef"
        response = client.get("/", headers={"X-Correlation-ID": test_correlation_id})
        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == test_correlation_id
        assert response.json()["correlation_id"] == test_correlation_id

    def test_correlation_id_in_health_endpoints(self):
        """Test correlation IDs are included in health check responses."""
        # Test /health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        assert "correlation_id" in response.json()
        assert "X-Correlation-ID" in response.headers

        # Test /healthz endpoint
        response = client.get("/healthz")
        assert response.status_code == 200
        # Note: healthz doesn't have correlation_id in response body yet
        assert "X-Correlation-ID" in response.headers


class TestPHIScrubbing:
    """Test PHI scrubbing functionality."""

    def test_scrub_ssn_patterns(self):
        """Test SSN scrubbing."""
        text = "Patient SSN is 123-45-6789 and ID is 987654321"
        scrubbed = scrub_phi_from_string(text)
        assert "123-45-6789" not in scrubbed
        assert "987654321" not in scrubbed
        assert "[SSN-REDACTED]" in scrubbed

    def test_scrub_email_patterns(self):
        """Test email scrubbing."""
        text = "Contact patient at john.doe@example.com for follow-up"
        scrubbed = scrub_phi_from_string(text)
        assert "john.doe@example.com" not in scrubbed
        assert "[EMAIL-REDACTED]" in scrubbed

    def test_scrub_phone_patterns(self):
        """Test phone number scrubbing."""
        text = "Patient phone: (555) 123-4567 or 555.123.4567"
        scrubbed = scrub_phi_from_string(text)
        assert "(555) 123-4567" not in scrubbed
        assert "555.123.4567" not in scrubbed
        assert "[PHONE-REDACTED]" in scrubbed

    def test_scrub_medical_record_numbers(self):
        """Test MRN scrubbing."""
        text = "Patient MRN: 123456 and MR 789012"
        scrubbed = scrub_phi_from_string(text)
        assert "MRN: 123456" not in scrubbed
        assert "MR 789012" not in scrubbed
        assert "[MRN-REDACTED]" in scrubbed

    def test_scrub_date_of_birth(self):
        """Test DOB scrubbing."""
        text = "Patient DOB: 01/15/1990 or 1990-01-15"
        scrubbed = scrub_phi_from_string(text)
        assert "01/15/1990" not in scrubbed
        assert "1990-01-15" not in scrubbed
        assert "[DOB-REDACTED]" in scrubbed

    def test_scrub_sensitive_fields_in_dict(self):
        """Test scrubbing of sensitive field names."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "555-1234",
            "user_id": "user_123",  # Should not be scrubbed
            "notes": "Patient has SSN 123-45-6789",  # Content scrubbed
        }
        scrubbed = scrub_phi_from_dict(data)

        assert scrubbed["first_name"] == "[REDACTED]"
        assert scrubbed["last_name"] == "[REDACTED]"
        assert scrubbed["email"] == "[REDACTED]"
        assert scrubbed["phone"] == "[REDACTED]"
        assert scrubbed["user_id"] == "user_123"  # Not sensitive
        assert "123-45-6789" not in scrubbed["notes"]
        assert "[SSN-REDACTED]" in scrubbed["notes"]

    def test_scrub_nested_data_structures(self):
        """Test scrubbing of nested dictionaries and lists."""
        data = {
            "patient": {
                "name": "John Doe",
                "contact": {"email": "john@example.com", "phone": "555-1234"},
            },
            "appointments": [
                {"patient_name": "Jane Smith", "date": "2024-01-15"},
                {"notes": "Patient SSN: 987-65-4321"},
            ],
        }
        scrubbed = scrub_phi(data)

        assert scrubbed["patient"]["name"] == "[REDACTED]"
        assert scrubbed["patient"]["contact"]["email"] == "[REDACTED]"
        assert scrubbed["patient"]["contact"]["phone"] == "[REDACTED]"
        assert "Jane Smith" not in str(scrubbed)
        assert "987-65-4321" not in str(scrubbed)

    def test_centralized_phi_scrubbing(self):
        """Test the centralized PHI scrubbing functionality."""
        event_dict = {
            "event": "Patient John Doe with SSN 123-45-6789 logged in",
            "user_email": "john@example.com",
            "phone_number": "555-1234",
            "user_id": "user_123",
            "correlation_id": "test-123",
        }

        # Test with centralized config
        scrubbed = scrub_phi(event_dict, use_centralized_config=True)

        # SSN should be redacted
        assert "123-45-6789" not in scrubbed["event"]
        assert "[SSN-REDACTED]" in scrubbed["event"]
        # Sensitive fields should be redacted
        assert scrubbed["user_email"] == "[REDACTED]"
        assert scrubbed["phone_number"] == "[REDACTED]"
        # Non-sensitive fields should remain
        assert scrubbed["user_id"] == "user_123"
        assert scrubbed["correlation_id"] == "test-123"


class TestAuditLogging:
    """Test audit logging functionality."""

    @patch("utils.audit_logger.logger")
    def test_crud_action_logging(self, mock_logger):
        """Test CRUD action audit logging."""
        log_crud_action(
            action="CREATE",
            resource="patient",
            user_id="user_123",
            correlation_id="test-correlation-456",
            resource_id="patient_789",
            changes={"status": "active", "name": "John Doe"},
            metadata={"ip_address": "192.168.1.1"},
        )

        # Verify logger.info was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args

        # Check the log message
        assert "Audit: CREATE patient" in call_args[0][0]

        # Check the audit entry structure
        audit_entry = call_args[1]
        # Note: 'event' is now passed as positional argument, not in kwargs
        assert audit_entry["audit_action"] == "CREATE"
        assert audit_entry["resource_type"] == "patient"
        assert audit_entry["user_id"] == "user_123"
        assert audit_entry["correlation_id"] == "test-correlation-456"
        assert audit_entry["resource_id"] == "patient_789"
        assert audit_entry["immutable"] is True

        # Verify PHI scrubbing in changes
        assert "John Doe" not in str(audit_entry["changes"])
        assert audit_entry["changes"]["status"] == "active"

    @patch("utils.audit_logger.logger")
    def test_authentication_event_logging(self, mock_logger):
        """Test authentication event logging."""
        log_authentication_event(
            event_type="LOGIN",
            user_id="user_123",
            correlation_id="test-correlation-789",
            success=True,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0...",
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args

        assert "Security: LOGIN SUCCESS" in call_args[0][0]

        audit_entry = call_args[1]
        assert audit_entry["auth_event"] == "LOGIN"
        assert audit_entry["success"] is True
        assert audit_entry["immutable"] is True

    @patch("utils.audit_logger.logger")
    def test_data_access_logging(self, mock_logger):
        """Test data access logging."""
        log_data_access(
            user_id="user_123",
            correlation_id="test-correlation-abc",
            resource_type="patient",
            resource_id="patient_456",
            access_type="READ",
            query_params={"include": "appointments", "patient_name": "John"},
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args

        assert "Data Access: READ patient" in call_args[0][0]

        audit_entry = call_args[1]
        # Note: 'event' is now passed as positional argument, not in kwargs
        assert audit_entry["access_type"] == "READ"
        assert audit_entry["resource_type"] == "patient"
        assert audit_entry["immutable"] is True

        # Verify PHI scrubbing in query params
        assert "John" not in str(audit_entry["query_params"])


class TestLoggingIntegration:
    """Test end-to-end logging integration."""

    @patch("main.logger")
    def test_request_logging_with_correlation_id(self, mock_logger):
        """Test that requests are logged with correlation IDs."""
        test_correlation_id = "integration-test-123"
        response = client.get("/", headers={"X-Correlation-ID": test_correlation_id})

        assert response.status_code == 200
        assert response.json()["correlation_id"] == test_correlation_id

        # Verify logger was called with correlation ID context
        mock_logger.info.assert_called_with(
            "Health check requested",
            correlation_id=test_correlation_id,
            endpoint="root",
        )

    def test_no_phi_in_error_responses(self):
        """Test that error responses don't contain PHI."""
        # This would test a non-existent endpoint to trigger an error
        response = client.get("/nonexistent")
        assert response.status_code == 404

        # Verify response doesn't contain any PHI patterns
        response_text = response.text
        assert "123-45-6789" not in response_text  # No SSN
        assert "@example.com" not in response_text  # No email
        assert "555-1234" not in response_text  # No phone

    def test_correlation_id_format(self):
        """Test that generated correlation IDs follow expected format."""
        response = client.get("/")
        correlation_id = response.headers["X-Correlation-ID"]

        # Should contain timestamp and random components
        assert len(correlation_id) > 10
        assert "-" in correlation_id

        # Should be unique across requests
        response2 = client.get("/")
        correlation_id2 = response2.headers["X-Correlation-ID"]
        assert correlation_id != correlation_id2


class TestComplianceValidation:
    """Test HIPAA compliance validation."""

    def test_no_phi_patterns_in_logs(self):
        """Validate that common PHI patterns are not present in logs."""
        # This is a spot-check test that would be run against actual log files
        phi_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b",  # Phone
        ]

        # In a real implementation, this would check actual log files
        # For now, we test that our scrubbing functions work correctly
        test_data = {
            "message": (
                "Patient John Doe (SSN: 123-45-6789) contacted at " "john@example.com"
            ),
            "phone": "555-123-4567",
            "notes": "Follow up with patient via (555) 987-6543",
        }

        scrubbed = scrub_phi(test_data)
        scrubbed_str = json.dumps(scrubbed)

        import re

        for pattern in phi_patterns:
            matches = re.findall(pattern, scrubbed_str, re.IGNORECASE)
            assert (
                len(matches) == 0
            ), f"PHI pattern {pattern} found in scrubbed data: {matches}"

    def test_audit_log_immutability_flag(self):
        """Test that audit logs are marked as immutable."""
        with patch("utils.audit_logger.logger") as mock_logger:
            log_crud_action(
                action="UPDATE",
                resource="appointment",
                user_id="user_456",
                correlation_id="test-immutable-123",
            )

            call_args = mock_logger.info.call_args
            audit_entry = call_args[1]
            assert audit_entry["immutable"] is True

    def test_correlation_id_coverage(self):
        """Test that all requests have correlation IDs."""
        endpoints = ["/", "/health", "/healthz"]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert (
                "X-Correlation-ID" in response.headers
            ), f"Missing correlation ID for {endpoint}"
            correlation_id = response.headers["X-Correlation-ID"]
            assert correlation_id is not None
            assert len(correlation_id) > 0

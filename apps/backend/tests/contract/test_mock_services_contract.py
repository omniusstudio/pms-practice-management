"""Contract tests for mock services.

Validates API contracts, request/response schemas, and integration
behavior for EDI, Stripe, and Video mock services.
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path for importing main
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
try:
    from main import app
except ImportError:
    # Fallback for test execution
    import sys

    sys.path.append("/Volumes/external storage /PMS/apps/backend")
    from main import app


class TestEDIServiceContract:
    """Contract tests for EDI mock service."""

    @pytest.fixture
    def client(self):
        """Test client with mock EDI enabled."""
        return TestClient(app)

    @pytest.fixture(autouse=True)
    def enable_mock_edi(self, monkeypatch):
        """Enable mock EDI service for tests."""

        def mock_is_enabled(self):
            return True

        monkeypatch.setattr(
            "utils.feature_flags.FeatureFlags.is_mock_edi_enabled", mock_is_enabled
        )

    def test_submit_claim_contract(self, client):
        """Test EDI claim submission contract."""
        sample_claim_data = {
            "patient_id": "PAT123456",
            "provider_id": "PRV789012",
            "services": [
                {
                    "service_code": "99213",
                    "service_date": "2024-01-15",
                    "amount": 150.00,
                }
            ],
            "claim_amount": 150.00,
            "diagnosis_codes": ["Z00.00"],
        }

        response = client.post("/api/mock/edi/submit-claim", json=sample_claim_data)

        assert response.status_code == 200
        data = response.json()

        # Validate required response fields
        required_fields = [
            "transaction_id",
            "status",
            "ack_code",
            "timestamp",
            "claim_amount",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Validate field types
        assert isinstance(data["transaction_id"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["ack_code"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["claim_amount"], (int, float))

        # Validate status values
        assert data["status"] in ["accepted", "rejected", "pending"]
        assert data["ack_code"] in ["AA", "AE", "AR"]

        # Validate claim amount matches request
        assert data["claim_amount"] == sample_claim_data["claim_amount"]

    def test_submit_claim_rejected_contract(self, client):
        """Test EDI claim rejection contract."""
        # Submit claim with invalid data to trigger rejection
        invalid_claim = {
            "patient_id": "",  # Invalid empty patient ID
            "provider_id": "PRV789012",
            "services": [],
            "claim_amount": 0.00,
            "diagnosis_codes": [],
        }

        response = client.post("/api/mock/edi/submit-claim", json=invalid_claim)

        # Should still return 200 but with rejection status
        assert response.status_code in [200, 400, 422]

        if response.status_code == 200:
            data = response.json()
            # If processed, should contain error information
            if data.get("status") == "rejected":
                assert "error_codes" in data
                assert "error_description" in data
                assert isinstance(data["error_codes"], list)
                assert isinstance(data["error_description"], str)

    def test_get_remittance_contract(self, client):
        """Test EDI remittance retrieval contract."""
        sample_claim_data = {
            "patient_id": "PAT123456",
            "provider_id": "PRV789012",
            "services": [
                {
                    "service_code": "99213",
                    "service_date": "2024-01-15",
                    "amount": 150.00,
                }
            ],
            "claim_amount": 150.00,
            "diagnosis_codes": ["Z00.00"],
        }

        # First submit a claim to get a transaction ID
        submit_response = client.post(
            "/api/mock/edi/submit-claim", json=sample_claim_data
        )
        assert submit_response.status_code == 200

        transaction_id = submit_response.json()["transaction_id"]

        # Get remittance for the transaction
        response = client.get(f"/api/mock/edi/remittance/{transaction_id}")

        assert response.status_code == 200
        data = response.json()

        # Validate required response fields
        required_fields = [
            "remittance_id",
            "transaction_id",
            "status",
            "original_amount",
            "paid_amount",
            "adjustment_amount",
            "check_number",
            "payment_date",
            "timestamp",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Validate field types
        assert isinstance(data["remittance_id"], str)
        assert isinstance(data["transaction_id"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["original_amount"], (int, float))
        assert isinstance(data["paid_amount"], (int, float))
        assert isinstance(data["adjustment_amount"], (int, float))

        # Validate status values
        assert data["status"] in ["paid_full", "paid_partial", "denied"]

        # Validate transaction ID matches
        assert data["transaction_id"] == transaction_id

    def test_get_nonexistent_remittance_contract(self, client):
        """Test EDI remittance retrieval for nonexistent transaction."""
        response = client.get("/api/mock/edi/remittance/NONEXISTENT_TXN")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "correlation_id" in data

    def test_edi_health_contract(self, client):
        """Test EDI service health check contract."""
        response = client.get("/api/mock/edi/health")

        assert response.status_code == 200
        data = response.json()

        # Validate required health fields
        required_fields = ["service", "status", "timestamp", "stats", "uptime_seconds"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        assert data["service"] == "edi_mock"
        assert data["status"] in ["healthy", "unhealthy"]
        assert isinstance(data["stats"], dict)
        assert isinstance(data["uptime_seconds"], int)


class TestStripeServiceContract:
    """Contract tests for Stripe mock service."""

    @pytest.fixture
    def client(self):
        """Test client with mock payments enabled."""
        return TestClient(app)

    @pytest.fixture(autouse=True)
    def enable_mock_payments(self, monkeypatch):
        """Enable mock payments service for tests."""

        def mock_is_enabled(self):
            return True

        monkeypatch.setattr(
            "utils.feature_flags.FeatureFlags." "is_mock_payments_enabled",
            mock_is_enabled,
        )

    def test_create_payment_intent_contract(self, client):
        """Test Stripe payment intent creation contract."""
        sample_payment_intent_request = {
            "amount": 2000,
            "currency": "usd",
            "payment_method_types": ["card"],
            "confirmation_method": "automatic",
            "capture_method": "automatic",
        }

        response = client.post(
            "/api/mock/payments/payment-intents", json=sample_payment_intent_request
        )

        assert response.status_code == 200
        data = response.json()

        # Validate required response fields
        required_fields = [
            "id",
            "object",
            "amount",
            "currency",
            "status",
            "client_secret",
            "created",
            "payment_method_types",
            "confirmation_method",
            "capture_method",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Validate field types and values
        assert isinstance(data["id"], str)
        assert data["id"].startswith("pi_")
        assert data["object"] == "payment_intent"
        assert data["amount"] == sample_payment_intent_request["amount"]
        assert data["currency"] == sample_payment_intent_request["currency"]
        assert isinstance(data["client_secret"], str)
        assert "_secret_" in data["client_secret"]

        # Validate status values
        valid_statuses = [
            "requires_payment_method",
            "requires_confirmation",
            "processing",
            "succeeded",
            "requires_action",
            "canceled",
        ]
        assert data["status"] in valid_statuses

    def test_retrieve_payment_intent_contract(self, client):
        """Test Stripe payment intent retrieval contract."""
        sample_payment_intent_request = {
            "amount": 2000,
            "currency": "usd",
            "payment_method_types": ["card"],
        }

        # First create a payment intent
        create_response = client.post(
            "/api/mock/payments/payment-intents", json=sample_payment_intent_request
        )
        assert create_response.status_code == 200

        payment_intent_id = create_response.json()["id"]

        # Retrieve the payment intent
        response = client.get(f"/api/mock/payments/payment-intents/{payment_intent_id}")

        assert response.status_code == 200
        data = response.json()

        # Should have same basic structure as creation response
        assert data["id"] == payment_intent_id
        assert data["object"] == "payment_intent"
        assert data["amount"] == sample_payment_intent_request["amount"]

    def test_confirm_payment_intent_contract(self, client):
        """Test Stripe payment intent confirmation contract."""
        sample_payment_intent_request = {
            "amount": 2000,
            "currency": "usd",
            "payment_method_types": ["card"],
        }

        # Create payment intent
        create_response = client.post(
            "/api/mock/payments/payment-intents", json=sample_payment_intent_request
        )
        payment_intent_id = create_response.json()["id"]

        # Confirm payment intent
        response = client.post(
            f"/api/mock/payments/payment-intents/{payment_intent_id}/confirm"
        )

        assert response.status_code == 200
        data = response.json()

        # Validate confirmation response
        assert data["id"] == payment_intent_id
        assert data["status"] in ["succeeded", "requires_action", "payment_failed"]

        # If succeeded, should have charges
        if data["status"] == "succeeded":
            assert "charges" in data
            assert isinstance(data["charges"], dict)
            assert "data" in data["charges"]
            assert isinstance(data["charges"]["data"], list)

    def test_create_customer_contract(self, client):
        """Test Stripe customer creation contract."""
        sample_customer_request = {
            "email": "patient@example.com",
            "name": "John Doe",
            "metadata": {"patient_id": "PAT123456"},
        }

        response = client.post(
            "/api/mock/payments/customers", json=sample_customer_request
        )

        assert response.status_code == 200
        data = response.json()

        # Validate required response fields
        required_fields = [
            "id",
            "object",
            "email",
            "name",
            "created",
            "metadata",
            "default_source",
            "subscriptions",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Validate field types and values
        assert isinstance(data["id"], str)
        assert data["id"].startswith("cus_")
        assert data["object"] == "customer"
        assert data["email"] == sample_customer_request["email"]
        assert data["name"] == sample_customer_request["name"]

    def test_payments_health_contract(self, client):
        """Test payments service health check contract."""
        response = client.get("/api/mock/payments/health")

        assert response.status_code == 200
        data = response.json()

        # Validate health response structure
        required_fields = ["service", "status", "timestamp", "stats", "uptime_seconds"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        assert data["service"] == "stripe_mock"
        assert data["status"] in ["healthy", "unhealthy"]


class TestVideoServiceContract:
    """Contract tests for Video mock service."""

    @pytest.fixture
    def client(self):
        """Test client with mock video enabled."""
        return TestClient(app)

    @pytest.fixture(autouse=True)
    def enable_mock_video(self, monkeypatch):
        """Enable mock video service for tests."""

        def mock_is_enabled(self):
            return True

        monkeypatch.setattr(
            "utils.feature_flags.FeatureFlags.is_mock_video_enabled", mock_is_enabled
        )

    def test_create_session_contract(self, client):
        """Test video session creation contract."""
        sample_video_session_request = {
            "session_name": "Patient Consultation",
            "max_participants": 2,
            "recording_enabled": True,
            "metadata": {"appointment_id": "APT123"},
        }

        response = client.post(
            "/api/mock/video/sessions", json=sample_video_session_request
        )

        assert response.status_code == 200
        data = response.json()

        # Validate required response fields
        required_fields = [
            "id",
            "name",
            "status",
            "created_at",
            "max_participants",
            "current_participants",
            "recording_enabled",
            "recording_status",
            "metadata",
            "join_urls",
            "room_token",
            "expires_at",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Validate field types and values
        assert isinstance(data["id"], str)
        assert data["id"].startswith("session_")
        assert data["name"] == sample_video_session_request["session_name"]
        assert data["status"] == "created"
        assert (
            data["max_participants"] == sample_video_session_request["max_participants"]
        )
        assert data["current_participants"] == 0
        assert (
            data["recording_enabled"]
            == sample_video_session_request["recording_enabled"]
        )

        # Validate join URLs structure
        assert isinstance(data["join_urls"], dict)
        assert "provider" in data["join_urls"]
        assert "patient" in data["join_urls"]
        assert isinstance(data["join_urls"]["provider"], str)
        assert isinstance(data["join_urls"]["patient"], str)

    def test_join_session_contract(self, client):
        """Test video session join contract."""
        sample_video_session_request = {
            "session_name": "Patient Consultation",
            "max_participants": 2,
            "recording_enabled": True,
        }

        # Create session first
        create_response = client.post(
            "/api/mock/video/sessions", json=sample_video_session_request
        )
        session_id = create_response.json()["id"]

        # Join session
        join_request = {
            "participant_name": "Dr. Smith",
            "participant_role": "provider",
            "participant_metadata": {"provider_id": "PRV123"},
        }

        response = client.post(
            f"/api/mock/video/sessions/{session_id}/join", json=join_request
        )

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        required_fields = ["participant", "session_status", "recording_status"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Validate participant structure
        participant = data["participant"]
        participant_fields = [
            "id",
            "name",
            "role",
            "status",
            "joined_at",
            "audio_enabled",
            "video_enabled",
            "metadata",
        ]
        for field in participant_fields:
            assert field in participant, f"Missing participant field: {field}"

        assert participant["name"] == join_request["participant_name"]
        assert participant["role"] == join_request["participant_role"]
        assert participant["status"] in ["connected", "connection_failed", "audio_only"]

    def test_get_session_info_contract(self, client):
        """Test video session info retrieval contract."""
        sample_video_session_request = {
            "session_name": "Patient Consultation",
            "max_participants": 2,
            "recording_enabled": True,
        }

        # Create session
        create_response = client.post(
            "/api/mock/video/sessions", json=sample_video_session_request
        )
        session_id = create_response.json()["id"]

        # Get session info
        response = client.get(f"/api/mock/video/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()

        # Should include participants list
        assert "participants" in data
        assert isinstance(data["participants"], list)

        # Should have same basic structure as creation response
        assert data["id"] == session_id
        assert data["name"] == sample_video_session_request["session_name"]

    def test_list_recordings_contract(self, client):
        """Test video recordings listing contract."""
        response = client.get("/api/mock/video/recordings")

        assert response.status_code == 200
        data = response.json()

        # Should return a list
        assert isinstance(data, list)

        # If recordings exist, validate structure
        if data:
            recording = data[0]
            required_fields = [
                "id",
                "session_id",
                "status",
                "started_at",
                "duration_seconds",
                "file_size_mb",
            ]
            for field in required_fields:
                assert field in recording, f"Missing recording field: {field}"

    def test_video_health_contract(self, client):
        """Test video service health check contract."""
        response = client.get("/api/mock/video/health")

        assert response.status_code == 200
        data = response.json()

        # Validate health response structure
        required_fields = ["service", "status", "timestamp", "stats", "uptime_seconds"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        assert data["service"] == "video_mock"
        assert data["status"] in ["healthy", "unhealthy"]

        # Validate stats structure
        stats = data["stats"]
        stats_fields = [
            "total_sessions",
            "active_sessions",
            "recording_sessions",
            "total_recordings",
            "total_participants",
        ]
        for field in stats_fields:
            assert field in stats, f"Missing stats field: {field}"
            assert isinstance(stats[field], int)


class TestMockServicesIntegration:
    """Integration contract tests for mock services."""

    @pytest.fixture
    def client(self):
        """Test client with all mock services enabled."""
        return TestClient(app)

    @pytest.fixture(autouse=True)
    def enable_all_mock_services(self, monkeypatch):
        """Enable all mock services for integration tests."""

        def mock_is_edi_enabled(self):
            return True

        def mock_is_payments_enabled(self):
            return True

        def mock_is_video_enabled(self):
            return True

        monkeypatch.setattr(
            "utils.feature_flags.FeatureFlags." "is_mock_edi_enabled",
            mock_is_edi_enabled,
        )
        monkeypatch.setattr(
            "utils.feature_flags.FeatureFlags." "is_mock_payments_enabled",
            mock_is_payments_enabled,
        )
        monkeypatch.setattr(
            "utils.feature_flags.FeatureFlags." "is_mock_video_enabled",
            mock_is_video_enabled,
        )

    def test_overall_health_contract(self, client):
        """Test overall mock services health check contract."""
        response = client.get("/api/mock/health")

        assert response.status_code == 200
        data = response.json()

        # Validate overall health structure
        assert "timestamp" in data
        assert "services" in data
        assert isinstance(data["services"], dict)

        # Should include all enabled services
        expected_services = ["edi", "payments", "video"]
        for service in expected_services:
            assert service in data["services"]
            service_health = data["services"][service]
            assert "service" in service_health
            assert "status" in service_health
            assert "timestamp" in service_health

    def test_feature_flag_disabled_contract(self, client, monkeypatch):
        """Test contract when feature flags are disabled."""

        # Disable all mock services
        def mock_is_disabled(self):
            return False

        monkeypatch.setattr(
            "utils.feature_flags.FeatureFlags.is_mock_edi_enabled", mock_is_disabled
        )
        monkeypatch.setattr(
            "utils.feature_flags.FeatureFlags." "is_mock_payments_enabled",
            mock_is_disabled,
        )
        monkeypatch.setattr(
            "utils.feature_flags.FeatureFlags." "is_mock_video_enabled",
            mock_is_disabled,
        )

        # All endpoints should return 503 when disabled
        endpoints = [
            "/api/mock/edi/health",
            "/api/mock/payments/health",
            "/api/mock/video/health",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 503
            data = response.json()
            assert "detail" in data
            assert "not enabled" in data["detail"]

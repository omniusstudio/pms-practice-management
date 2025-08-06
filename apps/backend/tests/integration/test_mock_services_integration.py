"""Integration tests for mock services.

These tests verify the integration between mock services and the FastAPI
application, including feature flag behavior, service interactions, and
error handling.
"""

from unittest.mock import patch


class TestMockServicesIntegration:
    """Integration tests for mock services."""

    def test_service_initialization_integration(
        self, client, mock_all_services_enabled
    ):
        """Test that services initialize correctly with feature flags."""
        # Test health endpoints are accessible
        response = client.get("/api/mock/edi/health")
        assert response.status_code == 200
        assert "service" in response.json()

        response = client.get("/api/mock/payments/health")
        assert response.status_code == 200
        assert "service" in response.json()

        response = client.get("/api/mock/video/health")
        assert response.status_code == 200
        assert "service" in response.json()

    def test_feature_flag_disabled_integration(
        self, client, mock_all_services_disabled
    ):
        """Test behavior when all feature flags are disabled."""
        # All endpoints should return 503
        response = client.get("/api/mock/edi/health")
        assert response.status_code == 503

        response = client.get("/api/mock/payments/health")
        assert response.status_code == 503

        response = client.get("/api/mock/video/health")
        assert response.status_code == 503

    def test_edi_service_integration(self, client, mock_all_services_enabled):
        """Test EDI service integration."""
        # Test claim submission
        claim_data = {
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

        response = client.post("/api/mock/edi/submit-claim", json=claim_data)
        assert response.status_code == 200
        assert "transaction_id" in response.json()

        transaction_id = response.json()["transaction_id"]

        # Test remittance retrieval
        response = client.get(f"/api/mock/edi/remittance/{transaction_id}")
        assert response.status_code == 200
        assert "remittance_id" in response.json()

    def test_stripe_service_integration(self, client, mock_all_services_enabled):
        """Test Stripe service integration."""
        # Test payment intent creation
        payment_data = {"amount": 5000, "currency": "usd", "customer_id": "cus_test123"}

        response = client.post("/api/mock/payments/payment-intents", json=payment_data)
        assert response.status_code == 200
        assert "id" in response.json()
        assert response.json()["amount"] == 5000

        # Test customer creation
        customer_data = {"email": "test@example.com", "name": "Test Customer"}

        response = client.post("/api/mock/payments/customers", json=customer_data)
        assert response.status_code == 200
        assert "id" in response.json()
        assert response.json()["email"] == "test@example.com"

    def test_video_service_integration(self, client, mock_all_services_enabled):
        """Test Video service integration."""
        # Test session creation
        session_data = {
            "session_name": "Test Session",
            "max_participants": 10,
            "recording_enabled": True,
        }

        response = client.post("/api/mock/video/sessions", json=session_data)
        assert response.status_code == 200
        assert "id" in response.json()
        assert response.json()["name"] == "Test Session"

        session_id = response.json()["id"]

        # Test joining session
        join_data = {"participant_name": "Test Participant", "role": "participant"}

        response = client.post(
            f"/api/mock/video/sessions/{session_id}/join", json=join_data
        )
        assert response.status_code == 200
        assert "participant" in response.json()
        assert "id" in response.json()["participant"]

    def test_cross_service_interaction_integration(
        self, client, mock_all_services_enabled
    ):
        """Test interactions between different mock services."""
        # Create a customer in Stripe
        customer_data = {"email": "integration@example.com", "name": "Integration Test"}

        stripe_response = client.post(
            "/api/mock/payments/customers", json=customer_data
        )
        assert stripe_response.status_code == 200
        customer_id = stripe_response.json()["id"]

        # Create a payment intent for the customer
        payment_data = {"amount": 10000, "currency": "usd", "customer_id": customer_id}

        payment_response = client.post(
            "/api/mock/payments/payment-intents", json=payment_data
        )
        assert payment_response.status_code == 200
        assert payment_response.json()["customer"] == customer_id

        # Create a video session
        session_data = {
            "session_name": "Payment Consultation",
            "max_participants": 2,
            "recording_enabled": False,
        }

        video_response = client.post("/api/mock/video/sessions", json=session_data)
        assert video_response.status_code == 200

        # All services should be working independently
        assert stripe_response.json()["id"] != video_response.json()["id"]

    def test_error_handling_integration(self, client, mock_all_services_enabled):
        """Test error handling across services."""
        # Test invalid EDI claim
        invalid_claim = {
            "patient_id": "",  # Invalid empty patient_id
            "provider_id": "PRV789012",
            "services": [],  # Empty services
            "claim_amount": -100.00,  # Invalid negative amount
            "diagnosis_codes": [],
        }

        response = client.post("/api/mock/edi/submit-claim", json=invalid_claim)
        assert response.status_code == 422  # Validation error

        # Test invalid Stripe payment
        invalid_payment = {
            "amount": -1000,  # Invalid negative amount
            "currency": "invalid",  # Invalid currency
            "customer_id": "",
        }

        response = client.post(
            "/api/mock/payments/payment-intents", json=invalid_payment
        )
        assert response.status_code == 422  # Validation error

        # Test invalid video session
        invalid_session = {
            "session_name": "",  # Empty name
            "max_participants": -1,  # Invalid negative participants
            "recording_enabled": "not_boolean",  # Invalid boolean
        }

        response = client.post("/api/mock/video/sessions", json=invalid_session)
        assert response.status_code == 422  # Validation error

    @patch("api.mock_services.edi_service")
    async def test_service_dependency_injection_integration(
        self, mock_edi_service, client, mock_all_services_enabled
    ):
        """Test that service dependencies are properly injected."""

        # Mock the service instance with async return
        async def mock_health():
            return {
                "service": "edi_mock",
                "status": "healthy",
                "timestamp": "2024-01-15T10:00:00Z",
                "stats": {"processed_claims": 0, "processed_remittances": 0},
                "uptime_seconds": 3600,
            }

        mock_edi_service.get_service_health = mock_health

        with patch(
            "utils.feature_flags.FeatureFlags." "is_mock_edi_enabled", return_value=True
        ):
            response = client.get("/api/mock/edi/health")
            assert response.status_code == 200

    def test_concurrent_requests_integration(self, client, mock_all_services_enabled):
        """Test handling of concurrent requests to mock services."""
        import threading

        results = []

        def make_request():
            """Make a request to EDI service."""
            claim_data = {
                "patient_id": f"PAT{threading.current_thread().ident}",
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

            response = client.post("/api/mock/edi/submit-claim", json=claim_data)
            results.append(response.status_code)

        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All requests should succeed
        assert len(results) == 5
        assert all(status == 200 for status in results)

    def test_service_state_persistence_integration(
        self, client, mock_all_services_enabled
    ):
        """Test that service state persists across requests."""
        # Submit multiple claims
        for i in range(3):
            claim_data = {
                "patient_id": f"PAT{i:06d}",
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

            response = client.post("/api/mock/edi/submit-claim", json=claim_data)
            assert response.status_code == 200

        # Check health to see if stats accumulated
        health_response = client.get("/api/mock/edi/health")
        assert health_response.status_code == 200

        health_data = health_response.json()
        stats = health_data["stats"]

        # Should have processed claims
        assert stats["processed_claims"] >= 3

    def test_feature_flag_runtime_changes_integration(self, client, monkeypatch):
        """Test behavior when feature flags change at runtime."""
        # Start with service enabled
        monkeypatch.setattr(
            "utils.feature_flags.FeatureFlags." "is_mock_edi_enabled", lambda self: True
        )

        # Should work
        response = client.get("/api/mock/edi/health")
        assert response.status_code == 200

        # Disable service
        monkeypatch.setattr(
            "utils.feature_flags.FeatureFlags." "is_mock_edi_enabled",
            lambda self: False,
        )

        # Should now return 503
        response = client.get("/api/mock/edi/health")
        assert response.status_code == 503

        # Re-enable service
        monkeypatch.setattr(
            "utils.feature_flags.FeatureFlags." "is_mock_edi_enabled", lambda self: True
        )

        # Should work again
        response = client.get("/api/mock/edi/health")
        assert response.status_code == 200

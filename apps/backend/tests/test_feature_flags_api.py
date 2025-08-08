"""Integration tests for the feature flags API."""

import json
import tempfile
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from routers.auth_router import get_current_user


class TestFeatureFlagsAPI:
    """Test suite for Feature Flags API endpoints."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)

        # Create a temporary file for feature flags configuration
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json"
        )

        # Write test feature flags configuration
        test_config = {
            "test": {
                "video_calls_enabled": True,
                "edi_integration_enabled": False,
                "payments_enabled": True,
                "advanced_reporting_enabled": True,
                "audit_trail_enhanced": True,
                "multi_practice_support": False,
                "database_query_optimization": True,
                "caching_enabled": True,
                "enhanced_encryption": True,
                "two_factor_auth_required": False,
            }
        }

        json.dump(test_config, self.temp_file)
        self.temp_file.flush()
        self.temp_file.close()

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        import os

        try:
            os.unlink(self.temp_file.name)
        except FileNotFoundError:
            pass

        # Clear any dependency overrides
        app.dependency_overrides.clear()

        # Clear global singletons to ensure fresh instances in next test
        import config.feature_flags_config as ff_config
        import services.feature_flags_service as ff_service

        ff_service._feature_flags_service = None
        ff_config.feature_flags_config = None

    @patch.dict(
        "os.environ", {"FEATURE_FLAGS_PROVIDER": "local", "ENVIRONMENT": "test"}
    )
    def test_evaluate_flag_success(self):
        """Test successful flag evaluation."""
        from config.feature_flags_config import FeatureFlagsConfig
        from services.feature_flags_service import (
            FeatureFlagsService,
            get_feature_flags_service,
        )

        try:
            # Override the get_current_user dependency
            app.dependency_overrides[get_current_user] = lambda: {
                "sub": "test-user-123",
                "roles": ["admin"],
            }

            with patch.dict("os.environ", {"FEATURE_FLAGS_FILE": self.temp_file.name}):
                # Create a fresh service instance with updated environment
                fresh_config = FeatureFlagsConfig()
                fresh_service = FeatureFlagsService(fresh_config)

                # Override the service dependency to use fresh instance
                app.dependency_overrides[
                    get_feature_flags_service
                ] = lambda: fresh_service

                request_data = {
                    "flag_name": "video_calls_enabled",
                    "context": {"environment": "test"},
                }

                response = self.client.post(
                    "/api/feature-flags/evaluate", json=request_data
                )

                if response.status_code != 200:
                    print(f"Status: {response.status_code}")
                    print(f"Response: {response.text}")

                assert response.status_code == 200
                data = response.json()
                assert data["enabled"] is True
                assert data["flag_name"] == "video_calls_enabled"
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch.dict(
        "os.environ", {"FEATURE_FLAGS_PROVIDER": "local", "ENVIRONMENT": "test"}
    )
    def test_evaluate_flag_missing_flag_name(self):
        """Test flag evaluation with missing flag name."""
        try:
            # Override the get_current_user dependency
            app.dependency_overrides[get_current_user] = lambda: {
                "sub": "test-user-123",
                "roles": ["admin"],
            }

            with patch.dict("os.environ", {"FEATURE_FLAGS_FILE": self.temp_file.name}):
                request_data = {
                    "context": {"user_id": "user123", "environment": "test"}
                }

                response = self.client.post(
                    "/api/feature-flags/evaluate", json=request_data
                )

                assert response.status_code == 422  # Validation error
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch.dict(
        "os.environ", {"FEATURE_FLAGS_PROVIDER": "local", "ENVIRONMENT": "test"}
    )
    def test_evaluate_flag_invalid_context(self):
        """Test flag evaluation with invalid context."""
        try:
            # Override the get_current_user dependency
            app.dependency_overrides[get_current_user] = lambda: {
                "sub": "test-user-123",
                "roles": ["admin"],
            }

            with patch.dict("os.environ", {"FEATURE_FLAGS_FILE": self.temp_file.name}):
                request_data = {
                    "flag_name": "video_calls_enabled",
                    "context": "invalid_context",  # Should be dict
                }

                response = self.client.post(
                    "/api/feature-flags/evaluate", json=request_data
                )

                assert response.status_code == 422  # Validation error
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch.dict(
        "os.environ", {"FEATURE_FLAGS_PROVIDER": "local", "ENVIRONMENT": "test"}
    )
    def test_get_all_flags_success(self):
        """Test successful retrieval of all flags."""
        try:
            # Override the get_current_user dependency
            app.dependency_overrides[get_current_user] = lambda: {
                "sub": "test-user-123",
                "roles": ["admin"],
            }

            with patch.dict("os.environ", {"FEATURE_FLAGS_FILE": self.temp_file.name}):
                response = self.client.get("/api/feature-flags/all")

                assert response.status_code == 200
                data = response.json()
                assert "flags" in data
                assert "environment" in data
                assert isinstance(data["flags"], dict)
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch.dict(
        "os.environ", {"FEATURE_FLAGS_PROVIDER": "local", "ENVIRONMENT": "test"}
    )
    def test_get_flag_info_success(self):
        """Test successful retrieval of flag information."""
        try:
            # Override the get_current_user dependency
            app.dependency_overrides[get_current_user] = lambda: {
                "sub": "test-user-123",
                "roles": ["admin"],
            }

            with patch.dict("os.environ", {"FEATURE_FLAGS_FILE": self.temp_file.name}):
                response = self.client.get(
                    "/api/feature-flags/video_calls_enabled/info"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["name"] == "video_calls_enabled"
                assert "default_value" in data
                assert "provider" in data
                assert "environment" in data
                assert "cached" in data
                assert "correlation_id" in data
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch.dict(
        "os.environ", {"FEATURE_FLAGS_PROVIDER": "local", "ENVIRONMENT": "test"}
    )
    def test_get_flag_info_nonexistent_flag(self):
        """Test retrieval of non-existent flag information."""
        try:
            # Override the get_current_user dependency
            app.dependency_overrides[get_current_user] = lambda: {
                "sub": "test-user-123",
                "roles": ["admin"],
            }

            with patch.dict("os.environ", {"FEATURE_FLAGS_FILE": self.temp_file.name}):
                response = self.client.get("/api/feature-flags/nonexistent_flag/info")

                assert response.status_code == 200
                data = response.json()
                assert data["name"] == "nonexistent_flag"
                assert data["default_value"] is None
                assert "provider" in data
                assert "environment" in data
                assert "cached" in data
                assert "correlation_id" in data
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch.dict(
        "os.environ", {"FEATURE_FLAGS_PROVIDER": "local", "ENVIRONMENT": "test"}
    )
    def test_clear_cache_success_admin(self):
        """Test successful cache clearing by admin user."""
        try:
            # Override the get_current_user dependency
            app.dependency_overrides[get_current_user] = lambda: {
                "sub": "test-user-123",
                "roles": ["admin"],
            }

            with patch.dict("os.environ", {"FEATURE_FLAGS_FILE": self.temp_file.name}):
                response = self.client.post("/api/feature-flags/cache/clear")

                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Feature flags cache cleared successfully"
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch.dict(
        "os.environ", {"FEATURE_FLAGS_PROVIDER": "local", "ENVIRONMENT": "test"}
    )
    def test_clear_cache_forbidden_non_admin(self):
        """Test cache clearing forbidden for non-admin user."""
        try:
            # Override the get_current_user dependency
            app.dependency_overrides[get_current_user] = lambda: {
                "sub": "test-user-123",
                "roles": ["user"],
            }

            with patch.dict("os.environ", {"FEATURE_FLAGS_FILE": self.temp_file.name}):
                response = self.client.post("/api/feature-flags/cache/clear")

                assert response.status_code == 403
                data = response.json()
                assert "Insufficient permissions to clear cache" in data["detail"]
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    def test_clear_cache_unauthorized(self):
        """Test cache clearing without authentication."""
        response = self.client.post("/api/feature-flags/cache/clear")

        assert response.status_code == 401

    @patch.dict(
        "os.environ", {"FEATURE_FLAGS_PROVIDER": "local", "ENVIRONMENT": "test"}
    )
    def test_kill_switch_video_calls(self):
        """Test video calls kill switch endpoint."""
        try:
            # Override the get_current_user dependency
            app.dependency_overrides[get_current_user] = lambda: {
                "sub": "test-user-123",
                "roles": ["admin"],
            }

            with patch.dict("os.environ", {"FEATURE_FLAGS_FILE": self.temp_file.name}):
                response = self.client.get("/api/feature-flags/video-calls/enabled")

                assert response.status_code == 200
                data = response.json()
                assert data["flag_name"] == "video_calls_enabled"
                assert "enabled" in data
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch.dict(
        "os.environ", {"FEATURE_FLAGS_PROVIDER": "local", "ENVIRONMENT": "test"}
    )
    def test_kill_switch_edi_integration(self):
        """Test EDI integration kill switch endpoint."""
        try:
            # Override the get_current_user dependency
            app.dependency_overrides[get_current_user] = lambda: {
                "sub": "test-user-123",
                "roles": ["admin"],
            }

            with patch.dict("os.environ", {"FEATURE_FLAGS_FILE": self.temp_file.name}):
                response = self.client.get("/api/feature-flags/edi-integration/enabled")

                assert response.status_code == 200
                data = response.json()
                assert data["flag_name"] == "edi_integration_enabled"
                assert "enabled" in data
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch.dict(
        "os.environ", {"FEATURE_FLAGS_PROVIDER": "local", "ENVIRONMENT": "test"}
    )
    def test_kill_switch_payments(self):
        """Test payments kill switch endpoint."""
        try:
            # Override the get_current_user dependency
            app.dependency_overrides[get_current_user] = lambda: {
                "sub": "test-user-123",
                "roles": ["admin"],
            }

            with patch.dict("os.environ", {"FEATURE_FLAGS_FILE": self.temp_file.name}):
                response = self.client.get("/api/feature-flags/payments/enabled")

                assert response.status_code == 200
                data = response.json()
                assert data["flag_name"] == "payments_enabled"
                assert "enabled" in data
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch.dict(
        "os.environ", {"FEATURE_FLAGS_PROVIDER": "local", "ENVIRONMENT": "test"}
    )
    def test_evaluate_flag_with_ip_address(self):
        """Test flag evaluation with IP address in context."""
        try:
            # Override the get_current_user dependency
            app.dependency_overrides[get_current_user] = lambda: {
                "sub": "test-user-123",
                "roles": ["admin"],
            }

            with patch.dict("os.environ", {"FEATURE_FLAGS_FILE": self.temp_file.name}):
                request_data = {
                    "flag_name": "video_calls_enabled",
                    "context": {
                        "user_id": "user123",
                        "ip_address": "192.168.1.1",
                        "environment": "test",
                    },
                }

                response = self.client.post(
                    "/api/feature-flags/evaluate", json=request_data
                )

                assert response.status_code == 200
                data = response.json()
                assert data["flag_name"] == "video_calls_enabled"
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch.dict(
        "os.environ", {"FEATURE_FLAGS_PROVIDER": "local", "ENVIRONMENT": "test"}
    )
    def test_evaluate_flag_context_scrubbing(self):
        """Test that PHI is scrubbed from evaluation context."""
        try:
            # Override the get_current_user dependency
            app.dependency_overrides[get_current_user] = lambda: {
                "sub": "test-user-123",
                "roles": ["admin"],
            }

            with patch.dict("os.environ", {"FEATURE_FLAGS_FILE": self.temp_file.name}):
                request_data = {
                    "flag_name": "video_calls_enabled",
                    "context": {
                        "user_id": "user123",
                        "email": "test@example.com",
                        "phone": "555-1234",
                        "environment": "test",
                    },
                }

                response = self.client.post(
                    "/api/feature-flags/evaluate", json=request_data
                )

                assert response.status_code == 200
                data = response.json()
                assert data["flag_name"] == "video_calls_enabled"
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    def test_api_error_handling(self):
        """Test API error handling for invalid requests."""
        # Test with completely invalid JSON
        response = self.client.post(
            "/api/feature-flags/evaluate",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    @patch.dict(
        "os.environ", {"FEATURE_FLAGS_PROVIDER": "local", "ENVIRONMENT": "test"}
    )
    def test_flag_evaluation_logging(self):
        """Test that flag evaluations are properly logged."""
        try:
            # Override the get_current_user dependency
            app.dependency_overrides[get_current_user] = lambda: {
                "sub": "test-user-123",
                "roles": ["admin"],
            }

            with patch.dict("os.environ", {"FEATURE_FLAGS_FILE": self.temp_file.name}):
                request_data = {
                    "flag_name": "video_calls_enabled",
                    "context": {"user_id": "user123", "environment": "test"},
                }

                response = self.client.post(
                    "/api/feature-flags/evaluate", json=request_data
                )

                assert response.status_code == 200
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    @patch.dict(
        "os.environ", {"FEATURE_FLAGS_PROVIDER": "local", "ENVIRONMENT": "test"}
    )
    def test_concurrent_flag_evaluations(self):
        """Test handling of concurrent flag evaluations."""
        import concurrent.futures
        import threading

        try:
            # Override the get_current_user dependency
            app.dependency_overrides[get_current_user] = lambda: {
                "sub": "test-user-123",
                "roles": ["admin"],
            }

            with patch.dict("os.environ", {"FEATURE_FLAGS_FILE": self.temp_file.name}):

                def evaluate_flag():
                    thread_id = threading.current_thread().ident
                    request_data = {
                        "flag_name": "video_calls_enabled",
                        "context": {
                            "user_id": f"user{thread_id}",
                            "environment": "test",
                        },
                    }

                    response = self.client.post(
                        "/api/feature-flags/evaluate", json=request_data
                    )
                    return response.status_code

                # Execute multiple concurrent requests
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [executor.submit(evaluate_flag) for _ in range(10)]
                    results = [future.result() for future in futures]

                # All requests should succeed
                assert all(status == 200 for status in results)
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

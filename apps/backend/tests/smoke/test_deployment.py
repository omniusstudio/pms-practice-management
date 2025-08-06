"""Smoke tests for deployment validation."""

import os

import pytest
import requests  # type: ignore[import]


def get_api_base_url() -> str:
    """Get the API base URL from environment or use default."""
    return os.getenv("API_BASE_URL", "http://localhost:8000")


class TestDeploymentSmoke:
    """Smoke tests to validate deployment health."""

    @pytest.fixture(scope="class")
    def base_url(self) -> str:
        """Get base URL from environment or default to localhost."""
        return os.getenv("API_BASE_URL", "http://localhost:8000")

    @pytest.mark.smoke
    def test_service_is_running(self, base_url: str):
        """Test that the service is running and responding."""
        try:
            response = requests.get(f"{base_url}/healthz", timeout=10)
            assert response.status_code == 200
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Service is not responding: {e}")

    @pytest.mark.smoke
    @pytest.mark.critical
    def test_health_endpoint(self, base_url: str):
        """Test health endpoint returns expected structure."""
        base_url = get_api_base_url()
        response = requests.get(f"{base_url}/healthz", timeout=5)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
        assert data["status"] in ["healthy", "ok"]

    @pytest.mark.smoke
    @pytest.mark.critical
    def test_readiness_endpoint(self, base_url: str):
        """Test readiness endpoint indicates system is ready."""
        response = requests.get(f"{base_url}/readyz", timeout=10)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)

        # Check database connectivity
        if "database" in data:
            assert data["database"] in ["connected", "ok", "healthy"]

    @pytest.mark.smoke
    def test_api_documentation_accessible(self, base_url: str):
        """Test that API documentation is accessible."""
        # Test OpenAPI docs
        base_url = get_api_base_url()
        response = requests.get(f"{base_url}/api/docs", timeout=5)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

        # Test OpenAPI JSON
        base_url = get_api_base_url()
        response = requests.get(f"{base_url}/openapi.json", timeout=5)
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    @pytest.mark.smoke
    @pytest.mark.security
    def test_security_headers(self, base_url: str):
        """Test that security headers are present."""
        response = requests.get(f"{base_url}/healthz", timeout=5)
        assert response.status_code == 200

        headers = response.headers

        # Check for basic security headers (adjust based on middleware)
        expected_headers = [
            "content-type",
            # Add other security headers as configured
        ]

        for header in expected_headers:
            assert header.lower() in [h.lower() for h in headers.keys()]

    @pytest.mark.smoke
    @pytest.mark.hipaa
    def test_unauthorized_access_protection(self, base_url: str):
        """Test that protected endpoints require authentication."""
        protected_endpoints = [
            "/api/patients",
            "/api/appointments",
            "/api/auth/me",
        ]

        for endpoint in protected_endpoints:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            assert (
                response.status_code == 401
            ), f"Endpoint {endpoint} should require authentication"

            # Verify no PHI is exposed in error messages
            if response.headers.get("content-type", "").startswith("application/json"):
                data = response.json()
                error_text = str(data).lower()

                # Check that common PHI terms are not in error messages
                phi_terms = [
                    "patient",
                    "medical",
                    "diagnosis",
                    "treatment",
                    "prescription",
                    "ssn",
                    "social security",
                ]

                for term in phi_terms:
                    assert (
                        term not in error_text
                    ), f"Potential PHI '{term}' found in error response"

    @pytest.mark.smoke
    @pytest.mark.performance
    def test_response_times(self, base_url: str):
        """Test that critical endpoints respond within acceptable time."""
        import time

        endpoints = [
            ("/healthz", 0.1),  # Health check should be very fast
            ("/readyz", 0.5),  # Readiness can be slower (DB check)
            ("/api/docs", 2.0),  # Documentation can be slower
        ]

        for endpoint, max_time in endpoints:
            start_time = time.time()
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            end_time = time.time()

            response_time = end_time - start_time

            assert (
                response.status_code == 200
            ), f"Endpoint {endpoint} returned {response.status_code}"
            assert response_time < max_time, (
                f"Endpoint {endpoint} took {response_time:.3f}s, "
                f"expected < {max_time}s"
            )

    @pytest.mark.smoke
    def test_cors_configuration(self, base_url: str):
        """Test CORS configuration for frontend integration."""
        # Test preflight request
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization",
        }

        response = requests.options(
            f"{base_url}/api/auth/login", headers=headers, timeout=5
        )

        # Should handle CORS preflight
        assert response.status_code in [200, 204]

    @pytest.mark.smoke
    @pytest.mark.critical
    def test_database_connectivity(self, base_url: str):
        """Test database connectivity through readiness endpoint."""
        response = requests.get(f"{base_url}/readyz", timeout=15)

        # If readiness endpoint exists and returns 200,
        # database should be connected
        if response.status_code == 200:
            data = response.json()
            if "database" in data:
                assert data["database"] in [
                    "connected",
                    "ok",
                    "healthy",
                    "up",
                ], f"Database status: {data.get('database')}"

    @pytest.mark.smoke
    def test_environment_configuration(self, base_url: str):
        """Test that environment is properly configured."""
        # Test that we're not accidentally in debug mode in production
        response = requests.get(f"{base_url}/healthz", timeout=5)
        assert response.status_code == 200

        # Check that debug info is not exposed
        data = response.json()
        debug_indicators = ["debug", "traceback", "exception", "stack"]

        response_text = str(data).lower()
        for indicator in debug_indicators:
            assert (
                indicator not in response_text
            ), f"Debug information '{indicator}' found in response"


class TestCriticalPathSmoke:
    """Smoke tests for critical user paths."""

    @pytest.fixture(scope="class")
    def base_url(self) -> str:
        """Get base URL from environment or default to localhost."""
        return os.getenv("API_BASE_URL", "http://localhost:8000")

    @pytest.mark.smoke
    @pytest.mark.critical
    def test_login_endpoint_structure(self, base_url: str):
        """Test login endpoint accepts requests with proper structure."""
        # Test with invalid credentials to check endpoint structure
        response = requests.post(
            f"{base_url}/api/auth/login",
            json={"email": "test@example.com", "password": "invalid"},
            timeout=5,
        )

        # Should return 401 for invalid credentials, not 404 or 500
        assert response.status_code in [401, 422], (
            f"Login endpoint returned unexpected status: " f"{response.status_code}"
        )

        # Should return JSON error
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type

        data = response.json()
        assert "detail" in data or "message" in data

    @pytest.mark.smoke
    @pytest.mark.critical
    def test_patient_endpoints_exist(self, base_url: str):
        """Test that patient endpoints exist (return 401, not 404)."""
        endpoints = [
            "/api/patients",
            "/api/patients/1",  # Specific patient
        ]

        for endpoint in endpoints:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)

            # Should require auth (401), not be missing (404)
            assert response.status_code != 404, f"Endpoint {endpoint} not found (404)"
            assert response.status_code in [401, 403], (
                f"Endpoint {endpoint} returned {response.status_code}, "
                "expected 401/403 for unauthorized access"
            )

    @pytest.mark.smoke
    @pytest.mark.critical
    def test_appointment_endpoints_exist(self, base_url: str):
        """Test that appointment endpoints exist."""
        endpoints = [
            "/api/appointments",
            "/api/appointments/1",  # Specific appointment
        ]

        for endpoint in endpoints:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)

            # Should require auth (401), not be missing (404)
            assert response.status_code != 404, f"Endpoint {endpoint} not found (404)"
            assert response.status_code in [401, 403], (
                f"Endpoint {endpoint} returned {response.status_code}, "
                "expected 401/403 for unauthorized access"
            )

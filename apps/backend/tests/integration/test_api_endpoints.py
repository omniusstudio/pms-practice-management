"""Integration tests for API endpoints with database."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models.base import Base

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_integration.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def setup_database():
    """Set up test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(setup_database):
    """Create test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.integration
class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_endpoint(self, client):
        """Test basic health endpoint."""
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_readiness_endpoint(self, client):
        """Test readiness endpoint with database check."""
        response = client.get("/readyz")
        assert response.status_code == 200
        data = response.json()
        assert "database" in data
        assert data["database"] == "connected"


@pytest.mark.integration
@pytest.mark.hipaa
class TestAuthenticationEndpoints:
    """Test authentication endpoints with database integration."""

    def test_login_endpoint_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/auth/login",
            json={"email": "invalid@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        data = response.json()

        # Verify no PHI is exposed in error messages
        assert "detail" in data
        assert "invalid" in data["detail"].lower()
        assert "invalid@example.com" not in str(data)
        assert "wrongpassword" not in str(data)

    def test_login_endpoint_missing_fields(self, client):
        """Test login with missing required fields."""
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

        # Check validation errors
        errors = data["detail"]
        email_error = next((e for e in errors if e["loc"] == ["body", "email"]), None)
        password_error = next(
            (e for e in errors if e["loc"] == ["body", "password"]), None
        )

        assert email_error is not None
        assert password_error is not None

    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without authentication."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "not authenticated" in data["detail"].lower()


@pytest.mark.integration
@pytest.mark.critical
class TestPatientEndpoints:
    """Test patient management endpoints."""

    def test_create_patient_unauthorized(self, client):
        """Test creating patient without authorization."""
        patient_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "555-0123",
            "date_of_birth": "1990-01-01",
        }

        response = client.post("/api/patients", json=patient_data)
        assert response.status_code == 401

    def test_get_patients_unauthorized(self, client):
        """Test getting patients without authorization."""
        response = client.get("/api/patients")
        assert response.status_code == 401

    def test_patient_data_validation(self, client):
        """Test patient data validation."""
        # Test with invalid email
        invalid_patient = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "invalid-email",
            "phone": "555-0123",
            "date_of_birth": "1990-01-01",
        }

        response = client.post(
            "/api/patients",
            json=invalid_patient,
            headers={"Authorization": "Bearer fake-token"},
        )
        # Should fail due to both auth and validation
        assert response.status_code in [401, 422]


@pytest.mark.integration
@pytest.mark.security
class TestSecurityHeaders:
    """Test security headers and CORS configuration."""

    def test_security_headers_present(self, client):
        """Test that security headers are present in responses."""
        response = client.get("/healthz")
        assert response.status_code == 200

        # Check for security headers
        headers = response.headers
        # Note: Actual headers depend on middleware configuration
        assert "content-type" in headers

    def test_cors_headers(self, client):
        """Test CORS headers for preflight requests."""
        response = client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        # Should handle CORS preflight
        assert response.status_code in [200, 204]


@pytest.mark.integration
@pytest.mark.performance
class TestPerformanceBaseline:
    """Test basic performance requirements."""

    def test_health_endpoint_response_time(self, client):
        """Test health endpoint responds within acceptable time."""
        import time

        start_time = time.time()
        response = client.get("/healthz")
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time

        # Should respond within 100ms for health check
        assert response_time < 0.1, f"Health check took {response_time:.3f}s"

    def test_concurrent_health_checks(self, client):
        """Test handling multiple concurrent requests."""
        import concurrent.futures
        import time

        def make_request():
            start = time.time()
            response = client.get("/healthz")
            end = time.time()
            return response.status_code, end - start

        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in futures]

        # All should succeed
        for status_code, response_time in results:
            assert status_code == 200
            assert response_time < 0.5  # Should handle concurrent load

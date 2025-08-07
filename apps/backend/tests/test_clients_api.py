"""Tests for clients API endpoints."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.clients import get_db, require_read_financial_reports, require_read_ledger
from main import app
from middleware.auth_middleware import require_auth_dependency
from middleware.correlation import get_correlation_id


class TestClientsAPI:
    """Test cases for clients API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock()

    @patch("middleware.auth_middleware.require_auth_dependency")
    def test_list_clients_basic(self, mock_auth, client, mock_authenticated_user):
        """Test basic client listing."""
        # Mock authentication
        mock_auth.return_value = mock_authenticated_user

        with patch("api.clients.get_db") as mock_get_db:
            mock_get_db.return_value = AsyncMock()

            response = client.get("/api/clients/")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "clients" in data["data"]
            assert "total" in data["data"]
            assert "page" in data["data"]
            assert "per_page" in data["data"]

    @patch("middleware.auth_middleware.require_auth_dependency")
    def test_list_clients_with_params(self, mock_auth, client, mock_authenticated_user):
        """Test client listing with parameters."""
        # Mock authentication
        mock_auth.return_value = mock_authenticated_user

        with patch("api.clients.get_db") as mock_get_db:
            mock_get_db.return_value = AsyncMock()

            response = client.get(
                "/api/clients/?page=2&per_page=25&active_only=false&"
                "search=john&include_stats=true"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["page"] == 2
            assert data["data"]["per_page"] == 25

    @patch("middleware.auth_middleware.require_auth_dependency")
    def test_get_client_basic(self, mock_auth, client, mock_authenticated_user):
        """Test getting a single client."""
        # Mock authentication
        mock_auth.return_value = mock_authenticated_user

        client_id = uuid4()

        with patch("api.clients.get_db") as mock_get_db:
            mock_get_db.return_value = AsyncMock()

            response = client.get(f"/api/clients/{client_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    @patch("middleware.auth_middleware.require_auth_dependency")
    def test_get_client_with_includes(self, mock_auth, client, mock_authenticated_user):
        """Test getting a client with optional includes."""
        # Mock authentication
        mock_auth.return_value = mock_authenticated_user

        client_id = uuid4()

        with patch("api.clients.get_db") as mock_get_db:
            mock_get_db.return_value = AsyncMock()

            response = client.get(
                f"/api/clients/{client_id}?include_appointments=true&"
                f"include_notes=true&include_ledger=true"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_get_client_financial_summary(self, client, mock_authenticated_user):
        """Test getting client financial summary."""
        client_id = uuid4()

        # Override dependencies
        app.dependency_overrides[
            require_auth_dependency
        ] = lambda: mock_authenticated_user
        app.dependency_overrides[get_db] = lambda: AsyncMock()
        app.dependency_overrides[require_read_ledger] = lambda: {"user_id": "test-user"}
        app.dependency_overrides[get_correlation_id] = lambda: "test-correlation-id"

        try:
            response = client.get(f"/api/clients/{client_id}/financial-summary")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
        finally:
            # Clean up overrides
            app.dependency_overrides.clear()

    def test_get_financial_dashboard(self, client, mock_authenticated_user):
        """Test getting financial dashboard data."""
        # Override dependencies
        app.dependency_overrides[
            require_auth_dependency
        ] = lambda: mock_authenticated_user
        app.dependency_overrides[get_db] = lambda: AsyncMock()
        app.dependency_overrides[require_read_financial_reports] = lambda: {
            "user_id": "test-user"
        }
        app.dependency_overrides[get_correlation_id] = lambda: "test-correlation-id"

        try:
            response = client.get(
                "/api/clients/dashboard/financial?date_from=2024-01-01&"
                "date_to=2024-12-31"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
        finally:
            # Clean up overrides
            app.dependency_overrides.clear()

    @patch("middleware.auth_middleware.require_auth_dependency")
    def test_get_performance_stats(self, mock_auth, client, mock_authenticated_user):
        """Test getting performance statistics."""
        # Mock authentication
        mock_auth.return_value = mock_authenticated_user

        with patch("api.clients.get_db") as mock_get_db:
            mock_get_db.return_value = AsyncMock()

            response = client.get("/api/clients/performance/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    @patch("middleware.auth_middleware.require_auth_dependency")
    def test_list_clients_pagination_validation(
        self, mock_auth, client, mock_authenticated_user
    ):
        """Test pagination parameter validation."""
        # Mock authentication
        mock_auth.return_value = mock_authenticated_user

        with patch("api.clients.get_db") as mock_get_db:
            mock_get_db.return_value = AsyncMock()

            # Test invalid page number
            response = client.get("/api/clients/?page=0")
            assert response.status_code == 422

            # Test invalid per_page
            response = client.get("/api/clients/?per_page=0")
            assert response.status_code == 422

            # Test per_page too large
            response = client.get("/api/clients/?per_page=101")
            assert response.status_code == 422

    @patch("middleware.auth_middleware.require_auth_dependency")
    def test_get_client_invalid_uuid(self, mock_auth, client, mock_authenticated_user):
        """Test getting client with invalid UUID."""
        # Mock authentication
        mock_auth.return_value = mock_authenticated_user

        with patch("api.clients.get_db") as mock_get_db:
            mock_get_db.return_value = AsyncMock()

            response = client.get("/api/clients/invalid-uuid")
            assert response.status_code == 422

    def test_financial_dashboard_missing_params(self, client, mock_authenticated_user):
        """Test financial dashboard with missing required parameters."""
        # Override dependencies
        app.dependency_overrides[
            require_auth_dependency
        ] = lambda: mock_authenticated_user
        app.dependency_overrides[get_db] = lambda: AsyncMock()
        app.dependency_overrides[require_read_financial_reports] = lambda: {
            "user_id": "test-user"
        }
        app.dependency_overrides[get_correlation_id] = lambda: "test-correlation-id"

        try:
            # Missing both date_from and date_to parameters
            response = client.get("/api/clients/dashboard/financial")
            assert response.status_code == 422

            # Missing date_from
            response = client.get("/api/clients/dashboard/financial?date_to=2024-12-31")
            assert response.status_code == 422

            # Missing date_to
            response = client.get(
                "/api/clients/dashboard/financial?date_from=2024-01-01"
            )
            assert response.status_code == 422
        finally:
            # Clean up overrides
            app.dependency_overrides.clear()

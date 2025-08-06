"""Tests for clients API endpoints."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app


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

    def test_list_clients_basic(self, client):
        """Test basic client listing."""
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

    def test_list_clients_with_params(self, client):
        """Test client listing with parameters."""
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

    def test_get_client_basic(self, client):
        """Test getting a single client."""
        client_id = uuid4()

        with patch("api.clients.get_db") as mock_get_db:
            mock_get_db.return_value = AsyncMock()

            response = client.get(f"/api/clients/{client_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_get_client_with_includes(self, client):
        """Test getting a client with optional includes."""
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

    def test_get_client_financial_summary(self, client):
        """Test getting client financial summary."""
        client_id = uuid4()

        with patch("api.clients.get_db") as mock_get_db, patch(
            "api.clients.require_read_ledger"
        ) as mock_auth:
            mock_get_db.return_value = AsyncMock()
            mock_auth.return_value = {"user_id": "test-user"}

            response = client.get(f"/api/clients/{client_id}/financial-summary")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_get_financial_dashboard(self, client):
        """Test getting financial dashboard data."""
        with patch("api.clients.get_db") as mock_get_db, patch(
            "api.clients.require_read_financial_reports"
        ) as mock_auth:
            mock_get_db.return_value = AsyncMock()
            mock_auth.return_value = {"user_id": "test-user"}

            response = client.get(
                "/api/clients/dashboard/financial?date_from=2024-01-01&"
                "date_to=2024-12-31"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_get_performance_stats(self, client):
        """Test getting performance statistics."""
        with patch("api.clients.get_db") as mock_get_db:
            mock_get_db.return_value = AsyncMock()

            response = client.get("/api/clients/performance/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_list_clients_pagination_validation(self, client):
        """Test pagination parameter validation."""
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

    def test_get_client_invalid_uuid(self, client):
        """Test getting client with invalid UUID."""
        with patch("api.clients.get_db") as mock_get_db:
            mock_get_db.return_value = AsyncMock()

            response = client.get("/api/clients/invalid-uuid")
            assert response.status_code == 422

    def test_financial_dashboard_missing_params(self, client):
        """Test financial dashboard with missing required parameters."""
        with patch("api.clients.get_db") as mock_get_db, patch(
            "api.clients.require_read_financial_reports"
        ) as mock_auth:
            mock_get_db.return_value = AsyncMock()
            mock_auth.return_value = {"user_id": "test-user"}

            # Missing date_from
            response = client.get("/api/clients/dashboard/financial?date_to=2024-12-31")
            assert response.status_code == 422

            # Missing date_to
            response = client.get(
                "/api/clients/dashboard/financial?date_from=2024-01-01"
            )
            assert response.status_code == 422

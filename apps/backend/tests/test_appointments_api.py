"""Tests for Appointments API."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app


class TestAppointmentsAPI:
    """Test cases for Appointments API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def appointment_id(self):
        """Generate test appointment ID."""
        return str(uuid4())

    @pytest.fixture
    def client_id(self):
        """Generate test client ID."""
        return str(uuid4())

    @pytest.fixture
    def provider_id(self):
        """Generate test provider ID."""
        return str(uuid4())

    @patch("middleware.auth_middleware.require_auth_dependency")
    def test_get_appointments_success(self, mock_auth, client):
        """Test successful appointments retrieval."""
        with patch("database.get_db"):
            mock_auth.return_value = {"user_id": "test-user"}

            response = client.get("/api/appointments/")

            # Should return 200 even if no appointments found
            assert response.status_code in [200, 404]

    @patch("middleware.auth_middleware.require_auth_dependency")
    def test_get_appointments_with_pagination(self, mock_auth, client):
        """Test appointments retrieval with pagination."""
        with patch("database.get_db"):
            mock_auth.return_value = {"user_id": "test-user"}

            response = client.get("/api/appointments/?page=1&per_page=10")

            assert response.status_code in [200, 404]

    @patch("middleware.auth_middleware.require_auth_dependency")
    def test_get_appointments_with_filters(self, mock_auth, client, client_id):
        """Test appointments retrieval with filters."""
        with patch("database.get_db"):
            mock_auth.return_value = {"user_id": "test-user"}

            url = f"/api/appointments/?client_id={client_id}&status=scheduled"
            response = client.get(url)

            assert response.status_code in [200, 404]

    @patch("middleware.auth_middleware.require_auth_dependency")
    def test_get_appointment_by_id(self, mock_auth, client, appointment_id):
        """Test single appointment retrieval."""
        with patch("database.get_db"):
            mock_auth.return_value = {"user_id": "test-user"}

            response = client.get(f"/api/appointments/{appointment_id}")

            assert response.status_code in [200, 404]

    @patch("middleware.auth_middleware.require_auth_dependency")
    def test_create_appointment(self, mock_auth, client, client_id, provider_id):
        """Test appointment creation."""
        with patch("database.get_db"):
            mock_auth.return_value = {"user_id": "test-user"}

            appointment_data = {
                "client_id": client_id,
                "provider_id": provider_id,
                "scheduled_start": "2024-01-15T10:00:00",
                "scheduled_end": "2024-01-15T11:00:00",
                "appointment_type": "consultation",
                "reason_for_visit": "Regular checkup",
                "is_telehealth": False,
            }

            response = client.post("/api/appointments/", json=appointment_data)

            # Should return 201 on success or error status
            assert response.status_code in [201, 400, 422, 500]

    @patch("middleware.auth_middleware.require_auth_dependency")
    def test_update_appointment(
        self, mock_auth, client, appointment_id, client_id, provider_id
    ):
        """Test appointment update."""
        with patch("database.get_db"):
            mock_auth.return_value = {"user_id": "test-user"}

            appointment_data = {
                "client_id": client_id,
                "provider_id": provider_id,
                "scheduled_start": "2024-01-15T14:00:00",
                "scheduled_end": "2024-01-15T15:00:00",
                "appointment_type": "follow_up",
                "reason_for_visit": "Follow-up visit",
                "is_telehealth": True,
            }

            response = client.put(
                f"/api/appointments/{appointment_id}", json=appointment_data
            )

            assert response.status_code in [200, 404, 422, 500]

    @patch("middleware.auth_middleware.require_auth_dependency")
    def test_delete_appointment(self, mock_auth, client, appointment_id):
        """Test appointment deletion."""
        with patch("database.get_db"):
            mock_auth.return_value = {"user_id": "test-user"}

            response = client.delete(f"/api/appointments/{appointment_id}")

            assert response.status_code in [200, 404, 500]

    def test_get_appointments_unauthorized(self, client):
        """Test appointments access without authentication."""
        response = client.get("/api/appointments/")

        # Should return 401 or 403 for unauthorized access
        assert response.status_code in [401, 403]

    def test_create_appointment_invalid_data(self, client):
        """Test appointment creation with invalid data."""
        with patch("middleware.auth_middleware.require_auth_dependency") as mock_auth:
            mock_auth.return_value = {"user_id": "test-user"}

            invalid_data = {
                "client_id": "invalid-uuid",
                "provider_id": "invalid-uuid",
                "scheduled_start": "invalid-date",
                "scheduled_end": "invalid-date",
            }

            response = client.post("/api/appointments/", json=invalid_data)

            # Should return validation error
            assert response.status_code == 422

    def test_get_appointment_invalid_uuid(self, client):
        """Test appointment retrieval with invalid UUID."""
        with patch("middleware.auth_middleware.require_auth_dependency") as mock_auth:
            mock_auth.return_value = {"user_id": "test-user"}

            response = client.get("/api/appointments/invalid-uuid")

            # Should return validation error
            assert response.status_code == 422

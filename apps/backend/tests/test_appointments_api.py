"""Tests for appointments API endpoints."""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app  # noqa: E402


class TestAppointmentsAPI:
    """Test class for appointment API endpoints."""

    def test_get_appointments_success(self, client, mock_authenticated_user):
        """Test successful retrieval of appointments."""
        from api.appointments import get_db
        from middleware.auth_middleware import require_auth_dependency
        from middleware.correlation import get_correlation_id

        # Override dependencies
        app.dependency_overrides[
            require_auth_dependency
        ] = lambda: mock_authenticated_user
        app.dependency_overrides[get_db] = lambda: AsyncMock()
        app.dependency_overrides[get_correlation_id] = lambda: "test-correlation-id"

        try:
            response = client.get("/api/appointments/")

            assert response.status_code == 200
            data = response.json()
            assert "success" in data
            assert data["success"] is True
            assert "data" in data
            assert data["data"] == []
            assert "correlation_id" in data
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    def test_get_appointments_with_pagination(self, client, mock_authenticated_user):
        """Test appointments retrieval with pagination."""
        from api.appointments import get_db
        from middleware.auth_middleware import require_auth_dependency
        from middleware.correlation import get_correlation_id

        # Mock database
        mock_db = AsyncMock()

        # Mock query result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # Override dependencies
        app.dependency_overrides[
            require_auth_dependency
        ] = lambda: mock_authenticated_user
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_correlation_id] = lambda: "test-correlation-id"

        try:
            response = client.get("/api/appointments/?page=1&page_size=10")
            assert response.status_code == 200
            data = response.json()
            assert "pagination" in data
            assert data["pagination"]["page"] == 1
            assert data["pagination"]["per_page"] == 10
        finally:
            # Clean up overrides
            app.dependency_overrides.clear()

    def test_get_appointments_with_filters(self, client, mock_authenticated_user):
        """Test appointments retrieval with filters."""
        from api.appointments import get_db
        from middleware.auth_middleware import require_auth_dependency
        from middleware.correlation import get_correlation_id

        # Mock database
        mock_db = AsyncMock()

        # Mock query result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # Override dependencies
        app.dependency_overrides[
            require_auth_dependency
        ] = lambda: mock_authenticated_user
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_correlation_id] = lambda: "test-correlation-id"

        try:
            client_id = str(uuid4())
            response = client.get(
                f"/api/appointments/?client_id={client_id}&status=scheduled"
            )
            assert response.status_code == 200
        finally:
            # Clean up overrides
            app.dependency_overrides.clear()

    def test_get_appointment_by_id(self, client, mock_authenticated_user):
        """Test retrieval of a specific appointment by ID."""
        from api.appointments import get_db
        from middleware.auth_middleware import require_auth_dependency
        from middleware.correlation import get_correlation_id

        # Mock database
        mock_db = AsyncMock()

        # Mock appointment object
        mock_appointment = AsyncMock()
        mock_appointment.id = uuid4()
        mock_appointment.client_id = uuid4()
        mock_appointment.provider_id = uuid4()
        mock_appointment.scheduled_start = datetime.now(timezone.utc)
        mock_appointment.scheduled_end = datetime.now(timezone.utc)
        mock_appointment.appointment_type = "consultation"
        mock_appointment.status = "scheduled"
        mock_appointment.reason_for_visit = "Regular checkup"
        mock_appointment.location = "Room 101"
        mock_appointment.is_telehealth = False
        mock_appointment.created_at = datetime.now(timezone.utc)
        mock_appointment.updated_at = datetime.now(timezone.utc)

        # Mock query result
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_appointment
        mock_db.execute.return_value = mock_result

        # Override dependencies
        app.dependency_overrides[
            require_auth_dependency
        ] = lambda: mock_authenticated_user
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_correlation_id] = lambda: "test-correlation-id"

        try:
            appointment_id = str(uuid4())
            response = client.get(f"/api/appointments/{appointment_id}")
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
        finally:
            # Clean up overrides
            app.dependency_overrides.clear()

    def test_create_appointment(self, client, mock_authenticated_user):
        """Test appointment creation."""
        from api.appointments import get_db
        from middleware.auth_middleware import require_auth_dependency
        from middleware.correlation import get_correlation_id

        # Mock database
        mock_db = AsyncMock()

        # Mock created appointment
        mock_appointment = AsyncMock()
        mock_appointment.id = uuid4()
        mock_appointment.client_id = uuid4()
        mock_appointment.provider_id = uuid4()
        mock_appointment.scheduled_start = datetime.now(timezone.utc)
        mock_appointment.scheduled_end = datetime.now(timezone.utc)
        mock_appointment.appointment_type = "consultation"
        mock_appointment.status = "scheduled"
        mock_appointment.created_at = datetime.now(timezone.utc)
        mock_appointment.updated_at = datetime.now(timezone.utc)

        mock_db.add = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Override dependencies
        app.dependency_overrides[
            require_auth_dependency
        ] = lambda: mock_authenticated_user
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_correlation_id] = lambda: "test-correlation-id"

        try:
            client_id = str(uuid4())
            provider_id = str(uuid4())
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
            assert response.status_code == 201
        finally:
            # Clean up overrides
            app.dependency_overrides.clear()

    def test_update_appointment(self, client, mock_authenticated_user):
        """Test appointment update."""
        from api.appointments import get_db
        from middleware.auth_middleware import require_auth_dependency
        from middleware.correlation import get_correlation_id

        # Mock database
        mock_db = AsyncMock()

        # Mock existing appointment
        appointment_id = str(uuid4())
        client_id = str(uuid4())
        provider_id = str(uuid4())

        mock_appointment = AsyncMock()
        mock_appointment.id = appointment_id
        mock_appointment.client_id = client_id
        mock_appointment.provider_id = provider_id

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_appointment
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Override dependencies
        app.dependency_overrides[
            require_auth_dependency
        ] = lambda: mock_authenticated_user
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_correlation_id] = lambda: "test-correlation-id"

        try:
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
            assert response.status_code == 200
        finally:
            # Clean up overrides
            app.dependency_overrides.clear()

    def test_delete_appointment(self, client, mock_authenticated_user):
        """Test appointment deletion."""
        from api.appointments import get_db
        from middleware.auth_middleware import require_auth_dependency
        from middleware.correlation import get_correlation_id

        # Mock database
        mock_db = AsyncMock()

        # Mock existing appointment
        appointment_id = str(uuid4())
        mock_appointment = AsyncMock()
        mock_appointment.id = appointment_id

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_appointment
        mock_db.execute.return_value = mock_result
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        # Override dependencies
        app.dependency_overrides[
            require_auth_dependency
        ] = lambda: mock_authenticated_user
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_correlation_id] = lambda: "test-correlation-id"

        try:
            response = client.delete(f"/api/appointments/{appointment_id}")
            assert response.status_code == 200
        finally:
            # Clean up overrides
            app.dependency_overrides.clear()

    def test_get_appointments_unauthorized(self, client):
        """Test unauthorized access to appointments."""
        response = client.get("/api/appointments/")
        assert response.status_code == 401

    def test_create_appointment_invalid_data(self, client, mock_authenticated_user):
        """Test appointment creation with invalid data."""
        from middleware.auth_middleware import require_auth_dependency
        from middleware.correlation import get_correlation_id

        # Override dependencies
        app.dependency_overrides[
            require_auth_dependency
        ] = lambda: mock_authenticated_user
        app.dependency_overrides[get_correlation_id] = lambda: "test-correlation-id"

        try:
            invalid_data = {
                "client_id": "invalid-uuid",
                "provider_id": "invalid-uuid",
                "scheduled_start": "invalid-date",
            }

            response = client.post("/api/appointments/", json=invalid_data)
            assert response.status_code == 422
        finally:
            # Clean up overrides
            app.dependency_overrides.clear()

    def test_get_appointment_invalid_uuid(self, client, mock_authenticated_user):
        """Test getting appointment with invalid UUID."""
        from middleware.auth_middleware import require_auth_dependency
        from middleware.correlation import get_correlation_id

        # Override dependencies
        app.dependency_overrides[
            require_auth_dependency
        ] = lambda: mock_authenticated_user
        app.dependency_overrides[get_correlation_id] = lambda: "test-correlation-id"

        try:
            response = client.get("/api/appointments/invalid-uuid")
            assert response.status_code == 422
        finally:
            # Clean up overrides
            app.dependency_overrides.clear()

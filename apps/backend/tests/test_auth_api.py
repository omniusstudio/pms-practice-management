"""Tests for auth API endpoints."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Request

from api.auth import LoginRequest, get_client_info, get_current_user, login


class TestAuthAPI:
    """Test cases for auth API functions."""

    def test_get_client_info_extracts_ip_and_user_agent(self):
        """Test that get_client_info extracts IP and user agent."""
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {"user-agent": "TestAgent/1.0"}

        ip, user_agent = get_client_info(mock_request)

        assert ip == "192.168.1.1"
        assert user_agent == "TestAgent/1.0"

    @pytest.mark.asyncio
    async def test_login_raises_401(self):
        """Test login endpoint raises 401 for invalid credentials."""
        login_data = LoginRequest(email="test@example.com", password="password")
        mock_request = MagicMock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await login(login_data, mock_request, "test-correlation-id")

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid credentials"

    @pytest.mark.asyncio
    async def test_get_current_user_raises_401(self):
        """Test get current user endpoint raises 401 for unauthenticated."""
        mock_request = MagicMock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, "test-correlation-id")

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Not authenticated"

    def test_get_client_info(self):
        """Test client info extraction from request."""
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {"user-agent": "Mozilla/5.0 Test Browser"}

        ip, user_agent = get_client_info(mock_request)

        assert ip == "192.168.1.1"
        assert user_agent == "Mozilla/5.0 Test Browser"

    def test_get_db_function(self):
        """Test get_db dependency function."""
        from api.auth import get_db as auth_get_db

        # Test that get_db returns a database session
        db_gen = auth_get_db()
        db_session = next(db_gen)

        # Should return a database session object
        assert db_session is not None

        # Clean up
        try:
            next(db_gen)
        except StopIteration:
            pass  # Expected behavior

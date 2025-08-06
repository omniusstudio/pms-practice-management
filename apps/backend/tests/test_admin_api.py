"""Tests for admin API endpoints."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from api.admin import (
    UserRoleUpdate,
    get_roles_info,
    get_user,
    list_users,
    update_user_roles,
)
from middleware.auth_middleware import AuthenticatedUser
from models.user import User


class TestAdminAPI:
    """Test cases for admin API endpoints."""

    @pytest.fixture
    def mock_admin_user(self):
        """Create a mock admin user."""
        admin_user = User(
            id=uuid4(),
            email="admin@test.com",
            first_name="Admin",
            last_name="User",
            roles=["admin"],
            permissions=["read", "write", "delete", "manage"],
            is_active=True,
            is_admin=True,
            provider_id="admin_provider_123",
            provider_name="admin_provider",
        )
        return AuthenticatedUser(
            user=admin_user, permissions=["read", "write", "delete", "manage"]
        )

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        return mock_db

    @pytest.fixture
    def sample_user(self):
        """Create a sample user for testing."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            first_name="Test",
            last_name="User",
            roles=["clinician"],
            permissions=["read", "write"],
            is_active=True,
            is_admin=False,
            provider_id="test_provider_123",
            provider_name="test_provider",
        )
        return user

    @pytest.mark.asyncio
    async def test_list_users_success(self, mock_admin_user, mock_db, sample_user):
        """Test successful user listing."""
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_user]
        mock_db.execute.return_value = mock_result

        # Call the function
        response = await list_users(
            skip=0,
            limit=100,
            role_filter=None,
            current_user=mock_admin_user,
            db=mock_db,
        )

        # Assertions
        assert response.success is True
        assert len(response.data) == 1
        assert response.data[0].email == "test@example.com"
        assert "Retrieved 1 users" in response.message

    @pytest.mark.asyncio
    async def test_list_users_with_role_filter(
        self, mock_admin_user, mock_db, sample_user
    ):
        """Test user listing with role filter."""
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_user]
        mock_db.execute.return_value = mock_result

        # Call the function with role filter
        response = await list_users(
            skip=0,
            limit=100,
            role_filter="clinician",
            current_user=mock_admin_user,
            db=mock_db,
        )

        # Assertions
        assert response.success is True
        assert len(response.data) == 1
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_users_database_error(self, mock_admin_user, mock_db):
        """Test list_users with database error."""
        # Mock database error
        mock_db.execute.side_effect = Exception("Database error")

        # Test that HTTPException is raised
        with pytest.raises(HTTPException) as exc_info:
            await list_users(
                skip=0,
                limit=100,
                role_filter=None,
                current_user=mock_admin_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 500
        assert "Failed to retrieve users" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_user_success(self, mock_admin_user, mock_db, sample_user):
        """Test successful user retrieval by ID."""
        user_id = sample_user.id

        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result

        # Call the function
        response = await get_user(
            user_id=user_id, current_user=mock_admin_user, db=mock_db
        )

        # Assertions
        assert response.success is True
        assert response.data.email == "test@example.com"
        assert response.message == "User retrieved successfully"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, mock_admin_user, mock_db):
        """Test get_user when user is not found."""
        user_id = uuid4()

        # Mock database query result - user not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Test that HTTPException is raised
        with pytest.raises(HTTPException) as exc_info:
            await get_user(user_id=user_id, current_user=mock_admin_user, db=mock_db)

        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_user_database_error(self, mock_admin_user, mock_db):
        """Test get_user with database error."""
        user_id = uuid4()

        # Mock database error
        mock_db.execute.side_effect = Exception("Database error")

        # Test that HTTPException is raised
        with pytest.raises(HTTPException) as exc_info:
            await get_user(user_id=user_id, current_user=mock_admin_user, db=mock_db)

        assert exc_info.value.status_code == 500
        assert "Failed to retrieve user" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_user_roles_success(
        self, mock_admin_user, mock_db, sample_user
    ):
        """Test successful user role update."""
        user_id = sample_user.id
        role_update = UserRoleUpdate(user_id=user_id, roles=["biller"])

        # Mock database query results
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_user_result

        # Call the function
        response = await update_user_roles(
            user_id=user_id,
            role_update=role_update,
            current_user=mock_admin_user,
            db=mock_db,
        )

        # Assertions
        assert response.success is True
        assert sample_user.roles == ["biller"]
        assert sample_user.is_admin is False
        assert "User roles updated to: biller" in response.message
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(sample_user)

    @pytest.mark.asyncio
    async def test_update_user_roles_invalid_role(self, mock_admin_user, mock_db):
        """Test update_user_roles with invalid role."""
        user_id = uuid4()
        role_update = UserRoleUpdate(user_id=user_id, roles=["invalid_role"])

        # Test that HTTPException is raised for invalid role
        with pytest.raises(HTTPException) as exc_info:
            await update_user_roles(
                user_id=user_id,
                role_update=role_update,
                current_user=mock_admin_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid roles: invalid_role" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_user_roles_user_not_found(self, mock_admin_user, mock_db):
        """Test update_user_roles when user is not found."""
        user_id = uuid4()
        role_update = UserRoleUpdate(user_id=user_id, roles=["clinician"])

        # Mock database query result - user not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Test that HTTPException is raised
        with pytest.raises(HTTPException) as exc_info:
            await update_user_roles(
                user_id=user_id,
                role_update=role_update,
                current_user=mock_admin_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_roles_info_success(self, mock_admin_user):
        """Test successful retrieval of roles information."""
        # Call the function
        response = await get_roles_info(current_user=mock_admin_user)

        # Assertions
        assert response.success is True
        assert "admin" in response.data
        assert "clinician" in response.data
        assert "biller" in response.data
        assert "front_desk" in response.data

        # Check admin role details
        admin_role = response.data["admin"]
        assert admin_role["name"] == "Administrator"
        assert "manage" in admin_role["permissions"]

        expected_msg = "RBAC roles information retrieved successfully"
        assert response.message == expected_msg

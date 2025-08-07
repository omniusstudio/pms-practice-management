"""Tests for User model."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.base import Base
from models.user import User

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TestUserModel:
    """Test cases for User model."""

    @pytest.fixture(scope="function")
    def db_session(self):
        """Create a test database session."""
        Base.metadata.create_all(bind=engine)
        session = TestingSessionLocal()
        yield session
        session.close()
        Base.metadata.drop_all(bind=engine)

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return {
            "email": "test@example.com",
            "provider_id": "test_provider_123",
            "provider_name": "test_provider",
            "first_name": "John",
            "last_name": "Doe",
            "display_name": "John Doe",
            "is_active": True,
            "is_admin": False,
        }

    def test_user_creation(self, db_session, sample_user_data):
        """Test creating a new user."""
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()

        assert user.email == "test@example.com"
        assert user.provider_id == "test_provider_123"
        assert user.provider_name == "test_provider"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.display_name == "John Doe"
        assert user.is_active is True
        assert user.is_admin is False
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_full_name_property(self, sample_user_data):
        """Test full_name property."""
        user = User(**sample_user_data)
        assert user.full_name == "John Doe"

    def test_user_full_name_with_display_name(self):
        """Test full_name property with display name only."""
        user = User(
            email="test@example.com",
            provider_id="test_123",
            provider_name="test",
            display_name="Test User",
        )
        assert user.full_name == "Test User"

    def test_user_full_name_fallback_to_email(self):
        """Test full_name property falls back to email."""
        user = User(
            email="test@example.com", provider_id="test_123", provider_name="test"
        )
        assert user.full_name == "test"

    def test_user_is_locked_property_default(self, sample_user_data):
        """Test is_locked property default value."""
        user = User(**sample_user_data)
        assert user.is_locked is False

    def test_user_is_locked_property_with_lockout(self, sample_user_data):
        """Test is_locked property with account lockout."""
        user = User(**sample_user_data)
        user.locked_until = datetime.now(timezone.utc) + timedelta(hours=1)
        assert user.is_locked is True

    def test_user_is_locked_property_with_expired_lockout(self, sample_user_data):
        """Test is_locked property with expired lockout."""
        user = User(**sample_user_data)
        user.locked_until = datetime.now(timezone.utc) - timedelta(hours=1)
        assert user.is_locked is False

    def test_has_role_method(self, sample_user_data):
        """Test has_role method."""
        user = User(**sample_user_data)
        user.roles = ["admin", "user"]

        assert user.has_role("admin") is True
        assert user.has_role("user") is True
        assert user.has_role("guest") is False

    def test_has_role_method_empty_roles(self, sample_user_data):
        """Test has_role method with empty roles."""
        user = User(**sample_user_data)
        user.roles = []

        assert user.has_role("admin") is False

    def test_has_role_method_none_roles(self, sample_user_data):
        """Test has_role method with None roles."""
        user = User(**sample_user_data)
        user.roles = None

        assert user.has_role("admin") is False

    def test_has_permission_method(self, sample_user_data):
        """Test has_permission method."""
        user = User(**sample_user_data)
        user.permissions = ["read", "write"]

        assert user.has_permission("read") is True
        assert user.has_permission("write") is True
        assert user.has_permission("delete") is False

    def test_has_permission_method_empty_permissions(self, sample_user_data):
        """Test has_permission method with empty permissions."""
        user = User(**sample_user_data)
        user.permissions = []

        assert user.has_permission("read") is False

    def test_has_permission_method_none_permissions(self, sample_user_data):
        """Test has_permission method with None permissions."""
        user = User(**sample_user_data)
        user.permissions = None

        assert user.has_permission("read") is False

    def test_record_login_method(self, sample_user_data):
        """Test record_login method."""
        user = User(**sample_user_data)
        user.record_login()

        assert user.last_login_at is not None
        assert user.login_count == "1"
        assert user.failed_login_attempts == "0"
        assert user.locked_until is None

    def test_record_login_method_increment_count(self, sample_user_data):
        """Test record_login method increments count."""
        user = User(**sample_user_data)
        user.login_count = "5"
        user.record_login()

        assert user.login_count == "6"

    def test_record_failed_login_method(self, sample_user_data):
        """Test record_failed_login method."""
        user = User(**sample_user_data)
        user.record_failed_login()

        assert user.failed_login_attempts == "1"

    def test_record_failed_login_method_increment_attempts(self, sample_user_data):
        """Test record_failed_login method increments attempts."""
        user = User(**sample_user_data)
        user.failed_login_attempts = "2"
        user.record_failed_login()

        assert user.failed_login_attempts == "3"

    def test_record_failed_login_method_locks_account(self, sample_user_data):
        """Test record_failed_login method locks account after 5 attempts."""
        user = User(**sample_user_data)
        user.failed_login_attempts = "4"
        user.record_failed_login()

        assert user.failed_login_attempts == "5"
        assert user.locked_until is not None

    def test_unlock_account_method(self, sample_user_data):
        """Test unlock_account method."""
        user = User(**sample_user_data)
        user.failed_login_attempts = "5"
        user.locked_until = datetime.now(timezone.utc) + timedelta(hours=1)

        user.unlock_account()

        assert user.failed_login_attempts == "0"
        assert user.locked_until is None

    def test_enable_mfa_method(self, sample_user_data):
        """Test enable_mfa method."""
        user = User(**sample_user_data)
        secret = "TESTSECRET123"
        backup_codes = ["code1", "code2"]

        user.enable_mfa(secret, backup_codes)

        assert user.mfa_enabled is True
        assert user.mfa_secret == secret
        assert user.backup_codes == backup_codes

    def test_disable_mfa_method(self, sample_user_data):
        """Test disable_mfa method."""
        user = User(**sample_user_data)
        user.mfa_enabled = True
        user.mfa_secret = "TESTSECRET123"
        user.backup_codes = ["code1", "code2"]

        user.disable_mfa()

        assert user.mfa_enabled is False
        assert user.mfa_secret is None
        assert user.backup_codes == []

    def test_user_repr_method(self, sample_user_data):
        """Test __repr__ method."""
        user = User(**sample_user_data)
        user.id = uuid4()

        repr_str = repr(user)
        assert "<User(" in repr_str
        assert "test@example.com" in repr_str
        assert str(user.id) in repr_str
        assert "test_provider" in repr_str

    def test_user_default_values(self, db_session):
        """Test User model default values."""
        user = User(
            email="test@example.com", provider_id="provider123", provider_name="auth0"
        )
        db_session.add(user)
        db_session.commit()

        assert user.roles == []
        assert user.permissions == []
        assert user.is_active is True
        assert user.is_admin is False
        assert user.login_count == "0"
        assert user.failed_login_attempts == "0"
        assert user.mfa_enabled is False
        assert user.backup_codes == []
        assert user.last_login_at is None
        assert user.locked_until is None
        assert user.mfa_secret is None

    def test_user_timestamps_auto_update(self, db_session, sample_user_data):
        """Test that timestamps are automatically updated."""
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()

        original_updated_at = user.updated_at

        # Update user
        user.first_name = "Jane"
        db_session.commit()

        assert user.updated_at > original_updated_at

    def test_user_email_uniqueness_constraint(self, db_session, sample_user_data):
        """Test email uniqueness constraint."""
        user1 = User(**sample_user_data)
        db_session.add(user1)
        db_session.commit()

        # Try to create another user with same email
        user2_data = sample_user_data.copy()
        user2_data["provider_id"] = "different_provider"
        user2 = User(**user2_data)
        db_session.add(user2)

        with pytest.raises(Exception):  # Should raise integrity error
            db_session.commit()

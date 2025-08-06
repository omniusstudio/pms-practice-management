"""Tests for AuthToken factories."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from factories.auth_token import (
    AccessTokenFactory,
    ApiKeyFactory,
    AuthTokenFactory,
    EmailVerificationTokenFactory,
    ExpiredTokenFactory,
    RefreshTokenFactory,
    ResetPasswordTokenFactory,
    RevokedTokenFactory,
    RotatedTokenFactory,
    SystemTokenFactory,
    create_token_with_plaintext,
)
from models.auth_token import TokenStatus, TokenType


class TestAuthTokenFactory:
    """Test AuthToken factory."""

    def test_creates_valid_token(self):
        """Test that factory creates a valid token."""
        token = AuthTokenFactory.build()

        assert isinstance(token.id, UUID)
        assert isinstance(token.created_at, datetime)
        assert isinstance(token.updated_at, datetime)
        assert token.token_hash is not None
        assert token.status == TokenStatus.ACTIVE
        assert token.issuer == "pms-backend"
        assert token.audience == "pms-client"
        assert isinstance(token.scopes, list)
        assert "read" in token.scopes
        assert "write" in token.scopes

    def test_token_expiration_logic(self):
        """Test token expiration is set correctly."""
        token = AuthTokenFactory.build()

        assert token.expires_at > token.issued_at
        expected_expiry = token.issued_at + timedelta(hours=1)
        # Allow small time difference due to factory execution time
        time_diff = abs((token.expires_at - expected_expiry).total_seconds())
        assert time_diff < 1

    def test_client_info_hashing(self):
        """Test client info is properly hashed."""
        token = AuthTokenFactory.build()

        assert token.client_ip_hash is not None
        assert token.user_agent_hash is not None
        # Hashes should not contain original values
        assert "192.168.1.100" not in token.client_ip_hash
        assert "Mozilla" not in token.user_agent_hash


class TestAccessTokenFactory:
    """Test AccessToken factory."""

    def test_creates_access_token(self):
        """Test access token creation."""
        token = AccessTokenFactory.build()

        assert token.token_type == TokenType.ACCESS
        assert "profile" in token.scopes
        assert token.expires_at > token.issued_at


class TestRefreshTokenFactory:
    """Test RefreshToken factory."""

    def test_creates_refresh_token(self):
        """Test refresh token creation."""
        token = RefreshTokenFactory.build()

        assert token.token_type == TokenType.REFRESH
        assert token.scopes == ["refresh"]
        # Refresh tokens should expire in 30 days
        expected_expiry = token.issued_at + timedelta(days=30)
        time_diff = abs((token.expires_at - expected_expiry).total_seconds())
        assert time_diff < 1


class TestApiKeyFactory:
    """Test ApiKey factory."""

    def test_creates_api_key(self):
        """Test API key creation."""
        token = ApiKeyFactory.build()

        assert token.token_type == TokenType.API_KEY
        assert "api" in token.scopes
        # API keys should expire in 365 days
        expected_expiry = token.issued_at + timedelta(days=365)
        time_diff = abs((token.expires_at - expected_expiry).total_seconds())
        assert time_diff < 1


class TestExpiredTokenFactory:
    """Test ExpiredToken factory."""

    def test_creates_expired_token(self):
        """Test expired token creation."""
        token = ExpiredTokenFactory.build()

        assert token.status == TokenStatus.EXPIRED
        assert token.expires_at < datetime.now(timezone.utc)
        assert token.issued_at < datetime.now(timezone.utc)


class TestRevokedTokenFactory:
    """Test RevokedToken factory."""

    def test_creates_revoked_token(self):
        """Test revoked token creation."""
        token = RevokedTokenFactory.build()

        assert token.status == TokenStatus.REVOKED
        assert token.revoked_at is not None
        assert "revocation_reason" in token.token_metadata
        assert token.token_metadata["revocation_reason"] == "User logout"


class TestRotatedTokenFactory:
    """Test RotatedToken factory."""

    def test_creates_rotated_token(self):
        """Test rotated token creation."""
        token = RotatedTokenFactory.build()

        assert token.parent_token_id is not None
        assert token.rotation_count == "1"
        assert "rotation_reason" in token.token_metadata
        assert token.token_metadata["rotation_reason"] == "Token refresh"


class TestResetPasswordTokenFactory:
    """Test ResetPasswordToken factory."""

    def test_creates_reset_password_token(self):
        """Test reset password token creation."""
        token = ResetPasswordTokenFactory.build()

        assert token.token_type == TokenType.RESET_PASSWORD
        assert token.scopes == ["password_reset"]
        # Reset tokens should expire in 1 hour
        expected_expiry = token.issued_at + timedelta(hours=1)
        time_diff = abs((token.expires_at - expected_expiry).total_seconds())
        assert time_diff < 1


class TestEmailVerificationTokenFactory:
    """Test EmailVerificationToken factory."""

    def test_creates_email_verification_token(self):
        """Test email verification token creation."""
        token = EmailVerificationTokenFactory.build()

        assert token.token_type == TokenType.EMAIL_VERIFICATION
        assert token.scopes == ["email_verification"]
        # Email verification tokens should expire in 24 hours
        expected_expiry = token.issued_at + timedelta(hours=24)
        time_diff = abs((token.expires_at - expected_expiry).total_seconds())
        assert time_diff < 1


class TestSystemTokenFactory:
    """Test SystemToken factory."""

    def test_creates_system_token(self):
        """Test system token creation."""
        token = SystemTokenFactory.build()

        assert token.user_id is None
        assert token.token_type == TokenType.API_KEY
        assert "system" in token.scopes
        assert "admin" in token.scopes
        assert token.token_metadata["system_token"] is True
        assert token.token_metadata["service"] == "background_tasks"


class TestCreateTokenWithPlaintext:
    """Test create_token_with_plaintext function."""

    def test_function_exists_and_callable(self):
        """Test that create_token_with_plaintext function exists."""
        assert callable(create_token_with_plaintext)

    def test_function_signature(self):
        """Test function signature and parameters."""
        import inspect

        sig = inspect.signature(create_token_with_plaintext)
        params = list(sig.parameters.keys())
        assert "token_type" in params
        assert "user_id" in params
        assert "kwargs" in params

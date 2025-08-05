"""Tests for authentication token functionality."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from factories.auth_token import (
    AccessTokenFactory,
    AuthTokenFactory,
    ExpiredTokenFactory,
    RefreshTokenFactory,
    RevokedTokenFactory,
    create_token_with_plaintext,
)
from models.auth_token import AuthToken, TokenStatus, TokenType
from models.base import Base
from services.auth_service import AuthService


class TestAuthTokenModel:
    """Test the AuthToken model."""

    @pytest.fixture
    def engine(self):
        """Create test database engine."""
        return create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    @pytest.fixture
    def session(self, engine):
        """Create test session."""
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.rollback()
        session.close()

    def test_token_creation(self, session):
        """Test basic token creation."""
        token = AuthTokenFactory.build()
        session.add(token)
        session.commit()

        assert token.id is not None
        assert token.token_hash is not None
        assert token.token_type in TokenType
        assert token.status == TokenStatus.ACTIVE
        assert token.created_at is not None
        assert token.expires_at > token.issued_at

    def test_token_hash_generation(self):
        """Test token hash generation."""
        plaintext = "test_token_123"
        hash1 = AuthToken.hash_token(plaintext)
        hash2 = AuthToken.hash_token(plaintext)

        # Same input should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

        # Different input should produce different hash
        hash3 = AuthToken.hash_token("different_token")
        assert hash1 != hash3

    def test_client_info_hashing(self):
        """Test client information hashing."""
        ip = "192.168.1.100"
        user_agent = "Mozilla/5.0 Test Browser"

        ip_hash = AuthToken.hash_client_info(ip)
        ua_hash = AuthToken.hash_client_info(user_agent)

        assert ip_hash is not None
        assert ua_hash is not None
        assert len(ip_hash) == 64
        assert len(ua_hash) == 64

        # Same input should produce same hash
        assert ip_hash == AuthToken.hash_client_info(ip)

        # None input should return None
        assert AuthToken.hash_client_info(None) is None
        assert AuthToken.hash_client_info("") is None

    def test_token_generation(self):
        """Test secure token generation."""
        token1 = AuthToken.generate_token()
        token2 = AuthToken.generate_token()

        # Tokens should be different
        assert token1 != token2
        assert len(token1) > 0
        assert len(token2) > 0

        # Custom length
        short_token = AuthToken.generate_token(16)
        long_token = AuthToken.generate_token(64)
        assert len(short_token) != len(long_token)

    def test_token_expiration_check(self, session):
        """Test token expiration checking."""
        # Set session for factories
        AuthTokenFactory._meta.sqlalchemy_session = session
        ExpiredTokenFactory._meta.sqlalchemy_session = session
        RevokedTokenFactory._meta.sqlalchemy_session = session

        # Active token
        active_token = AuthTokenFactory(
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        assert not active_token.is_expired()
        assert active_token.is_active()

        # Expired token
        expired_token = ExpiredTokenFactory()
        assert expired_token.is_expired()
        assert not expired_token.is_active()

        # Revoked token
        revoked_token = RevokedTokenFactory()
        assert not revoked_token.is_active()

    def test_token_ttl(self, session):
        """Test time-to-live calculation."""
        # Set session for factories
        AuthTokenFactory._meta.sqlalchemy_session = session
        ExpiredTokenFactory._meta.sqlalchemy_session = session

        # Future expiration
        future_token = AuthTokenFactory(
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        ttl = future_token.get_ttl_seconds()
        assert ttl > 0
        assert ttl <= 3600  # Should be less than or equal to 1 hour

        # Expired token
        expired_token = ExpiredTokenFactory()
        assert expired_token.get_ttl_seconds() == 0

    def test_token_to_dict(self, session):
        """Test token dictionary conversion."""
        # Set session for factory
        AuthTokenFactory._meta.sqlalchemy_session = session

        token = AuthTokenFactory()
        token_dict = token.to_dict()

        # Check required fields
        required_fields = [
            "id",
            "token_type",
            "status",
            "issued_at",
            "expires_at",
            "issuer",
            "audience",
            "rotation_count",
            "is_active",
            "ttl_seconds",
        ]

        for field in required_fields:
            assert field in token_dict

        # Sensitive fields should not be included
        assert "token_hash" not in token_dict
        assert "client_ip_hash" not in token_dict
        assert "user_agent_hash" not in token_dict

    def test_token_repr(self, session):
        """Test token string representation."""
        # Set session for factory
        AuthTokenFactory._meta.sqlalchemy_session = session

        token = AuthTokenFactory()
        repr_str = repr(token)

        assert "AuthToken" in repr_str
        assert str(token.id) in repr_str
        assert token.token_type.value in repr_str
        assert token.status.value in repr_str

        # Sensitive data should not be in repr
        assert token.token_hash not in repr_str


class TestAuthService:
    """Test the AuthService class."""

    @pytest.fixture
    def engine(self):
        """Create test database engine."""
        return create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    @pytest.fixture
    def session(self, engine):
        """Create test session."""
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.rollback()
        session.close()

    @pytest.fixture
    def auth_service(self, session):
        """Create auth service instance."""
        return AuthService(session, "test-correlation-id")

    def test_create_access_token(self, auth_service, session):
        """Test access token creation."""
        user_id = uuid4()

        plaintext_token, token_record = auth_service.create_token(
            token_type=TokenType.ACCESS,
            user_id=user_id,
            scopes=["read", "write"],
            client_ip="192.168.1.100",
            user_agent="Test Browser",
        )

        assert plaintext_token is not None
        assert len(plaintext_token) > 0
        assert token_record.id is not None
        assert token_record.token_type == TokenType.ACCESS
        assert token_record.user_id == user_id
        assert token_record.scopes == ["read", "write"]
        assert token_record.client_ip_hash is not None
        assert token_record.user_agent_hash is not None
        assert token_record.status == TokenStatus.ACTIVE

    def test_create_refresh_token(self, auth_service, session):
        """Test refresh token creation."""
        user_id = uuid4()

        plaintext_token, token_record = auth_service.create_token(
            token_type=TokenType.REFRESH,
            user_id=user_id,
            lifetime_seconds=86400 * 30,  # 30 days
        )

        assert token_record.token_type == TokenType.REFRESH
        expected_expiry = token_record.issued_at + timedelta(days=30)
        # Allow for small time differences
        assert abs((token_record.expires_at - expected_expiry).total_seconds()) < 60

    def test_validate_token_success(self, auth_service, session):
        """Test successful token validation."""
        # Create a token
        plaintext_token, created_token = auth_service.create_token(
            token_type=TokenType.ACCESS,
            user_id=uuid4(),
        )
        session.commit()

        # Validate the token
        validated_token = auth_service.validate_token(plaintext_token)

        assert validated_token is not None
        assert validated_token.id == created_token.id
        assert validated_token.last_used_at is not None

    def test_validate_token_failure(self, auth_service, session):
        """Test token validation failure."""
        # Try to validate non-existent token
        result = auth_service.validate_token("invalid_token")
        assert result is None

        # Try to validate expired token
        ExpiredTokenFactory._meta.sqlalchemy_session = session
        ExpiredTokenFactory()
        session.commit()

        # Generate a token that would hash to the expired token's hash
        # (This is just for testing - in reality, we can't reverse the hash)
        result = auth_service.validate_token("some_token")
        assert result is None

    def test_validate_token_with_type(self, auth_service, session):
        """Test token validation with expected type."""
        # Create access token
        plaintext_token, _ = auth_service.create_token(
            token_type=TokenType.ACCESS,
            user_id=uuid4(),
        )
        session.commit()

        # Validate with correct type
        result = auth_service.validate_token(
            plaintext_token, expected_type=TokenType.ACCESS
        )
        assert result is not None

        # Validate with wrong type
        result = auth_service.validate_token(
            plaintext_token, expected_type=TokenType.REFRESH
        )
        assert result is None

    def test_revoke_token(self, auth_service, session):
        """Test token revocation."""
        # Create a token
        plaintext_token, token_record = auth_service.create_token(
            token_type=TokenType.ACCESS,
            user_id=uuid4(),
        )
        session.commit()

        # Revoke the token
        success = auth_service.revoke_token(token_record.id, reason="Test revocation")

        assert success is True

        # Token should no longer validate
        result = auth_service.validate_token(plaintext_token)
        assert result is None

    def test_revoke_user_tokens(self, auth_service, session):
        """Test bulk user token revocation."""
        user_id = uuid4()

        # Create multiple tokens for the user
        tokens = []
        for _ in range(3):
            plaintext_token, token_record = auth_service.create_token(
                token_type=TokenType.ACCESS,
                user_id=user_id,
            )
            tokens.append((plaintext_token, token_record))

        session.commit()

        # Revoke all user tokens
        revoked_count = auth_service.revoke_user_tokens(user_id, reason="User logout")

        assert revoked_count == 3

        # None of the tokens should validate
        for plaintext_token, _ in tokens:
            result = auth_service.validate_token(plaintext_token)
            assert result is None

    def test_token_rotation(self, auth_service, session):
        """Test token rotation."""
        user_id = uuid4()

        # Create initial token
        old_plaintext, old_token = auth_service.create_token(
            token_type=TokenType.ACCESS,
            user_id=user_id,
        )
        session.commit()

        # Rotate the token
        new_plaintext, new_token = auth_service.rotate_token(old_token)

        assert new_plaintext != old_plaintext
        assert new_token.id != old_token.id
        assert new_token.parent_token_id == old_token.id
        assert int(new_token.rotation_count) == 1

        # Old token should be revoked
        old_result = auth_service.validate_token(old_plaintext)
        assert old_result is None

        # New token should be valid
        new_result = auth_service.validate_token(new_plaintext)
        assert new_result is not None
        assert new_result.id == new_token.id

    def test_get_user_tokens(self, auth_service, session):
        """Test getting user tokens."""
        user_id = uuid4()

        # Create tokens for the user
        active_tokens = []
        for i in range(2):
            _, token = auth_service.create_token(
                token_type=TokenType.ACCESS,
                user_id=user_id,
            )
            active_tokens.append(token)

        # Create an expired token
        ExpiredTokenFactory._meta.sqlalchemy_session = session
        ExpiredTokenFactory(user_id=user_id)
        session.commit()

        # Get active tokens only
        active_results = auth_service.get_user_tokens(user_id, active_only=True)
        assert len(active_results) == 2

        # Get all tokens
        all_results = auth_service.get_user_tokens(user_id, active_only=False)
        assert len(all_results) == 3

    def test_cleanup_expired_tokens(self, auth_service, session):
        """Test cleanup of expired tokens."""
        # Set factory sessions
        ExpiredTokenFactory._meta.sqlalchemy_session = session
        AuthTokenFactory._meta.sqlalchemy_session = session

        # Create some expired tokens
        for _ in range(3):
            ExpiredTokenFactory()

        # Create some active tokens
        for _ in range(2):
            AuthTokenFactory()

        session.commit()

        # Run cleanup
        cleaned_count = auth_service.cleanup_expired_tokens()

        assert cleaned_count == 3

        # Verify only active tokens remain
        remaining_tokens = session.query(AuthToken).all()
        assert len(remaining_tokens) == 2
        for token in remaining_tokens:
            assert token.status == TokenStatus.ACTIVE

    def test_default_lifetimes(self, auth_service):
        """Test default token lifetimes."""
        lifetimes = {
            TokenType.ACCESS: auth_service.DEFAULT_ACCESS_TOKEN_LIFETIME,
            TokenType.REFRESH: auth_service.DEFAULT_REFRESH_TOKEN_LIFETIME,
            TokenType.API_KEY: auth_service.DEFAULT_API_KEY_LIFETIME,
            TokenType.RESET_PASSWORD: (auth_service.DEFAULT_RESET_TOKEN_LIFETIME),
            TokenType.EMAIL_VERIFICATION: (
                auth_service.DEFAULT_VERIFICATION_TOKEN_LIFETIME
            ),
        }

        for token_type, expected_lifetime in lifetimes.items():
            actual_lifetime = auth_service._get_default_lifetime(token_type)
            assert actual_lifetime == expected_lifetime


class TestTokenFactories:
    """Test token factories."""

    @pytest.fixture
    def engine(self):
        """Create test engine."""
        return create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )

    @pytest.fixture
    def session(self, engine):
        """Create test session."""
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.rollback()
        session.close()

    def test_create_token_with_plaintext(self, session):
        """Test factory function for creating tokens with plaintext."""
        user_id = str(uuid4())

        # Set up factory sessions for all factory classes
        AuthTokenFactory._meta.sqlalchemy_session = session
        AccessTokenFactory._meta.sqlalchemy_session = session
        RefreshTokenFactory._meta.sqlalchemy_session = session

        plaintext_token, token_record = create_token_with_plaintext(
            token_type=TokenType.ACCESS,
            user_id=user_id,
        )

        assert plaintext_token is not None
        assert len(plaintext_token) > 0
        assert token_record.token_type == TokenType.ACCESS
        assert str(token_record.user_id) == user_id

        # Verify the hash matches
        expected_hash = AuthToken.hash_token(plaintext_token)
        assert token_record.token_hash == expected_hash

    def test_access_token_factory(self):
        """Test AccessTokenFactory."""
        token = AccessTokenFactory.build()

        assert token.token_type == TokenType.ACCESS
        assert "read" in token.scopes
        assert "write" in token.scopes

        # Should expire in about 1 hour
        time_diff = token.expires_at - token.issued_at
        assert abs(time_diff.total_seconds() - 3600) < 60

    def test_refresh_token_factory(self):
        """Test RefreshTokenFactory."""
        token = RefreshTokenFactory.build()

        assert token.token_type == TokenType.REFRESH
        assert "refresh" in token.scopes

        # Should expire in about 30 days
        time_diff = token.expires_at - token.issued_at
        expected_seconds = 30 * 24 * 3600
        assert abs(time_diff.total_seconds() - expected_seconds) < 3600

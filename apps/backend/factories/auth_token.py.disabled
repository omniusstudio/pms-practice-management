"""Factory for creating AuthToken test instances."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import factory
from factory import Faker, LazyAttribute
from factory.alchemy import SQLAlchemyModelFactory

from models.auth_token import AuthToken, TokenStatus, TokenType


class AuthTokenFactory(SQLAlchemyModelFactory):
    """Factory for creating AuthToken instances for testing."""

    class Meta:
        """Factory configuration."""

        model = AuthToken
        sqlalchemy_session_persistence = "commit"
        sqlalchemy_session = None  # Set by tests

    # Base model fields
    id = factory.LazyFunction(uuid4)
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    correlation_id = Faker("uuid4")

    # Token-specific fields
    token_hash = LazyAttribute(
        lambda obj: AuthToken.hash_token(secrets.token_urlsafe(32))
    )
    token_type = factory.Iterator(TokenType)
    status = TokenStatus.ACTIVE

    # User association (nullable)
    user_id = factory.LazyFunction(uuid4)

    # Token lifecycle
    issued_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    expires_at = LazyAttribute(lambda obj: obj.issued_at + timedelta(hours=1))
    last_used_at = None
    revoked_at = None

    # Token metadata
    issuer = "pms-backend"
    audience = "pms-client"
    scopes = factory.LazyFunction(lambda: ["read", "write"])

    # Client information (hashed)
    client_ip_hash = LazyAttribute(
        lambda obj: AuthToken.hash_client_info("192.168.1.100")
    )
    user_agent_hash = LazyAttribute(
        lambda obj: AuthToken.hash_client_info("Mozilla/5.0 Test Browser")
    )

    # Rotation tracking
    parent_token_id = None
    rotation_count = "0"

    # Additional metadata
    token_metadata = factory.LazyFunction(lambda: {})


class AccessTokenFactory(AuthTokenFactory):
    """Factory for access tokens."""

    token_type = TokenType.ACCESS
    expires_at = LazyAttribute(lambda obj: obj.issued_at + timedelta(hours=1))
    scopes = factory.LazyFunction(lambda: ["read", "write", "profile"])


class RefreshTokenFactory(AuthTokenFactory):
    """Factory for refresh tokens."""

    token_type = TokenType.REFRESH
    expires_at = LazyAttribute(lambda obj: obj.issued_at + timedelta(days=30))
    scopes = factory.LazyFunction(lambda: ["refresh"])


class ApiKeyFactory(AuthTokenFactory):
    """Factory for API keys."""

    token_type = TokenType.API_KEY
    expires_at = LazyAttribute(lambda obj: obj.issued_at + timedelta(days=365))
    scopes = factory.LazyFunction(lambda: ["api", "read", "write"])


class ExpiredTokenFactory(AuthTokenFactory):
    """Factory for expired tokens."""

    status = TokenStatus.EXPIRED
    issued_at = LazyAttribute(
        lambda obj: datetime.now(timezone.utc) - timedelta(hours=2)
    )
    expires_at = LazyAttribute(lambda obj: obj.issued_at + timedelta(hours=1))


class RevokedTokenFactory(AuthTokenFactory):
    """Factory for revoked tokens."""

    status = TokenStatus.REVOKED
    revoked_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    token_metadata = factory.LazyFunction(lambda: {"revocation_reason": "User logout"})


class RotatedTokenFactory(AuthTokenFactory):
    """Factory for rotated tokens."""

    parent_token_id = factory.LazyFunction(uuid4)
    rotation_count = "1"
    token_metadata = factory.LazyFunction(lambda: {"rotation_reason": "Token refresh"})


class ResetPasswordTokenFactory(AuthTokenFactory):
    """Factory for password reset tokens."""

    token_type = TokenType.RESET_PASSWORD
    expires_at = LazyAttribute(lambda obj: obj.issued_at + timedelta(hours=1))
    scopes = factory.LazyFunction(lambda: ["password_reset"])


class EmailVerificationTokenFactory(AuthTokenFactory):
    """Factory for email verification tokens."""

    token_type = TokenType.EMAIL_VERIFICATION
    expires_at = LazyAttribute(lambda obj: obj.issued_at + timedelta(hours=24))
    scopes = factory.LazyFunction(lambda: ["email_verification"])


class SystemTokenFactory(AuthTokenFactory):
    """Factory for system tokens (no user association)."""

    user_id = None
    token_type = TokenType.API_KEY
    scopes = factory.LazyFunction(lambda: ["system", "admin"])
    token_metadata = factory.LazyFunction(
        lambda: {"system_token": True, "service": "background_tasks"}
    )


def create_token_with_plaintext(
    token_type: TokenType = TokenType.ACCESS, user_id: Optional[str] = None, **kwargs
) -> tuple[str, AuthToken]:
    """Create a token and return both plaintext and record.

    Args:
        token_type: Type of token to create
        user_id: User ID for the token
        **kwargs: Additional factory parameters

    Returns:
        Tuple of (plaintext_token, token_record)
    """
    # Generate plaintext token
    plaintext_token = secrets.token_urlsafe(32)
    token_hash = AuthToken.hash_token(plaintext_token)

    # Create token record with the hash
    factory_class = {
        TokenType.ACCESS: AccessTokenFactory,
        TokenType.REFRESH: RefreshTokenFactory,
        TokenType.API_KEY: ApiKeyFactory,
        TokenType.RESET_PASSWORD: ResetPasswordTokenFactory,
        TokenType.EMAIL_VERIFICATION: EmailVerificationTokenFactory,
    }.get(token_type, AuthTokenFactory)

    token_record = factory_class(
        token_hash=token_hash, token_type=token_type, user_id=user_id, **kwargs
    )

    return plaintext_token, token_record


def create_token_chain(length: int = 3):
    """Create a chain of rotated tokens.

    Args:
        length: Number of tokens in the chain

    Returns:
        List of tokens in rotation order
    """
    tokens = []
    parent_id = None

    for i in range(length):
        token = AuthTokenFactory(
            parent_token_id=parent_id,
            rotation_count=str(i),
            status=TokenStatus.REVOKED if i < length - 1 else TokenStatus.ACTIVE,
        )
        tokens.append(token)
        parent_id = token.id

    return tokens

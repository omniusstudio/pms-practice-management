"""Authentication service for token lifecycle management."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from models.auth_token import AuthToken, TokenStatus, TokenType
from utils.audit_logger import log_authentication_event


class AuthService:
    """Service for managing authentication tokens.

    Provides secure token lifecycle management including:
    - Token creation and validation
    - Token rotation and revocation
    - Cleanup of expired tokens
    - Comprehensive audit logging
    """

    # Default token lifetimes (in seconds)
    DEFAULT_ACCESS_TOKEN_LIFETIME = 3600  # 1 hour
    DEFAULT_REFRESH_TOKEN_LIFETIME = 86400 * 30  # 30 days
    DEFAULT_RESET_TOKEN_LIFETIME = 3600  # 1 hour
    DEFAULT_VERIFICATION_TOKEN_LIFETIME = 86400  # 24 hours
    DEFAULT_API_KEY_LIFETIME = 86400 * 365  # 1 year

    def __init__(self, session: Session, correlation_id: str):
        """Initialize the auth service.

        Args:
            session: Database session
            correlation_id: Request correlation ID for audit logging
        """
        self.session = session
        self.correlation_id = correlation_id

    def create_token(
        self,
        token_type: TokenType,
        user_id: Optional[UUID] = None,
        lifetime_seconds: Optional[int] = None,
        scopes: Optional[List[str]] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        parent_token_id: Optional[UUID] = None,
        metadata: Optional[Dict] = None,
    ) -> Tuple[str, AuthToken]:
        """Create a new authentication token.

        Args:
            token_type: Type of token to create
            user_id: User ID (optional for system tokens)
            lifetime_seconds: Token lifetime (uses defaults if not provided)
            scopes: List of permission scopes
            client_ip: Client IP address (will be hashed)
            user_agent: Client user agent (will be hashed)
            parent_token_id: Parent token for rotation tracking
            metadata: Additional token metadata

        Returns:
            Tuple of (plaintext_token, token_record)
        """
        # Generate secure token
        plaintext_token = AuthToken.generate_token()
        token_hash = AuthToken.hash_token(plaintext_token)

        # Determine token lifetime
        if lifetime_seconds is None:
            lifetime_seconds = self._get_default_lifetime(token_type)

        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=lifetime_seconds)

        # Create token record
        token_record = AuthToken(
            token_hash=token_hash,
            token_type=token_type,
            user_id=user_id,
            expires_at=expires_at,
            scopes=scopes,
            client_ip_hash=(
                AuthToken.hash_client_info(client_ip) if client_ip else None
            ),
            user_agent_hash=(
                AuthToken.hash_client_info(user_agent) if user_agent else None
            ),
            parent_token_id=parent_token_id,
            token_metadata=metadata or {},
            correlation_id=self.correlation_id,
        )

        # Handle token rotation
        if parent_token_id:
            parent_token = self.session.get(AuthToken, parent_token_id)
            if parent_token:
                # Set rotation count for new token
                rotation_count_value = str(int(parent_token.rotation_count or 0) + 1)
                # Use setattr to avoid type checker issues with SQLAlchemy
                setattr(token_record, "rotation_count", rotation_count_value)

        self.session.add(token_record)
        self.session.flush()  # Get the ID

        # Log token creation
        try:
            log_authentication_event(
                event_type="TOKEN_CREATED",
                user_id=str(user_id) if user_id else "system",
                correlation_id=self.correlation_id,
                success=True,
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except Exception:
            # Don't fail token creation if logging fails
            pass

        return plaintext_token, token_record

    def validate_token(
        self, plaintext_token: str, expected_type: Optional[TokenType] = None
    ) -> Optional[AuthToken]:
        """Validate a token and return the token record if valid.

        Args:
            plaintext_token: The plaintext token to validate
            expected_type: Expected token type (optional)

        Returns:
            Token record if valid, None otherwise
        """
        token_hash = AuthToken.hash_token(plaintext_token)

        # Query for the token
        query = select(AuthToken).where(
            and_(
                AuthToken.token_hash == token_hash,
                AuthToken.status == TokenStatus.ACTIVE.value,
                AuthToken.expires_at > datetime.now(timezone.utc),
            )
        )

        if expected_type:
            query = query.where(AuthToken.token_type == expected_type.value)

        token = self.session.execute(query).scalar_one_or_none()

        if token:
            # Update last used timestamp
            token.mark_used()
            self.session.commit()

            # Log successful validation
            log_authentication_event(
                event_type="TOKEN_VALIDATED",
                user_id=str(token.user_id) if token.user_id else "system",
                correlation_id=self.correlation_id,
                success=True,
            )
        else:
            # Log failed validation
            log_authentication_event(
                event_type="TOKEN_VALIDATION_FAILED",
                user_id="unknown",
                correlation_id=self.correlation_id,
                success=False,
                failure_reason="Invalid or expired token",
            )

        return token

    def revoke_token(self, token_id: UUID, reason: Optional[str] = None) -> bool:
        """Revoke a specific token.

        Args:
            token_id: ID of the token to revoke
            reason: Optional reason for revocation

        Returns:
            True if token was revoked, False if not found
        """
        token = self.session.get(AuthToken, token_id)
        if not token:
            return False

        token.revoke(reason)
        self.session.commit()

        # Log token revocation
        try:
            log_authentication_event(
                event_type="TOKEN_REVOKED",
                user_id=str(token.user_id) if token.user_id else "system",
                correlation_id=self.correlation_id,
                success=True,
            )
        except Exception:
            # Don't fail revocation if logging fails
            pass

        return True

    def revoke_user_tokens(
        self,
        user_id: UUID,
        token_type: Optional[TokenType] = None,
        reason: Optional[str] = None,
    ) -> int:
        """Revoke all tokens for a user.

        Args:
            user_id: User ID whose tokens to revoke
            token_type: Optional specific token type to revoke
            reason: Optional reason for revocation

        Returns:
            Number of tokens revoked
        """
        query = select(AuthToken).where(
            and_(
                AuthToken.user_id == user_id,
                AuthToken.status == TokenStatus.ACTIVE.value,
            )
        )

        if token_type:
            query = query.where(AuthToken.token_type == token_type.value)

        tokens = self.session.execute(query).scalars().all()

        for token in tokens:
            token.revoke(reason)

        self.session.commit()

        # Log bulk revocation
        try:
            log_authentication_event(
                event_type="TOKENS_BULK_REVOKED",
                user_id=str(user_id),
                correlation_id=self.correlation_id,
                success=True,
            )
        except Exception:
            # Don't fail revocation if logging fails
            pass

        return len(tokens)

    def rotate_token(
        self, old_token: AuthToken, new_lifetime_seconds: Optional[int] = None
    ) -> Tuple[str, AuthToken]:
        """Rotate a token by creating a new one and revoking the old one.

        Args:
            old_token: The token to rotate
            new_lifetime_seconds: Lifetime for the new token

        Returns:
            Tuple of (new_plaintext_token, new_token_record)
        """
        # Create new token with same properties
        from uuid import UUID as UUIDType

        user_id_val = (
            old_token.user_id if isinstance(old_token.user_id, UUIDType) else None
        )
        parent_id_val = old_token.id if isinstance(old_token.id, UUIDType) else None

        new_plaintext_token, new_token = self.create_token(
            token_type=TokenType(old_token.token_type),
            user_id=user_id_val,
            lifetime_seconds=new_lifetime_seconds,
            scopes=list(old_token.scopes) if old_token.scopes else None,
            parent_token_id=parent_id_val,
            metadata=(
                dict(old_token.token_metadata) if old_token.token_metadata else None
            ),
        )

        # Revoke old token
        old_token.revoke()

        self.session.commit()

        # Log token rotation
        try:
            log_authentication_event(
                event_type="TOKEN_ROTATED",
                user_id=(str(old_token.user_id) if old_token.user_id else "system"),
                correlation_id=self.correlation_id,
                success=True,
            )
        except Exception:
            # Don't fail rotation if logging fails
            pass

        return new_plaintext_token, new_token

    def cleanup_expired_tokens(self, batch_size: int = 1000) -> int:
        """Clean up expired and revoked tokens.

        Args:
            batch_size: Number of tokens to process in each batch

        Returns:
            Number of tokens cleaned up
        """
        cutoff_time = datetime.now(timezone.utc)

        # Find expired or revoked tokens
        query = (
            select(AuthToken)
            .where(
                or_(
                    AuthToken.expires_at < cutoff_time,
                    AuthToken.status.in_(
                        [TokenStatus.EXPIRED.value, TokenStatus.REVOKED.value]
                    ),
                )
            )
            .limit(batch_size)
        )

        tokens_to_delete = self.session.execute(query).scalars().all()

        for token in tokens_to_delete:
            self.session.delete(token)

        self.session.commit()

        # Log cleanup operation
        if tokens_to_delete:
            try:
                log_authentication_event(
                    event_type="TOKENS_CLEANED_UP",
                    user_id="system",
                    correlation_id=self.correlation_id,
                    success=True,
                )
            except Exception:
                # Don't fail cleanup if logging fails
                pass

        return len(tokens_to_delete)

    def get_user_tokens(
        self, user_id: UUID, active_only: bool = True
    ) -> List[AuthToken]:
        """Get all tokens for a user.

        Args:
            user_id: User ID
            active_only: Whether to return only active tokens

        Returns:
            List of user's tokens
        """
        query = select(AuthToken).where(AuthToken.user_id == user_id)

        if active_only:
            query = query.where(
                and_(
                    AuthToken.status == TokenStatus.ACTIVE.value,
                    AuthToken.expires_at > datetime.now(timezone.utc),
                )
            )

        return list(self.session.execute(query).scalars().all())

    def _get_default_lifetime(self, token_type: TokenType) -> int:
        """Get default lifetime for a token type.

        Args:
            token_type: The token type

        Returns:
            Default lifetime in seconds
        """
        lifetimes = {
            TokenType.ACCESS: self.DEFAULT_ACCESS_TOKEN_LIFETIME,
            TokenType.REFRESH: self.DEFAULT_REFRESH_TOKEN_LIFETIME,
            TokenType.RESET_PASSWORD: self.DEFAULT_RESET_TOKEN_LIFETIME,
            TokenType.EMAIL_VERIFICATION: (self.DEFAULT_VERIFICATION_TOKEN_LIFETIME),
            TokenType.API_KEY: self.DEFAULT_API_KEY_LIFETIME,
        }

        return lifetimes.get(token_type, self.DEFAULT_ACCESS_TOKEN_LIFETIME)


class AsyncAuthService:
    """Async version of the authentication service."""

    def __init__(self, session: AsyncSession, correlation_id: str):
        """Initialize the async auth service.

        Args:
            session: Async database session
            correlation_id: Request correlation ID for audit logging
        """
        self.session = session
        self.correlation_id = correlation_id

    async def validate_token(
        self, plaintext_token: str, expected_type: Optional[TokenType] = None
    ) -> Optional[AuthToken]:
        """Async version of token validation.

        Args:
            plaintext_token: The plaintext token to validate
            expected_type: Expected token type (optional)

        Returns:
            Token record if valid, None otherwise
        """
        token_hash = AuthToken.hash_token(plaintext_token)

        # Query for the token
        query = select(AuthToken).where(
            and_(
                AuthToken.token_hash == token_hash,
                AuthToken.status == TokenStatus.ACTIVE.value,
                AuthToken.expires_at > datetime.now(timezone.utc),
            )
        )

        if expected_type:
            query = query.where(AuthToken.token_type == expected_type.value)

        result = await self.session.execute(query)
        token = result.scalar_one_or_none()

        if token:
            # Update last used timestamp
            token.mark_used()
            await self.session.commit()

            # Log successful validation
            log_authentication_event(
                event_type="TOKEN_VALIDATED",
                user_id=str(token.user_id) if token.user_id else "system",
                correlation_id=self.correlation_id,
                success=True,
            )
        else:
            # Log failed validation
            log_authentication_event(
                event_type="TOKEN_VALIDATION_FAILED",
                user_id="unknown",
                correlation_id=self.correlation_id,
                success=False,
                failure_reason="Invalid or expired token",
            )

        return token


def get_auth_service(session: Session, correlation_id: str) -> AuthService:
    """Factory function to create an AuthService instance.

    Args:
        session: Database session
        correlation_id: Request correlation ID

    Returns:
        AuthService instance
    """
    return AuthService(session, correlation_id)


def get_async_auth_service(
    session: AsyncSession, correlation_id: str
) -> AsyncAuthService:
    """Factory function to create an AsyncAuthService instance.

    Args:
        session: Async database session
        correlation_id: Request correlation ID

    Returns:
        AsyncAuthService instance
    """
    return AsyncAuthService(session, correlation_id)

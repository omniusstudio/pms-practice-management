"""Authentication API endpoints for token management."""

import logging
from datetime import datetime
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import SessionLocal
from middleware.correlation import get_correlation_id
from models.auth_token import TokenStatus, TokenType
from schemas.auth import (
    TokenCleanupResponse,
    TokenCreateRequest,
    TokenInfoResponse,
    TokenResponse,
    TokenRevocationRequest,
    TokenRevocationResponse,
    TokenRotationRequest,
    TokenRotationResponse,
    TokenValidationRequest,
    TokenValidationResponse,
    UserTokensResponse,
)
from services.auth_service import get_auth_service

# Removed unused import: log_authentication_event
from utils.error_handlers import handle_database_error, log_and_raise_error

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_client_info(request: Request) -> tuple[str, str]:
    """Extract client information from request.

    Args:
        request: FastAPI request object

    Returns:
        Tuple of (client_ip, user_agent)
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    return client_ip, user_agent


@router.post(
    "/tokens",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new authentication token",
    description="Create a new authentication token with specified properties.",
)
def create_token(
    request_data: TokenCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id),
):
    """Create a new authentication token.

    Args:
        request_data: Token creation parameters
        request: FastAPI request object
        db: Database session
        correlation_id: Request correlation ID

    Returns:
        Created token information

    Raises:
        HTTPException: If token creation fails
    """
    try:
        auth_service = get_auth_service(db, correlation_id)
        client_ip, user_agent = get_client_info(request)

        # Create the token
        plaintext_token, token_record = auth_service.create_token(
            token_type=request_data.token_type,
            user_id=request_data.user_id,
            lifetime_seconds=request_data.lifetime_seconds,
            scopes=request_data.scopes,
            client_ip=client_ip,
            user_agent=user_agent,
            metadata=request_data.metadata,
        )

        db.commit()

        return TokenResponse(
            token=plaintext_token,
            token_id=cast(UUID, token_record.id),
            token_type=TokenType(token_record.token_type),
            expires_at=cast(datetime, token_record.expires_at),
            scopes=list(token_record.scopes) if token_record.scopes else [],
        )

    except Exception as e:
        error = handle_database_error(e, correlation_id, "token creation")
        user_id = str(request_data.user_id) if request_data.user_id else "system"
        log_and_raise_error(
            error=error, db_session=db, user_id=user_id, operation="token_creation"
        )


@router.post(
    "/tokens/validate",
    response_model=TokenValidationResponse,
    summary="Validate an authentication token",
    description="Validate a token and return its information if valid.",
)
def validate_token(
    request_data: TokenValidationRequest,
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id),
):
    """Validate an authentication token.

    Args:
        request_data: Token validation parameters
        db: Database session
        correlation_id: Request correlation ID

    Returns:
        Token validation result
    """
    try:
        auth_service = get_auth_service(db, correlation_id)

        # Validate the token
        token_record = auth_service.validate_token(
            plaintext_token=request_data.token,
            expected_type=request_data.expected_type,
        )

        if token_record:
            return TokenValidationResponse(
                valid=True,
                token_id=cast(UUID, token_record.id),
                user_id=cast(UUID, token_record.user_id),
                token_type=TokenType(token_record.token_type),
                scopes=(list(token_record.scopes) if token_record.scopes else []),
                expires_at=cast(datetime, token_record.expires_at),
            )
        else:
            return TokenValidationResponse(
                valid=False,
                token_id=None,
                user_id=None,
                token_type=None,
                scopes=None,
                expires_at=None,
            )

    except Exception as e:
        logger.error(
            f"Token validation failed: {str(e)}",
            extra={"correlation_id": correlation_id, "error": str(e)},
        )

        return TokenValidationResponse(
            valid=False,
            token_id=None,
            user_id=None,
            token_type=None,
            scopes=None,
            expires_at=None,
        )


@router.post(
    "/tokens/revoke",
    response_model=TokenRevocationResponse,
    summary="Revoke authentication tokens",
    description="Revoke specific tokens or all tokens for a user.",
)
def revoke_tokens(
    request_data: TokenRevocationRequest,
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id),
):
    """Revoke authentication tokens.

    Args:
        request_data: Token revocation parameters
        db: Database session
        correlation_id: Request correlation ID

    Returns:
        Revocation result

    Raises:
        HTTPException: If no target specified or revocation fails
    """
    try:
        # Validate that at least one target is specified
        if not request_data.token_id and not request_data.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must specify either token_id or user_id",
            )

        auth_service = get_auth_service(db, correlation_id)
        revoked_count = 0

        if request_data.token_id:
            # Revoke specific token
            success = auth_service.revoke_token(
                token_id=request_data.token_id,
                reason=request_data.reason,
            )
            revoked_count = 1 if success else 0
        elif request_data.user_id:
            # Revoke user tokens
            revoked_count = auth_service.revoke_user_tokens(
                user_id=request_data.user_id,
                token_type=request_data.token_type,
                reason=request_data.reason,
            )

        db.commit()

        return TokenRevocationResponse(
            revoked_count=revoked_count,
            success=revoked_count > 0,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            f"Token revocation failed: {str(e)}",
            extra={"correlation_id": correlation_id, "error": str(e)},
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke tokens",
        )


@router.post(
    "/tokens/rotate",
    response_model=TokenRotationResponse,
    summary="Rotate an authentication token",
    description="Create a new token and revoke the old one.",
)
def rotate_token(
    request_data: TokenRotationRequest,
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id),
):
    """Rotate an authentication token.

    Args:
        request_data: Token rotation parameters
        db: Database session
        correlation_id: Request correlation ID

    Returns:
        New token information

    Raises:
        HTTPException: If token is invalid or rotation fails
    """
    try:
        auth_service = get_auth_service(db, correlation_id)

        # First validate the current token
        current_token = auth_service.validate_token(plaintext_token=request_data.token)

        if not current_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        # Rotate the token
        new_plaintext_token, new_token = auth_service.rotate_token(
            old_token=current_token,
            new_lifetime_seconds=request_data.new_lifetime_seconds,
        )

        db.commit()

        return TokenRotationResponse(
            new_token=new_plaintext_token,
            new_token_id=cast(UUID, new_token.id),
            expires_at=cast(datetime, new_token.expires_at),
            rotation_count=int(new_token.rotation_count),
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            f"Token rotation failed: {str(e)}",
            extra={"correlation_id": correlation_id, "error": str(e)},
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate token",
        )


@router.get(
    "/tokens/{token_id}",
    response_model=TokenInfoResponse,
    summary="Get token information",
    description="Get detailed information about a specific token.",
)
def get_token_info(
    token_id: UUID,
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id),
):
    """Get information about a specific token.

    Args:
        token_id: Token ID to retrieve
        db: Database session
        correlation_id: Request correlation ID

    Returns:
        Token information

    Raises:
        HTTPException: If token not found
    """
    try:
        from models.auth_token import AuthToken

        token = db.get(AuthToken, token_id)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token not found",
            )

        return TokenInfoResponse(
            id=cast(UUID, token.id),
            token_type=TokenType(token.token_type),
            status=TokenStatus(token.status),
            user_id=cast(UUID, token.user_id) if token.user_id else None,
            issued_at=cast(datetime, token.issued_at),
            expires_at=cast(datetime, token.expires_at),
            last_used_at=(
                cast(datetime, token.last_used_at) if token.last_used_at else None
            ),
            scopes=list(token.scopes) if token.scopes else [],
            rotation_count=int(token.rotation_count),
            is_active=token.is_active(),
            ttl_seconds=token.get_ttl_seconds(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get token info: {str(e)}",
            extra={"correlation_id": correlation_id, "error": str(e)},
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve token information",
        )


@router.get(
    "/users/{user_id}/tokens",
    response_model=UserTokensResponse,
    summary="Get user's tokens",
    description="Get all tokens for a specific user.",
)
def get_user_tokens(
    user_id: UUID,
    active_only: bool = True,
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id),
):
    """Get all tokens for a user.

    Args:
        user_id: User ID
        active_only: Whether to return only active tokens
        db: Database session
        correlation_id: Request correlation ID

    Returns:
        User's tokens
    """
    try:
        auth_service = get_auth_service(db, correlation_id)

        tokens = auth_service.get_user_tokens(
            user_id=user_id,
            active_only=active_only,
        )

        token_responses = [
            TokenInfoResponse(
                id=cast(UUID, token.id),
                token_type=TokenType(token.token_type),
                status=TokenStatus(token.status),
                user_id=cast(UUID, token.user_id) if token.user_id else None,
                issued_at=cast(datetime, token.issued_at),
                expires_at=cast(datetime, token.expires_at),
                last_used_at=(
                    cast(datetime, token.last_used_at) if token.last_used_at else None
                ),
                scopes=list(token.scopes) if token.scopes else [],
                rotation_count=int(token.rotation_count),
                is_active=token.is_active(),
                ttl_seconds=token.get_ttl_seconds(),
            )
            for token in tokens
        ]

        active_count = sum(1 for token in tokens if token.is_active())

        return UserTokensResponse(
            user_id=user_id,
            tokens=token_responses,
            total_count=len(tokens),
            active_count=active_count,
        )

    except Exception as e:
        logger.error(
            f"Failed to get user tokens: {str(e)}",
            extra={"correlation_id": correlation_id, "error": str(e)},
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user tokens",
        )


@router.post(
    "/tokens/cleanup",
    response_model=TokenCleanupResponse,
    summary="Clean up expired tokens",
    description="Remove expired and revoked tokens from the database.",
)
def cleanup_tokens(
    batch_size: int = 1000,
    db: Session = Depends(get_db),
    correlation_id: str = Depends(get_correlation_id),
):
    """Clean up expired and revoked tokens.

    Args:
        batch_size: Number of tokens to process in each batch
        db: Database session
        correlation_id: Request correlation ID

    Returns:
        Cleanup result
    """
    try:
        auth_service = get_auth_service(db, correlation_id)

        cleaned_count = auth_service.cleanup_expired_tokens(
            batch_size=min(batch_size, 10000)  # Cap at 10k for safety
        )

        db.commit()

        return TokenCleanupResponse(
            cleaned_count=cleaned_count,
            success=True,
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"Token cleanup failed: {str(e)}",
            extra={"correlation_id": correlation_id, "error": str(e)},
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clean up tokens",
        )

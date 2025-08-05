"""Authentication schemas for API requests and responses."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from models.auth_token import TokenStatus, TokenType


class TokenCreateRequest(BaseModel):
    """Request schema for creating a new token."""

    token_type: TokenType = Field(..., description="Type of token to create")
    user_id: Optional[UUID] = Field(
        None, description="User ID (optional for system tokens)"
    )
    lifetime_seconds: Optional[int] = Field(
        None,
        description="Token lifetime in seconds (uses defaults if not provided)",
        gt=0,
        le=86400 * 365,  # Max 1 year
    )
    scopes: Optional[List[str]] = Field(None, description="List of permission scopes")
    metadata: Optional[Dict] = Field(None, description="Additional token metadata")

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v):
        """Validate scopes format."""
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("Scopes must be a list")
            for scope in v:
                if not isinstance(scope, str) or not scope.strip():
                    raise ValueError("Each scope must be a non-empty string")
        return v


class TokenResponse(BaseModel):
    """Response schema for token operations."""

    token: str = Field(..., description="The authentication token")
    token_id: UUID = Field(..., description="Token ID for management")
    token_type: TokenType = Field(..., description="Type of token")
    expires_at: datetime = Field(..., description="Token expiration time")
    scopes: Optional[List[str]] = Field(None, description="Token scopes")

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat(), UUID: str}


class TokenValidationRequest(BaseModel):
    """Request schema for token validation."""

    token: str = Field(..., description="Token to validate")
    expected_type: Optional[TokenType] = Field(None, description="Expected token type")


class TokenValidationResponse(BaseModel):
    """Response schema for token validation."""

    valid: bool = Field(..., description="Whether the token is valid")
    token_id: Optional[UUID] = Field(None, description="Token ID if valid")
    user_id: Optional[UUID] = Field(None, description="User ID if valid")
    token_type: Optional[TokenType] = Field(None, description="Token type if valid")
    scopes: Optional[List[str]] = Field(None, description="Token scopes if valid")
    expires_at: Optional[datetime] = Field(
        None, description="Token expiration if valid"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat(), UUID: str}


class TokenRevocationRequest(BaseModel):
    """Request schema for token revocation."""

    token_id: Optional[UUID] = Field(None, description="Specific token ID to revoke")
    user_id: Optional[UUID] = Field(None, description="Revoke all tokens for this user")
    token_type: Optional[TokenType] = Field(
        None, description="Specific token type to revoke"
    )
    reason: Optional[str] = Field(
        None, description="Reason for revocation", max_length=255
    )

    @field_validator("token_id", "user_id")
    @classmethod
    def validate_revocation_target(cls, v, info):
        """Ensure at least one target is specified."""
        # This will be validated in the endpoint logic
        return v


class TokenRevocationResponse(BaseModel):
    """Response schema for token revocation."""

    revoked_count: int = Field(..., description="Number of tokens revoked")
    success: bool = Field(..., description="Whether revocation succeeded")


class TokenRotationRequest(BaseModel):
    """Request schema for token rotation."""

    token: str = Field(..., description="Current token to rotate")
    new_lifetime_seconds: Optional[int] = Field(
        None,
        description="Lifetime for new token (uses defaults if not provided)",
        gt=0,
        le=86400 * 365,  # Max 1 year
    )


class TokenRotationResponse(BaseModel):
    """Response schema for token rotation."""

    new_token: str = Field(..., description="The new authentication token")
    new_token_id: UUID = Field(..., description="New token ID")
    expires_at: datetime = Field(..., description="New token expiration")
    rotation_count: int = Field(
        ..., description="Number of times this token chain has been rotated"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat(), UUID: str}


class TokenInfoResponse(BaseModel):
    """Response schema for token information."""

    id: UUID = Field(..., description="Token ID")
    token_type: TokenType = Field(..., description="Token type")
    status: TokenStatus = Field(..., description="Token status")
    user_id: Optional[UUID] = Field(None, description="Associated user ID")
    issued_at: datetime = Field(..., description="Token issue time")
    expires_at: datetime = Field(..., description="Token expiration time")
    last_used_at: Optional[datetime] = Field(None, description="Last usage time")
    scopes: Optional[List[str]] = Field(None, description="Token scopes")
    rotation_count: int = Field(..., description="Number of rotations")
    is_active: bool = Field(..., description="Whether token is active")
    ttl_seconds: int = Field(..., description="Time to live in seconds")

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat(), UUID: str}


class UserTokensResponse(BaseModel):
    """Response schema for user's tokens."""

    user_id: UUID = Field(..., description="User ID")
    tokens: List[TokenInfoResponse] = Field(..., description="List of user's tokens")
    total_count: int = Field(..., description="Total number of tokens")
    active_count: int = Field(..., description="Number of active tokens")

    class Config:
        """Pydantic configuration."""

        json_encoders = {UUID: str}


class TokenCleanupResponse(BaseModel):
    """Response schema for token cleanup operations."""

    cleaned_count: int = Field(..., description="Number of tokens cleaned up")
    success: bool = Field(..., description="Whether cleanup succeeded")


class AuthErrorResponse(BaseModel):
    """Error response schema for authentication operations."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error timestamp"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}

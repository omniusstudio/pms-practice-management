"""OIDC Authentication Router.

This module provides OAuth2/OpenID Connect authentication endpoints including:
- Authorization initiation
- Callback handling
- Token refresh
- Logout
- Session management
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.exceptions import AuthenticationError, ConfigurationError, ValidationError
from database import get_db
from models.auth_token import AuthToken
from models.user import User
from services.auth_service import AuthService
from services.oidc_service import OIDCConfig, oidc_service

logger = logging.getLogger(__name__)


# Defer settings initialization to avoid requiring env vars at import time
def get_oidc_settings():
    """Get settings instance."""
    return get_settings()


router = APIRouter(prefix="/auth", tags=["authentication"])


# Request/Response Models
class LoginRequest(BaseModel):
    """OIDC login request."""

    provider: str = Field(..., description="OIDC provider name")
    redirect_url: Optional[str] = Field(
        None, description="URL to redirect after successful login"
    )


class LoginResponse(BaseModel):
    """OIDC login response."""

    authorization_url: str = Field(..., description="Authorization URL")
    state: str = Field(..., description="OAuth2 state parameter")


class CallbackResponse(BaseModel):
    """OIDC callback response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    user_id: str = Field(..., description="User ID")


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str = Field(..., description="Refresh token")


class RefreshResponse(BaseModel):
    """Token refresh response."""

    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")


# Provider configurations
def get_provider_config(provider: str) -> OIDCConfig:
    """Get OIDC provider configuration."""
    settings = get_oidc_settings()
    if provider == "google":
        if not settings.oidc_google_client_id or not settings.oidc_google_client_secret:
            raise ConfigurationError("Google OIDC not configured")

        return OIDCConfig(
            provider_name="google",
            client_id=settings.oidc_google_client_id,
            client_secret=settings.oidc_google_client_secret,
            discovery_url=(
                "https://accounts.google.com/.well-known/openid_configuration"
            ),
            redirect_uri=settings.oidc_redirect_uri,
            scopes=["openid", "profile", "email"],
        )
    elif provider == "microsoft":
        if (
            not settings.oidc_microsoft_client_id
            or not settings.oidc_microsoft_client_secret
        ):
            raise ConfigurationError("Microsoft OIDC not configured")

        return OIDCConfig(
            provider_name="microsoft",
            client_id=settings.oidc_microsoft_client_id,
            client_secret=settings.oidc_microsoft_client_secret,
            discovery_url=(
                "https://login.microsoftonline.com/common/v2.0/"
                ".well-known/openid_configuration"
            ),
            redirect_uri=settings.oidc_redirect_uri,
            scopes=["openid", "profile", "email"],
        )
    else:
        raise ValidationError(f"Unsupported provider: {provider}")


# Session storage (in production, use Redis)
_session_store: Dict[str, Dict] = {}


def store_session_data(state: str, data: Dict) -> None:
    """Store session data temporarily."""
    _session_store[state] = {
        **data,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
    }


def get_session_data(state: str) -> Optional[Dict]:
    """Retrieve and validate session data."""
    data = _session_store.get(state)
    if not data:
        return None

    # Check expiry
    if datetime.now(timezone.utc) > data["expires_at"]:
        _session_store.pop(state, None)
        return None

    return data


def clear_session_data(state: str) -> None:
    """Clear session data."""
    _session_store.pop(state, None)


@router.post("/login", response_model=LoginResponse)
async def initiate_oidc_login(
    request: LoginRequest, db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    """Initiate OIDC authentication flow."""
    try:
        # Get provider configuration
        config = get_provider_config(request.provider)

        # Generate state and nonce for security
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)

        # Store session data
        store_session_data(
            state,
            {
                "provider": request.provider,
                "nonce": nonce,
                "redirect_url": request.redirect_url,
            },
        )

        # Generate authorization URL
        authorization_url = await oidc_service.get_authorization_url(
            config, state, nonce
        )

        logger.info(
            "OIDC login initiated",
            extra={"provider": request.provider, "state": state[:8] + "..."},
        )

        return LoginResponse(authorization_url=authorization_url, state=state)

    except (ConfigurationError, ValidationError) as e:
        logger.error(f"OIDC login error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during OIDC login: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/callback")
async def handle_oidc_callback(
    code: str,
    state: str,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle OIDC callback from provider."""
    try:
        # Handle OAuth2 errors
        if error:
            logger.error(
                f"OIDC callback error: {error}",
                extra={"error_description": error_description},
            )
            raise HTTPException(
                status_code=400,
                detail=f"Authentication failed: {error_description or error}",
            )

        # Retrieve session data
        session_data = get_session_data(state)
        if not session_data:
            logger.error("Invalid or expired state parameter")
            raise HTTPException(status_code=400, detail="Invalid session")

        provider = session_data["provider"]
        nonce = session_data["nonce"]
        redirect_url = session_data.get("redirect_url")

        # Clear session data
        clear_session_data(state)

        # Get provider configuration
        config = get_provider_config(provider)

        # Exchange code for tokens
        tokens = await oidc_service.exchange_code_for_tokens(config, code, state)

        # Validate ID token
        await oidc_service.validate_id_token(config, tokens.id_token, nonce)

        # Get user info
        user_info = await oidc_service.get_user_info(config, tokens.access_token)

        # Find or create user
        user = await oidc_service.find_or_create_user(db, user_info, provider)

        # Record login
        user.record_login()

        # Create internal JWT token
        auth_svc = AuthService(db)
        jwt_token = await auth_svc.create_token(
            user_id=str(user.id),
            provider_id=provider,
            token_type="access",
            expires_minutes=settings.jwt_expire_minutes,
        )

        # Store OIDC tokens (encrypted)
        await auth_svc.create_token(
            user_id=str(user.id),
            provider_id=provider,
            token_type="oidc_access",
            expires_minutes=(tokens.expires_in // 60 if tokens.expires_in else 60),
            metadata={
                "oidc_access_token": tokens.access_token,
                "oidc_refresh_token": tokens.refresh_token,
                "oidc_id_token": tokens.id_token,
            },
        )

        await db.commit()

        logger.info(
            "OIDC authentication successful",
            extra={
                "user_id": str(user.id),
                "provider": provider,
                "email_verified": user.email_verified,
            },
        )

        # Redirect with token or return JSON
        if redirect_url:
            # Redirect to frontend with token
            params = urlencode(
                {
                    "access_token": jwt_token.token,
                    "token_type": "Bearer",
                    "expires_in": settings.jwt_expire_minutes * 60,
                    "user_id": str(user.id),
                }
            )
            return RedirectResponse(url=f"{redirect_url}?{params}")
        else:
            # Return JSON response
            return CallbackResponse(
                access_token=jwt_token.token,
                token_type="Bearer",
                expires_in=settings.jwt_expire_minutes * 60,
                user_id=str(user.id),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during OIDC callback: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_access_token(
    request: RefreshRequest, db: AsyncSession = Depends(get_db)
) -> RefreshResponse:
    """Refresh access token using refresh token."""
    try:
        # Validate refresh token
        auth_svc = AuthService(db)
        refresh_token = await auth_svc.validate_token(request.refresh_token)

        if refresh_token.token_type != "refresh":
            raise ValidationError("Invalid token type")

        # Get user
        stmt = select(User).where(User.id == refresh_token.user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        # Create new access token
        new_token = await auth_svc.create_token(
            user_id=str(user.id),
            provider_id=refresh_token.provider_id,
            token_type="access",
            expires_minutes=settings.jwt_expire_minutes,
        )

        # Rotate refresh token
        await auth_svc.rotate_token(refresh_token.id)

        await db.commit()

        logger.info("Access token refreshed", extra={"user_id": str(user.id)})

        return RefreshResponse(
            access_token=new_token.token,
            token_type="Bearer",
            expires_in=settings.jwt_expire_minutes * 60,
        )

    except (AuthenticationError, ValidationError) as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/logout")
async def logout(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    """Logout user and revoke tokens."""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="No token provided")

        token_value = auth_header.split(" ")[1]

        # Validate and revoke token
        auth_svc = AuthService(db)
        token = await auth_svc.validate_token(token_value)
        await auth_svc.revoke_token(token.id)

        # Get user for OIDC token revocation
        stmt = select(User).where(User.id == token.user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # Record logout
            user.record_logout()

            # Try to revoke OIDC tokens at provider
            try:
                # Find OIDC tokens
                oidc_stmt = select(AuthToken).where(
                    AuthToken.user_id == user.id,
                    AuthToken.token_type == "oidc_access",
                    AuthToken.status == "active",
                )
                oidc_result = await db.execute(oidc_stmt)
                oidc_tokens = oidc_result.scalars().all()

                for oidc_token in oidc_tokens:
                    if (
                        oidc_token.metadata
                        and "oidc_access_token" in oidc_token.metadata
                    ):
                        # Get provider config
                        config = get_provider_config(token.provider_id)

                        # Revoke at provider
                        await oidc_service.revoke_tokens(
                            config, oidc_token.metadata["oidc_access_token"]
                        )

                    # Revoke internal token
                    await auth_svc.revoke_token(oidc_token.id)

            except Exception as e:
                logger.warning(f"Failed to revoke OIDC tokens: {e}")

        await db.commit()

        logger.info(
            "User logged out",
            extra={"user_id": str(token.user_id) if token else "unknown"},
        )

        return {"message": "Logged out successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during logout: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/providers")
async def get_available_providers():
    """Get list of available OIDC providers."""
    providers = []

    if settings.oidc_google_client_id and settings.oidc_google_client_secret:
        providers.append({"name": "google", "display_name": "Google", "icon": "google"})

    if settings.oidc_microsoft_client_id and settings.oidc_microsoft_client_secret:
        providers.append(
            {"name": "microsoft", "display_name": "Microsoft", "icon": "microsoft"}
        )

    return {"providers": providers}

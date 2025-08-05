"""OIDC Service for OAuth2/OpenID Connect integration.

This module provides HIPAA-compliant OIDC authentication services including:
- Provider discovery and configuration
- Authorization code flow
- Token exchange and validation
- User info retrieval
- Session management
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from authlib.integrations.base_client import OAuthError
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.jose import JsonWebKey, jwt
from authlib.oidc.core import CodeIDToken
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AuthenticationError, ValidationError
from models.user import User

logger = logging.getLogger(__name__)


class OIDCConfig(BaseModel):
    """OIDC Provider Configuration."""

    provider_name: str = Field(..., description="Provider name")
    client_id: str = Field(..., description="OAuth2 client ID")
    client_secret: str = Field(..., description="OAuth2 client secret")
    discovery_url: str = Field(..., description="OIDC discovery endpoint")
    redirect_uri: str = Field(..., description="Redirect URI")
    scopes: List[str] = Field(
        default=["openid", "profile", "email"], description="OAuth2 scopes"
    )


class OIDCTokens(BaseModel):
    """OIDC Token Response."""

    access_token: str = Field(..., description="Access token")
    id_token: str = Field(..., description="ID token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: Optional[int] = Field(None, description="Token expiry")
    scope: Optional[str] = Field(None, description="Granted scopes")


class OIDCUserInfo(BaseModel):
    """OIDC User Information."""

    sub: str = Field(..., description="Subject identifier")
    email: str = Field(..., description="Email address")
    email_verified: Optional[bool] = Field(None, description="Email verified")
    name: Optional[str] = Field(None, description="Full name")
    given_name: Optional[str] = Field(None, description="First name")
    family_name: Optional[str] = Field(None, description="Last name")
    picture: Optional[str] = Field(None, description="Profile picture URL")
    locale: Optional[str] = Field(None, description="Locale")


class OIDCService:
    """OIDC Service for OAuth2/OpenID Connect operations."""

    def __init__(self):
        self._discovery_cache: Dict[str, Dict[str, Any]] = {}
        self._jwks_cache: Dict[str, Dict[str, Any]] = {}
        self._client_cache: Dict[str, AsyncOAuth2Client] = {}

    async def get_discovery_document(self, discovery_url: str) -> Dict[str, Any]:
        """Get OIDC discovery document with caching."""
        if discovery_url in self._discovery_cache:
            return self._discovery_cache[discovery_url]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(discovery_url)
                response.raise_for_status()

                discovery_doc = response.json()
                self._discovery_cache[discovery_url] = discovery_doc

                logger.info(
                    "Retrieved OIDC discovery document",
                    extra={"provider_url": discovery_url},
                )

                return discovery_doc

        except httpx.HTTPError as e:
            logger.error(
                "Failed to retrieve OIDC discovery document",
                extra={"error": str(e), "url": discovery_url},
            )
            raise AuthenticationError("Failed to retrieve provider configuration")

    async def get_jwks(self, jwks_uri: str) -> Dict[str, Any]:
        """Get JSON Web Key Set with caching."""
        if jwks_uri in self._jwks_cache:
            return self._jwks_cache[jwks_uri]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_uri)
                response.raise_for_status()

                jwks = response.json()
                self._jwks_cache[jwks_uri] = jwks

                logger.info("Retrieved JWKS", extra={"jwks_uri": jwks_uri})

                return jwks

        except httpx.HTTPError as e:
            logger.error(
                "Failed to retrieve JWKS", extra={"error": str(e), "uri": jwks_uri}
            )
            raise AuthenticationError("Failed to retrieve signing keys")

    async def create_oauth_client(self, config: OIDCConfig) -> AsyncOAuth2Client:
        """Create OAuth2 client with provider configuration."""
        cache_key = f"{config.provider_name}:{config.client_id}"

        if cache_key in self._client_cache:
            return self._client_cache[cache_key]

        # Get discovery document
        discovery_doc = await self.get_discovery_document(config.discovery_url)

        # Create OAuth2 client
        client = AsyncOAuth2Client(
            client_id=config.client_id,
            client_secret=config.client_secret,
            redirect_uri=config.redirect_uri,
            scope=" ".join(config.scopes),
        )

        # Configure endpoints from discovery
        client.server_metadata = discovery_doc

        self._client_cache[cache_key] = client

        logger.info(
            "Created OAuth2 client",
            extra={
                "provider": config.provider_name,
                "client_id": config.client_id[:8] + "...",
            },
        )

        return client

    async def get_authorization_url(
        self, config: OIDCConfig, state: str, nonce: str
    ) -> str:
        """Generate authorization URL for OIDC flow."""
        client = await self.create_oauth_client(config)

        # Generate authorization URL
        authorization_url, _ = client.create_authorization_url(
            client.server_metadata["authorization_endpoint"], state=state, nonce=nonce
        )

        logger.info(
            "Generated authorization URL",
            extra={"provider": config.provider_name, "state": state[:8] + "..."},
        )

        return authorization_url

    async def exchange_code_for_tokens(
        self, config: OIDCConfig, code: str, state: str
    ) -> OIDCTokens:
        """Exchange authorization code for tokens."""
        client = await self.create_oauth_client(config)

        try:
            # Exchange code for tokens
            token_response = await client.fetch_token(
                client.server_metadata["token_endpoint"], code=code, state=state
            )

            tokens = OIDCTokens(
                access_token=token_response["access_token"],
                id_token=token_response["id_token"],
                refresh_token=token_response.get("refresh_token"),
                token_type=token_response.get("token_type", "Bearer"),
                expires_in=token_response.get("expires_in"),
                scope=token_response.get("scope"),
            )

            logger.info(
                "Successfully exchanged code for tokens",
                extra={
                    "provider": config.provider_name,
                    "has_refresh_token": tokens.refresh_token is not None,
                },
            )

            return tokens

        except OAuthError as e:
            logger.error(
                "Failed to exchange code for tokens",
                extra={"error": str(e), "provider": config.provider_name},
            )
            raise AuthenticationError("Token exchange failed")

    async def validate_id_token(
        self, config: OIDCConfig, id_token: str, nonce: str
    ) -> Dict[str, Any]:
        """Validate ID token and return claims."""
        try:
            # Get discovery document and JWKS
            discovery_doc = await self.get_discovery_document(config.discovery_url)
            jwks = await self.get_jwks(discovery_doc["jwks_uri"])

            # Create key set
            key_set = JsonWebKey.import_key_set(jwks)

            # Validate token
            claims = jwt.decode(
                id_token,
                key_set,
                claims_options={
                    "iss": {"essential": True, "value": discovery_doc["issuer"]},
                    "aud": {"essential": True, "value": config.client_id},
                    "nonce": {"essential": True, "value": nonce},
                },
            )

            # Validate with CodeIDToken for additional checks
            code_id_token = CodeIDToken(claims)
            code_id_token.validate(nonce=nonce)

            logger.info(
                "Successfully validated ID token",
                extra={
                    "provider": config.provider_name,
                    "subject": claims.get("sub", "unknown")[:8] + "...",
                },
            )

            return claims

        except Exception as e:
            logger.error(
                "Failed to validate ID token",
                extra={"error": str(e), "provider": config.provider_name},
            )
            raise ValidationError("Invalid ID token")

    async def get_user_info(
        self, config: OIDCConfig, access_token: str
    ) -> OIDCUserInfo:
        """Get user information from OIDC provider."""
        try:
            # Get discovery document
            discovery_doc = await self.get_discovery_document(config.discovery_url)

            # Call userinfo endpoint
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    discovery_doc["userinfo_endpoint"],
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()

                user_data = response.json()

                user_info = OIDCUserInfo(
                    sub=user_data["sub"],
                    email=user_data["email"],
                    email_verified=user_data.get("email_verified"),
                    name=user_data.get("name"),
                    given_name=user_data.get("given_name"),
                    family_name=user_data.get("family_name"),
                    picture=user_data.get("picture"),
                    locale=user_data.get("locale"),
                )

                logger.info(
                    "Retrieved user info",
                    extra={
                        "provider": config.provider_name,
                        "subject": user_info.sub[:8] + "...",
                        "email_verified": user_info.email_verified,
                    },
                )

                return user_info

        except httpx.HTTPError as e:
            logger.error(
                "Failed to retrieve user info",
                extra={"error": str(e), "provider": config.provider_name},
            )
            raise AuthenticationError("Failed to retrieve user information")

    async def refresh_tokens(
        self, config: OIDCConfig, refresh_token: str
    ) -> OIDCTokens:
        """Refresh access tokens using refresh token."""
        client = await self.create_oauth_client(config)

        try:
            # Refresh tokens
            token_response = await client.refresh_token(
                client.server_metadata["token_endpoint"], refresh_token=refresh_token
            )

            tokens = OIDCTokens(
                access_token=token_response["access_token"],
                id_token=token_response.get("id_token", ""),
                refresh_token=token_response.get("refresh_token", refresh_token),
                token_type=token_response.get("token_type", "Bearer"),
                expires_in=token_response.get("expires_in"),
                scope=token_response.get("scope"),
            )

            logger.info(
                "Successfully refreshed tokens",
                extra={"provider": config.provider_name},
            )

            return tokens

        except OAuthError as e:
            logger.error(
                "Failed to refresh tokens",
                extra={"error": str(e), "provider": config.provider_name},
            )
            raise AuthenticationError("Token refresh failed")

    async def find_or_create_user(
        self, session: AsyncSession, user_info: OIDCUserInfo, provider_name: str
    ) -> User:
        """Find existing user or create new one from OIDC info."""
        # Try to find existing user by provider info
        stmt = select(User).where(
            User.provider_name == provider_name, User.provider_id == user_info.sub
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # Update existing user info
            if user_info.email:
                user.email = user_info.email
            if user_info.given_name:
                user.first_name = user_info.given_name
            if user_info.family_name:
                user.last_name = user_info.family_name
            if user_info.name:
                user.display_name = user_info.name
            if user_info.picture:
                user.avatar_url = user_info.picture
            user.last_login_at = datetime.now(timezone.utc)

            logger.info(
                "Updated existing OIDC user",
                extra={"user_id": str(user.id), "provider": provider_name},
            )
        else:
            # Create new user
            user = User(
                email=user_info.email,
                first_name=user_info.given_name,
                last_name=user_info.family_name,
                display_name=user_info.name,
                avatar_url=user_info.picture,
                provider_name=provider_name,
                provider_id=user_info.sub,
                is_active=True,
                roles=["user"],  # Default role
                permissions=["read:profile"],  # Default permissions
                last_login_at=datetime.now(timezone.utc),
            )

            session.add(user)
            await session.flush()  # Get user ID

            logger.info(
                "Created new OIDC user",
                extra={
                    "user_id": str(user.id),
                    "provider": provider_name,
                    "email": user_info.email,
                },
            )

        return user

    async def revoke_tokens(
        self, config: OIDCConfig, token: str, token_type_hint: str = "access_token"
    ) -> bool:
        """Revoke tokens at the OIDC provider."""
        try:
            # Get discovery document
            discovery_doc = await self.get_discovery_document(config.discovery_url)

            # Check if revocation endpoint exists
            revocation_endpoint = discovery_doc.get("revocation_endpoint")
            if not revocation_endpoint:
                logger.warning(
                    "Provider does not support token revocation",
                    extra={"provider": config.provider_name},
                )
                return False

            # Revoke token
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    revocation_endpoint,
                    data={
                        "token": token,
                        "token_type_hint": token_type_hint,
                        "client_id": config.client_id,
                        "client_secret": config.client_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                # RFC 7009: successful revocation returns 200
                success = response.status_code == 200

                if success:
                    logger.info(
                        "Successfully revoked token",
                        extra={"provider": config.provider_name},
                    )
                else:
                    logger.warning(
                        "Token revocation failed",
                        extra={
                            "provider": config.provider_name,
                            "status_code": response.status_code,
                        },
                    )

                return success

        except Exception as e:
            logger.error(
                "Error during token revocation",
                extra={"error": str(e), "provider": config.provider_name},
            )
            return False


# Global OIDC service instance
oidc_service = OIDCService()

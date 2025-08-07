"""Tests for OIDC Service."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from authlib.integrations.base_client import OAuthError

from core.exceptions import AuthenticationError
from services.oidc_service import OIDCConfig, OIDCService, OIDCTokens, OIDCUserInfo


class TestOIDCService:
    """Test cases for OIDCService."""

    @pytest.fixture
    def oidc_service(self):
        """Create OIDCService instance."""
        return OIDCService()

    @pytest.fixture
    def oidc_config(self):
        """Create test OIDC configuration."""
        return OIDCConfig(
            provider_name="test-provider",
            client_id="test-client-id",
            client_secret="test-client-secret",
            discovery_url=("https://provider.com/.well-known/openid_configuration"),
            redirect_uri="https://app.com/callback",
            scopes=["openid", "profile", "email"],
        )

    @pytest.fixture
    def discovery_doc(self):
        """Create test discovery document."""
        return {
            "issuer": "https://provider.com",
            "authorization_endpoint": "https://provider.com/auth",
            "token_endpoint": "https://provider.com/token",
            "userinfo_endpoint": "https://provider.com/userinfo",
            "jwks_uri": "https://provider.com/jwks",
        }

    @pytest.fixture
    def jwks_response(self):
        """Create test JWKS response."""
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": "test-key-id",
                    "n": "test-n",
                    "e": "AQAB",
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_get_discovery_document_success(self, oidc_service, discovery_doc):
        """Test successful discovery document retrieval."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = discovery_doc
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            url = "https://provider.com/.well-known/openid_configuration"
            result = await oidc_service.get_discovery_document(url)

            assert result == discovery_doc
            url = "https://provider.com/.well-known/openid_configuration"
            assert url in oidc_service._discovery_cache

    @pytest.mark.asyncio
    async def test_get_discovery_document_cached(self, oidc_service, discovery_doc):
        """Test cached discovery document retrieval."""
        url = "https://provider.com/.well-known/openid_configuration"
        oidc_service._discovery_cache[url] = discovery_doc

        result = await oidc_service.get_discovery_document(url)
        assert result == discovery_doc

    @pytest.mark.asyncio
    async def test_get_discovery_document_http_error(self, oidc_service):
        """Test discovery document retrieval with HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                httpx.HTTPError("Network error")
            )

            with pytest.raises(
                AuthenticationError,
                match="Failed to retrieve provider configuration",
            ):
                url = "https://provider.com/.well-known/openid_configuration"
                await oidc_service.get_discovery_document(url)

    @pytest.mark.asyncio
    async def test_get_jwks_success(self, oidc_service, jwks_response):
        """Test successful JWKS retrieval."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = jwks_response
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await oidc_service.get_jwks("https://provider.com/jwks")

            assert result == jwks_response
            assert "https://provider.com/jwks" in oidc_service._jwks_cache

    @pytest.mark.asyncio
    async def test_get_jwks_cached(self, oidc_service, jwks_response):
        """Test cached JWKS retrieval."""
        url = "https://provider.com/jwks"
        oidc_service._jwks_cache[url] = jwks_response

        result = await oidc_service.get_jwks(url)
        assert result == jwks_response

    @pytest.mark.asyncio
    async def test_get_jwks_http_error(self, oidc_service):
        """Test JWKS retrieval with HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                httpx.HTTPError("Network error")
            )

            with pytest.raises(
                AuthenticationError, match="Failed to retrieve signing keys"
            ):
                await oidc_service.get_jwks("https://provider.com/jwks")

    @pytest.mark.asyncio
    async def test_create_oauth_client(self, oidc_service, oidc_config, discovery_doc):
        """Test OAuth client creation."""
        with patch.object(
            oidc_service, "get_discovery_document", return_value=discovery_doc
        ):
            with patch("services.oidc_service.AsyncOAuth2Client") as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

                result = await oidc_service.create_oauth_client(oidc_config)

                assert result == mock_client
                mock_client_class.assert_called_once_with(
                    client_id="test-client-id",
                    client_secret="test-client-secret",
                    redirect_uri="https://app.com/callback",
                    scope="openid profile email",
                )

    @pytest.mark.asyncio
    async def test_get_authorization_url(self, oidc_service, oidc_config):
        """Test authorization URL generation."""
        mock_client = MagicMock()
        mock_client.create_authorization_url.return_value = (
            "https://auth.url",
            "state",
        )
        mock_client.server_metadata = {
            "authorization_endpoint": "https://provider.com/auth"
        }

        with patch.object(
            oidc_service, "create_oauth_client", return_value=mock_client
        ):
            result = await oidc_service.get_authorization_url(
                oidc_config, "test-state", "test-nonce"
            )

            assert result == "https://auth.url"
            mock_client.create_authorization_url.assert_called_once_with(
                "https://provider.com/auth",
                state="test-state",
                nonce="test-nonce",
            )

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_success(self, oidc_service, oidc_config):
        """Test successful token exchange."""
        token_response = {
            "access_token": "access-token",
            "id_token": "id-token",
            "refresh_token": "refresh-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid profile email",
        }

        mock_client = AsyncMock()
        mock_client.fetch_token.return_value = token_response
        mock_client.server_metadata = {"token_endpoint": "https://provider.com/token"}

        with patch.object(
            oidc_service, "create_oauth_client", return_value=mock_client
        ):
            result = await oidc_service.exchange_code_for_tokens(
                oidc_config, "auth-code", "test-state"
            )

            assert isinstance(result, OIDCTokens)
            assert result.access_token == "access-token"
            assert result.id_token == "id-token"
            assert result.refresh_token == "refresh-token"

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_oauth_error(
        self, oidc_service, oidc_config
    ):
        """Test token exchange with OAuth error."""
        mock_client = AsyncMock()
        mock_client.fetch_token.side_effect = OAuthError("Invalid code")

        with patch.object(
            oidc_service, "create_oauth_client", return_value=mock_client
        ):
            with pytest.raises(AuthenticationError, match="Token exchange failed"):
                await oidc_service.exchange_code_for_tokens(
                    oidc_config, "invalid-code", "test-state"
                )

    @pytest.mark.asyncio
    async def test_get_user_info_success(
        self, oidc_service, oidc_config, discovery_doc
    ):
        """Test successful user info retrieval."""
        user_data = {
            "sub": "user-123",
            "email": "user@example.com",
            "email_verified": True,
            "name": "Test User",
            "given_name": "Test",
            "family_name": "User",
        }

        with patch.object(
            oidc_service, "get_discovery_document", return_value=discovery_doc
        ):
            with patch("httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.json.return_value = user_data
                mock_response.raise_for_status = MagicMock()

                mock_client.return_value.__aenter__.return_value.get.return_value = (
                    mock_response
                )

                result = await oidc_service.get_user_info(oidc_config, "access-token")

                assert isinstance(result, OIDCUserInfo)
                assert result.sub == "user-123"
                assert result.email == "user@example.com"
                assert result.email_verified is True

    @pytest.mark.asyncio
    async def test_get_user_info_http_error(
        self, oidc_service, oidc_config, discovery_doc
    ):
        """Test user info retrieval with HTTP error."""
        with patch.object(
            oidc_service, "get_discovery_document", return_value=discovery_doc
        ):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get.side_effect = (
                    httpx.HTTPError("Network error")
                )

                with pytest.raises(
                    AuthenticationError,
                    match="Failed to retrieve user information",
                ):
                    await oidc_service.get_user_info(oidc_config, "access-token")

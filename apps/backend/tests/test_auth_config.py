"""Tests for auth configuration module."""

import os
from unittest.mock import patch

import pytest

from config.auth_config import AuthConfig, get_auth_config


class TestAuthConfig:
    """Test cases for AuthConfig class."""

    @pytest.fixture
    def mock_env_vars(self):
        """Mock environment variables for testing."""
        return {
            "AUTH0_DOMAIN": "test-domain.auth0.com",
            "AUTH0_CLIENT_ID": "test-client-id",
            "AUTH0_CLIENT_SECRET": "test-client-secret",
            "AUTH0_AUDIENCE": "test-audience",
            "APP_BASE_URL": "http://localhost:3000",
        }

    @patch.dict(os.environ, {}, clear=True)
    def test_auth_config_initialization_with_env_vars(self, mock_env_vars):
        """Test AuthConfig initialization with environment variables."""
        with patch.dict(os.environ, mock_env_vars):
            config = AuthConfig()

            assert config.auth0_domain == "test-domain.auth0.com"
            assert config.auth0_client_id == "test-client-id"
            assert config.auth0_client_secret == "test-client-secret"
            assert config.auth0_audience == "test-audience"
            assert config.callback_url == "http://localhost:3000/auth/callback"
            assert config.logout_url == "http://localhost:3000/auth/logout"

    @patch.dict(os.environ, {}, clear=True)
    def test_auth_config_initialization_with_defaults(self):
        """Test AuthConfig initialization with default values."""
        with pytest.raises(ValueError):
            AuthConfig()

    def test_get_auth_endpoint(self, mock_env_vars):
        """Test _get_auth_endpoint method."""
        with patch.dict(os.environ, mock_env_vars):
            config = AuthConfig()
            auth_endpoint = config._get_auth_endpoint()

            expected = "https://test-domain.auth0.com/authorize"
            assert auth_endpoint == expected

    def test_get_token_endpoint(self, mock_env_vars):
        """Test _get_token_endpoint method."""
        with patch.dict(os.environ, mock_env_vars):
            config = AuthConfig()
            token_endpoint = config._get_token_endpoint()

            expected = "https://test-domain.auth0.com/oauth/token"
            assert token_endpoint == expected

    def test_get_userinfo_endpoint(self, mock_env_vars):
        """Test _get_userinfo_endpoint method."""
        with patch.dict(os.environ, mock_env_vars):
            config = AuthConfig()
            userinfo_endpoint = config._get_userinfo_endpoint()

            expected = "https://test-domain.auth0.com/userinfo"
            assert userinfo_endpoint == expected

    def test_get_jwks_uri(self, mock_env_vars):
        """Test _get_jwks_uri method."""
        with patch.dict(os.environ, mock_env_vars):
            config = AuthConfig()
            jwks_uri = config._get_jwks_uri()

            expected = "https://test-domain.auth0.com/.well-known/jwks.json"
            assert jwks_uri == expected

    def test_callback_url_property(self, mock_env_vars):
        """Test callback_url property."""
        with patch.dict(os.environ, mock_env_vars):
            config = AuthConfig()
            assert config.callback_url == "http://localhost:3000/auth/callback"

    def test_logout_url_property(self, mock_env_vars):
        """Test logout_url property."""
        with patch.dict(os.environ, mock_env_vars):
            config = AuthConfig()
            assert config.logout_url == "http://localhost:3000/auth/logout"

    def test_get_auth0_logout_url(self, mock_env_vars):
        """Test get_auth0_logout_url method."""
        with patch.dict(os.environ, mock_env_vars):
            config = AuthConfig()
            logout_url = config.get_auth0_logout_url()

            expected = (
                "https://test-domain.auth0.com/v2/logout?"
                "returnTo=http://localhost:3000&client_id=test-client-id"
            )
            assert logout_url == expected

    def test_get_auth0_logout_url_empty_domain(self):
        """Test AuthConfig with empty domain raises ValueError."""
        env_vars = {
            "AUTH0_DOMAIN": "",
            "AUTH0_CLIENT_ID": "test-client-id",
            "AUTH0_CLIENT_SECRET": "test-secret",
            "APP_BASE_URL": "http://localhost:8000",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="AUTH0_DOMAIN"):
                AuthConfig()

    def test_validate_required_settings_all_present(self, mock_env_vars):
        """Test _validate_required_settings with all required settings."""
        with patch.dict(os.environ, mock_env_vars):
            config = AuthConfig()
            # Should not raise any exception
            config._validate_required_settings()

    def test_validate_required_settings_missing_domain(self):
        """Test _validate_required_settings with missing domain."""
        env_vars = {
            "AUTH0_CLIENT_ID": "test-client-id",
            "AUTH0_CLIENT_SECRET": "test-client-secret",
            "AUTH0_AUDIENCE": "test-audience",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="AUTH0_DOMAIN"):
                AuthConfig()

    def test_validate_required_settings_missing_client_id(self):
        """Test _validate_required_settings with missing client ID."""
        env_vars = {
            "AUTH0_DOMAIN": "test-domain.auth0.com",
            "AUTH0_CLIENT_SECRET": "test-client-secret",
            "AUTH0_AUDIENCE": "test-audience",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="AUTH0_CLIENT_ID"):
                AuthConfig()

    def test_validate_required_settings_missing_client_secret(self):
        """Test _validate_required_settings with missing client secret."""
        env_vars = {
            "AUTH0_DOMAIN": "test-domain.auth0.com",
            "AUTH0_CLIENT_ID": "test-client-id",
            "AUTH0_AUDIENCE": "test-audience",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="AUTH0_CLIENT_SECRET"):
                AuthConfig()

    def test_get_auth_config_function(self, mock_env_vars):
        """Test get_auth_config function."""
        with patch.dict(os.environ, mock_env_vars):
            config = get_auth_config()

            assert isinstance(config, AuthConfig)
            assert config.auth0_domain == "test-domain.auth0.com"
            assert config.auth0_client_id == "test-client-id"

    def test_auth_config_with_custom_frontend_url(self):
        """Test AuthConfig with custom app base URL."""
        env_vars = {
            "AUTH0_DOMAIN": "test-domain.auth0.com",
            "AUTH0_CLIENT_ID": "test-client-id",
            "AUTH0_CLIENT_SECRET": "test-client-secret",
            "AUTH0_AUDIENCE": "test-audience",
            "APP_BASE_URL": "https://myapp.com",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = AuthConfig()

            assert config.app_base_url == "https://myapp.com"
            assert config.callback_url == "https://myapp.com/auth/callback"
            assert config.logout_url == "https://myapp.com/auth/logout"

    def test_auth_config_endpoints_with_empty_domain(self):
        """Test endpoint methods with empty domain."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError):
                AuthConfig()

    def test_auth_config_object_creation(self, mock_env_vars):
        """Test AuthConfig object creation."""
        with patch.dict(os.environ, mock_env_vars):
            config = AuthConfig()

            assert config.auth0_domain == "test-domain.auth0.com"

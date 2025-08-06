"""Authentication configuration for OIDC/Auth0 integration."""

import os
from typing import Optional


class AuthConfig:
    """Authentication configuration settings."""

    def __init__(self):
        """Initialize authentication configuration from environment."""
        # Auth0 OIDC Configuration
        self.auth0_domain = os.getenv("AUTH0_DOMAIN", "")
        self.auth0_client_id = os.getenv("AUTH0_CLIENT_ID", "")
        self.auth0_client_secret = os.getenv("AUTH0_CLIENT_SECRET", "")
        self.auth0_audience = os.getenv("AUTH0_AUDIENCE", "")

        # OIDC Configuration (auto-generated from Auth0 domain)
        self.oidc_issuer = self._get_oidc_issuer()
        self.oidc_authorization_endpoint = self._get_auth_endpoint()
        self.oidc_token_endpoint = self._get_token_endpoint()
        self.oidc_userinfo_endpoint = self._get_userinfo_endpoint()
        self.oidc_jwks_uri = self._get_jwks_uri()

        # Application Configuration
        self.app_base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")

        # JWT Configuration
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "RS256")
        self.jwt_access_token_expire_minutes = int(
            os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )
        self.jwt_refresh_token_expire_days = int(
            os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
        )

        # Session Configuration
        self.session_secret_key = os.getenv(
            "SESSION_SECRET_KEY", "your-secret-key-change-in-production"
        )
        self.session_cookie_name = os.getenv("SESSION_COOKIE_NAME", "pms_session")
        self.session_cookie_max_age = int(os.getenv("SESSION_COOKIE_MAX_AGE", "3600"))

        # Security Configuration
        cors_origins_str = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:8000"
        )
        self.cors_origins = [
            origin.strip() for origin in cors_origins_str.split(",")
        ]

        # HIPAA Compliance
        self.enable_audit_logging = (
            os.getenv("ENABLE_AUDIT_LOGGING", "true").lower() == "true"
        )
        self.audit_log_retention_days = int(
            os.getenv("AUDIT_LOG_RETENTION_DAYS", "2555")  # 7 years
        )

        # Validate required settings
        self._validate_required_settings()

    def _get_oidc_issuer(self) -> Optional[str]:
        """Get OIDC issuer URL."""
        if self.auth0_domain:
            return f"https://{self.auth0_domain}/"
        return None

    def _get_auth_endpoint(self) -> Optional[str]:
        """Get OIDC authorization endpoint."""
        if self.auth0_domain:
            return f"https://{self.auth0_domain}/authorize"
        return None

    def _get_token_endpoint(self) -> Optional[str]:
        """Get OIDC token endpoint."""
        if self.auth0_domain:
            return f"https://{self.auth0_domain}/oauth/token"
        return None

    def _get_userinfo_endpoint(self) -> Optional[str]:
        """Get OIDC userinfo endpoint."""
        if self.auth0_domain:
            return f"https://{self.auth0_domain}/userinfo"
        return None

    def _get_jwks_uri(self) -> Optional[str]:
        """Get OIDC JWKS URI."""
        if self.auth0_domain:
            return f"https://{self.auth0_domain}/.well-known/jwks.json"
        return None

    @property
    def callback_url(self) -> str:
        """Get the OAuth callback URL."""
        return f"{self.app_base_url}/auth/callback"

    @property
    def logout_url(self) -> str:
        """Get the logout redirect URL."""
        return f"{self.app_base_url}/auth/logout"

    def get_auth0_logout_url(self) -> str:
        """Get the Auth0 logout URL with return URL."""
        return (
            f"https://{self.auth0_domain}/v2/logout?"
            f"returnTo={self.app_base_url}&client_id={self.auth0_client_id}"
        )

    def _validate_required_settings(self) -> None:
        """Validate required Auth0 settings."""
        if not self.auth0_domain:
            raise ValueError(
                "AUTH0_DOMAIN environment variable is required"
            )

        if not self.auth0_client_id:
            raise ValueError(
                "AUTH0_CLIENT_ID environment variable is required"
            )

        if not self.auth0_client_secret:
            raise ValueError(
                "AUTH0_CLIENT_SECRET environment variable is required"
            )


# Global instance will be created when needed
auth_config = None


def get_auth_config() -> AuthConfig:
    """Get or create the global auth config instance."""
    global auth_config
    if auth_config is None:
        auth_config = AuthConfig()
    return auth_config

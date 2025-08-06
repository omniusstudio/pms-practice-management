"""Application configuration management.

This module provides centralized configuration management for the PMS
application, including environment variable handling and settings validation.
"""

from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.env_loader import load_environment_config


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, env_prefix=""
    )

    def __init__(self, **kwargs):
        """Initialize settings with environment-specific configuration."""
        # Load environment-specific .env file before initializing
        load_environment_config()
        super().__init__(**kwargs)

    # Application
    app_name: str = Field(default="PMS Backend", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # Security
    secret_key: str = Field(alias="SECRET_KEY")
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=30, alias="JWT_EXPIRE_MINUTES")

    # Database
    database_url: str = Field(alias="DATABASE_URL")
    postgres_user: Optional[str] = Field(None, alias="POSTGRES_USER")
    postgres_password: Optional[str] = Field(None, alias="POSTGRES_PASSWORD")
    db_host: Optional[str] = Field(None, alias="DB_HOST")
    db_port: Optional[str] = Field(None, alias="DB_PORT")
    db_name: Optional[str] = Field(None, alias="DB_NAME")
    db_user: Optional[str] = Field(None, alias="DB_USER")
    db_password: Optional[str] = Field(None, alias="DB_PASSWORD")

    # Redis
    redis_url: str = Field(alias="REDIS_URL")

    # AWS Configuration
    aws_access_key_id: Optional[str] = Field(None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(None, alias="AWS_SECRET_ACCESS_KEY")
    aws_region: Optional[str] = Field(None, alias="AWS_REGION")

    # CORS
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    # Frontend Configuration
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")

    # Session Configuration
    session_secret_key: str = Field(
        default="dev-secret-key", alias="SESSION_SECRET_KEY"
    )
    session_max_age: int = Field(default=3600, alias="SESSION_MAX_AGE")

    # Audit Configuration
    enable_audit_logging: bool = Field(default=True, alias="ENABLE_AUDIT_LOGGING")
    audit_log_retention_days: int = Field(
        default=2555, alias="AUDIT_LOG_RETENTION_DAYS"
    )

    # Auth0 Configuration
    auth0_domain: Optional[str] = Field(None, alias="AUTH0_DOMAIN")
    auth0_client_id: Optional[str] = Field(None, alias="AUTH0_CLIENT_ID")
    auth0_client_secret: Optional[str] = Field(None, alias="AUTH0_CLIENT_SECRET")
    auth0_audience: Optional[str] = Field(None, alias="AUTH0_AUDIENCE")
    redirect_uri: Optional[str] = Field(None, alias="REDIRECT_URI")
    logout_redirect_uri: Optional[str] = Field(None, alias="LOGOUT_REDIRECT_URI")

    # OIDC Configuration
    oidc_google_client_id: Optional[str] = Field(None, alias="OIDC_GOOGLE_CLIENT_ID")
    oidc_google_client_secret: Optional[str] = Field(
        None, alias="OIDC_GOOGLE_CLIENT_SECRET"
    )
    oidc_microsoft_client_id: Optional[str] = Field(
        None, alias="OIDC_MICROSOFT_CLIENT_ID"
    )
    oidc_microsoft_client_secret: Optional[str] = Field(
        None, alias="OIDC_MICROSOFT_CLIENT_SECRET"
    )
    oidc_redirect_uri: str = Field(
        default="http://localhost:8000/auth/callback",
        alias="OIDC_REDIRECT_URI",
    )

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: Optional[str] = Field(None, alias="LOG_FORMAT")

    # Integration Service Configuration
    enable_mock_edi: bool = Field(default=True, alias="ENABLE_MOCK_EDI")
    enable_mock_payments: bool = Field(default=True, alias="ENABLE_MOCK_PAYMENTS")
    enable_mock_video: bool = Field(default=True, alias="ENABLE_MOCK_VIDEO")

    # External Service URLs
    edi_service_url: str = Field(
        default="http://localhost:8000/mock/edi", alias="EDI_SERVICE_URL"
    )
    stripe_api_key: Optional[str] = Field(None, alias="STRIPE_API_KEY")
    stripe_webhook_secret: Optional[str] = Field(None, alias="STRIPE_WEBHOOK_SECRET")
    video_service_url: str = Field(
        default="http://localhost:8000/mock/video", alias="VIDEO_SERVICE_URL"
    )
    video_api_key: Optional[str] = Field(None, alias="VIDEO_API_KEY")

    # Additional Configuration
    allowed_origins: Optional[str] = Field(None, alias="ALLOWED_ORIGINS")
    trusted_hosts: Optional[str] = Field(None, alias="TRUSTED_HOSTS")
    prometheus_enabled: Optional[str] = Field(None, alias="PROMETHEUS_ENABLED")
    metrics_port: Optional[str] = Field(None, alias="METRICS_PORT")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, list):
            return ",".join(v)
        return v

    def get_cors_origins_list(self):
        """Get CORS origins as a list."""
        origins = self.__dict__.get("cors_origins", "")
        if isinstance(origins, str) and origins:
            return [origin.strip() for origin in origins.split(",")]
        return []


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

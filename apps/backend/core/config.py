"""Application configuration management.

This module provides centralized configuration management for the PMS
application, including environment variable handling and settings validation.
"""

from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, env_prefix=""
    )

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

    # Redis
    redis_url: str = Field(alias="REDIS_URL")

    # CORS
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

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
        default="http://localhost:8000/auth/callback", alias="OIDC_REDIRECT_URI"
    )

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, list):
            return ",".join(v)
        return v

    @property
    def cors_origins_list(self):
        """Get CORS origins as a list."""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return self.cors_origins


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

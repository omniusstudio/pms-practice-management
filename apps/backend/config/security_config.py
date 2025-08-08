"""Security configuration for HIPAA-compliant encryption in-transit/at-rest."""

import os
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TLSVersion(str, Enum):
    """Supported TLS versions."""

    TLS_1_2 = "TLSv1.2"
    TLS_1_3 = "TLSv1.3"


class SecurityConfig(BaseModel):
    """Security configuration for encryption in-transit and at-rest."""

    # TLS Configuration
    tls_min_version: TLSVersion = Field(default=TLSVersion.TLS_1_2)
    tls_ciphers: List[str] = Field(
        default_factory=lambda: [
            "ECDHE-RSA-AES256-GCM-SHA384",
            "ECDHE-RSA-AES128-GCM-SHA256",
            "ECDHE-RSA-AES256-SHA384",
            "ECDHE-RSA-AES128-SHA256",
            "AES256-GCM-SHA384",
            "AES128-GCM-SHA256",
        ]
    )

    # HSTS Configuration
    hsts_max_age: int = Field(default=31536000)  # 1 year
    hsts_include_subdomains: bool = Field(default=True)
    hsts_preload: bool = Field(default=True)

    # Cookie Security
    cookie_secure: bool = Field(default=True)
    cookie_httponly: bool = Field(default=True)
    cookie_samesite: str = Field(default="Strict")
    session_cookie_name: str = Field(default="pms_session")
    session_cookie_max_age: int = Field(default=3600)  # 1 hour

    # SSL Certificate Configuration
    ssl_cert_path: Optional[str] = Field(default=None)
    ssl_key_path: Optional[str] = Field(default=None)
    ssl_ca_path: Optional[str] = Field(default=None)

    # Database Encryption
    db_ssl_mode: str = Field(default="require")
    db_ssl_cert: Optional[str] = Field(default=None)
    db_ssl_key: Optional[str] = Field(default=None)
    db_ssl_ca: Optional[str] = Field(default=None)

    # Key Management
    kms_provider: str = Field(default="aws_kms")
    kms_key_id: Optional[str] = Field(default=None)
    kms_region: str = Field(default="us-east-1")
    key_rotation_enabled: bool = Field(default=True)
    key_rotation_interval_days: int = Field(default=90)

    # Security Headers
    security_headers: Dict[str, str] = Field(
        default_factory=lambda: {
            "X-Frame-Options": "SAMEORIGIN",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": (
                "default-src 'self'; script-src 'self' 'unsafe-inline' "
                "'unsafe-eval'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; font-src 'self' data:; "
                "connect-src 'self' https:; frame-ancestors 'self';"
            ),
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }
    )

    class Config:
        env_prefix = "SECURITY_"


def get_security_config() -> SecurityConfig:
    """Get security configuration from environment variables."""
    return SecurityConfig(
        # TLS Configuration
        tls_min_version=TLSVersion(os.getenv("SECURITY_TLS_MIN_VERSION", "TLSv1.2")),
        # HSTS Configuration
        hsts_max_age=int(os.getenv("SECURITY_HSTS_MAX_AGE", "31536000")),
        hsts_include_subdomains=(
            os.getenv("SECURITY_HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true"
        ),
        hsts_preload=(os.getenv("SECURITY_HSTS_PRELOAD", "true").lower() == "true"),
        # Cookie Security
        cookie_secure=(os.getenv("SECURITY_COOKIE_SECURE", "true").lower() == "true"),
        cookie_httponly=(
            os.getenv("SECURITY_COOKIE_HTTPONLY", "true").lower() == "true"
        ),
        cookie_samesite=os.getenv("SECURITY_COOKIE_SAMESITE", "Strict"),
        session_cookie_name=(os.getenv("SECURITY_SESSION_COOKIE_NAME", "pms_session")),
        session_cookie_max_age=(
            int(os.getenv("SECURITY_SESSION_COOKIE_MAX_AGE", "3600"))
        ),
        # SSL Certificate Configuration
        ssl_cert_path=os.getenv("SECURITY_SSL_CERT_PATH"),
        ssl_key_path=os.getenv("SECURITY_SSL_KEY_PATH"),
        ssl_ca_path=os.getenv("SECURITY_SSL_CA_PATH"),
        # Database Encryption
        db_ssl_mode=os.getenv("SECURITY_DB_SSL_MODE", "require"),
        db_ssl_cert=os.getenv("SECURITY_DB_SSL_CERT"),
        db_ssl_key=os.getenv("SECURITY_DB_SSL_KEY"),
        db_ssl_ca=os.getenv("SECURITY_DB_SSL_CA"),
        # Key Management
        kms_provider=os.getenv("SECURITY_KMS_PROVIDER", "aws_kms"),
        kms_key_id=os.getenv("SECURITY_KMS_KEY_ID"),
        kms_region=os.getenv("SECURITY_KMS_REGION", "us-east-1"),
        key_rotation_enabled=(
            os.getenv("SECURITY_KEY_ROTATION_ENABLED", "true").lower() == "true"
        ),
        key_rotation_interval_days=(
            int(os.getenv("SECURITY_KEY_ROTATION_INTERVAL_DAYS", "90"))
        ),
    )


def get_hsts_header(config: SecurityConfig) -> str:
    """Generate HSTS header value."""
    hsts_value = f"max-age={config.hsts_max_age}"

    if config.hsts_include_subdomains:
        hsts_value += "; includeSubDomains"

    if config.hsts_preload:
        hsts_value += "; preload"

    return hsts_value


def get_database_ssl_params(config: SecurityConfig) -> Dict[str, str]:
    """Generate database SSL connection parameters."""
    ssl_params = {"sslmode": config.db_ssl_mode}

    if config.db_ssl_cert:
        ssl_params["sslcert"] = config.db_ssl_cert

    if config.db_ssl_key:
        ssl_params["sslkey"] = config.db_ssl_key

    if config.db_ssl_ca:
        ssl_params["sslrootcert"] = config.db_ssl_ca

    return ssl_params

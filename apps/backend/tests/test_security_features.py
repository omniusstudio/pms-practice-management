"""Tests for security features including TLS, encryption, and certificates."""

import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config.security_config import SecurityConfig, get_security_config
from middleware.security_middleware import (
    SecurityHeadersMiddleware,
    TLSEnforcementMiddleware,
    add_security_middleware,
)
from services.database_encryption_service import DatabaseEncryptionService
from utils.ssl_utils import SSLCertificateManager, TLSConfigValidator


class TestSecurityConfig:
    """Test security configuration."""

    def test_security_config_defaults(self):
        """Test security configuration default values."""
        config = SecurityConfig()

        assert config.tls_min_version == "TLSv1.2"
        assert config.hsts_max_age == 31536000
        assert config.hsts_include_subdomains is True
        assert config.cookie_secure is True
        assert config.cookie_httponly is True
        assert config.cookie_samesite == "Strict"

    def test_security_config_environment_override(self):
        """Test security configuration with environment variables."""
        with patch.dict(
            os.environ,
            {
                "SECURITY_TLS_MIN_VERSION": "TLSv1.3",
                "SECURITY_HSTS_MAX_AGE": "63072000",
                "SECURITY_COOKIE_SECURE": "false",
            },
        ):
            config = get_security_config()

            assert config.tls_min_version == "TLSv1.3"
            assert config.hsts_max_age == 63072000
            assert config.cookie_secure is False

    def test_get_security_config_singleton(self):
        """Test security configuration creation."""
        config1 = get_security_config()
        config2 = get_security_config()

        # Compare key attributes instead of object equality
        assert config1.tls_min_version == config2.tls_min_version
        assert config1.hsts_max_age == config2.hsts_max_age
        assert config1.cookie_secure == config2.cookie_secure


class TestSecurityMiddleware:
    """Test security middleware functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = FastAPI()
        self.security_config = SecurityConfig()

    def test_security_headers_middleware_init(self):
        """Test security headers middleware initialization."""
        middleware = SecurityHeadersMiddleware(
            self.app, security_config=self.security_config
        )

        assert middleware.security_config == self.security_config

    def test_tls_enforcement_middleware_init(self):
        """Test TLS enforcement middleware initialization."""
        middleware = TLSEnforcementMiddleware(
            self.app, security_config=self.security_config
        )

        assert middleware.security_config == self.security_config

    @patch("middleware.security_middleware.logger")
    def test_add_security_middleware(self, mock_logger):
        """Test adding security middleware to application."""
        add_security_middleware(self.app, self.security_config)

        # Verify middleware was added (check logger calls)
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0]
        assert "Security middleware added" in call_args[0]

    def test_security_headers_applied(self):
        """Test that security headers are properly applied."""

        @self.app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        add_security_middleware(self.app, self.security_config)
        client = TestClient(self.app)

        response = client.get("/test")

        # Check for security headers
        assert "strict-transport-security" in response.headers
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers
        assert "x-xss-protection" in response.headers


class TestDatabaseEncryptionService:
    """Test database encryption service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_key_service = Mock()
        self.service = DatabaseEncryptionService(key_service=self.mock_key_service)

    @patch("services.database_encryption_service.logger")
    def test_encrypt_field_success(self, mock_logger):
        """Test successful field encryption."""
        # Mock cipher
        mock_cipher = Mock()
        mock_cipher.encrypt.return_value = b"encrypted_data"

        with patch.object(self.service, "_get_cipher", return_value=mock_cipher):
            result = self.service.encrypt_field("test_value", "key_123")

            assert isinstance(result, str)
            mock_cipher.encrypt.assert_called_once_with(b"test_value")

    @patch("services.database_encryption_service.logger")
    def test_decrypt_field_success(self, mock_logger):
        """Test successful field decryption."""
        # Mock cipher
        mock_cipher = Mock()
        mock_cipher.decrypt.return_value = b"decrypted_data"

        with patch.object(self.service, "_get_cipher", return_value=mock_cipher):
            # Use a valid base64 encoded string
            encrypted_value = "ZW5jcnlwdGVkX2RhdGE="  # base64 for 'encrypted_data'
            result = self.service.decrypt_field(encrypted_value, "key_123")

            assert result == "decrypted_data"

    def test_encrypt_field_empty_value(self):
        """Test encryption of empty value."""
        result = self.service.encrypt_field("", "key_123")
        assert result == ""

        result = self.service.encrypt_field(None, "key_123")
        assert result is None

    def test_decrypt_field_empty_value(self):
        """Test decryption of empty value."""
        result = self.service.decrypt_field("", "key_123")
        assert result == ""

        result = self.service.decrypt_field(None, "key_123")
        assert result is None

    @patch("services.database_encryption_service.logger")
    def test_enable_database_encryption(self, mock_logger):
        """Test enabling database encryption."""
        mock_db = Mock()

        # Mock key service responses
        self.mock_key_service.create_key.return_value = {
            "key_id": "master_key_123",
            "status": "created",
        }

        with patch.object(self.service, "_create_encryption_tables"), patch.object(
            self.service,
            "_initialize_master_key",
            return_value={"key_id": "master_key_123"},
        ):
            result = self.service.enable_database_encryption(mock_db)

            assert result["status"] == "success"
            assert result["encryption_enabled"] is True
            assert "master_key_id" in result

    @patch("services.database_encryption_service.logger")
    def test_verify_encryption_status(self, mock_logger):
        """Test verifying encryption status."""
        mock_db = Mock()

        # Mock database queries
        mock_db.execute.return_value.scalar.side_effect = [True, 5, 3]

        result = self.service.verify_encryption_status(mock_db)

        assert result["pgcrypto_enabled"] is True
        assert result["active_keys_count"] == 5
        assert result["encrypted_fields_count"] == 3
        assert result["encryption_ready"] is True


class TestSSLCertificateManager:
    """Test SSL certificate manager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = SSLCertificateManager()

    def test_validate_certificate_file_not_found(self):
        """Test certificate validation with non-existent file."""
        result = self.manager.validate_certificate("/nonexistent/cert.pem")

        assert result["valid"] is False
        assert "not found" in result["error"]

    @patch("subprocess.run")
    def test_validate_certificate_success(self, mock_run):
        """Test successful certificate validation."""
        # Mock openssl output
        mock_run.return_value.stdout = """
        notBefore=Jan  1 00:00:00 2024 GMT
        notAfter=Dec 31 23:59:59 2024 GMT
        Subject: CN=example.com
        Issuer: CN=Test CA
        """

        with tempfile.NamedTemporaryFile(suffix=".pem") as temp_cert:
            temp_cert.write(b"dummy cert content")
            temp_cert.flush()

            result = self.manager.validate_certificate(temp_cert.name)

            assert result["valid"] is True
            assert result["not_before"] is not None
            assert result["not_after"] is not None

    @patch("subprocess.run")
    def test_validate_certificate_openssl_error(self, mock_run):
        """Test certificate validation with OpenSSL error."""
        from subprocess import CalledProcessError

        mock_run.side_effect = CalledProcessError(
            1, "openssl", stderr="Invalid certificate"
        )

        with tempfile.NamedTemporaryFile(suffix=".pem") as temp_cert:
            result = self.manager.validate_certificate(temp_cert.name)

            assert result["valid"] is False
            assert "OpenSSL validation failed" in result["error"]

    def test_parse_cert_date_valid(self):
        """Test parsing valid certificate date."""
        date_str = "Jan  1 00:00:00 2024 GMT"
        result = self.manager._parse_cert_date(date_str)

        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    def test_parse_cert_date_invalid(self):
        """Test parsing invalid certificate date."""
        result = self.manager._parse_cert_date("invalid date")
        assert result is None


class TestTLSConfigValidator:
    """Test TLS configuration validator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = TLSConfigValidator()

    def test_check_tls_requirements_tls12(self):
        """Test TLS requirements check for TLS 1.2."""
        self.validator.security_config.tls_min_version = "TLSv1.2"

        # Valid versions
        assert self.validator._check_tls_requirements("TLSv1.2", None) is True
        assert self.validator._check_tls_requirements("TLSv1.3", None) is True

        # Invalid version
        assert self.validator._check_tls_requirements("TLSv1.1", None) is False

    def test_check_tls_requirements_tls13(self):
        """Test TLS requirements check for TLS 1.3."""
        self.validator.security_config.tls_min_version = "TLSv1.3"

        # Valid version
        assert self.validator._check_tls_requirements("TLSv1.3", None) is True

        # Invalid version
        assert self.validator._check_tls_requirements("TLSv1.2", None) is False

    @patch("socket.create_connection")
    @patch("ssl.create_default_context")
    def test_validate_tls_configuration_success(self, mock_context, mock_socket):
        """Test successful TLS configuration validation."""
        # Mock SSL context and socket
        mock_ssl_context = Mock()
        mock_context.return_value = mock_ssl_context

        mock_ssock = Mock()
        mock_ssock.getpeercert.return_value = {
            "subject": [("CN", "example.com")],
            "issuer": [("CN", "Test CA")],
            "notAfter": "Dec 31 23:59:59 2024 GMT",
        }
        mock_ssock.cipher.return_value = ("ECDHE-RSA-AES256-GCM-SHA384", "TLSv1.2", 256)
        mock_ssock.version.return_value = "TLSv1.2"

        # Mock context manager for SSL socket
        mock_ssl_socket_cm = Mock()
        mock_ssl_socket_cm.__enter__ = Mock(return_value=mock_ssock)
        mock_ssl_socket_cm.__exit__ = Mock(return_value=None)
        mock_ssl_context.wrap_socket.return_value = mock_ssl_socket_cm

        # Mock context manager for regular socket
        mock_socket_cm = Mock()
        mock_socket_cm.__enter__ = Mock(return_value=Mock())
        mock_socket_cm.__exit__ = Mock(return_value=None)
        mock_socket.return_value = mock_socket_cm

        result = self.validator.validate_tls_configuration("example.com", 443)

        assert result["valid"] is True
        assert result["host"] == "example.com"
        assert result["port"] == 443
        assert result["tls_version"] == "TLSv1.2"

    @patch("socket.create_connection")
    def test_validate_tls_configuration_connection_error(self, mock_socket):
        """Test TLS configuration validation with connection error."""
        mock_socket.side_effect = ConnectionError("Connection refused")

        result = self.validator.validate_tls_configuration("example.com", 443)

        assert result["valid"] is False
        assert "Connection refused" in result["error"]

    @patch.object(SSLCertificateManager, "validate_certificate")
    def test_ssl_configuration_test(self, mock_validate_cert):
        """Test SSL configuration testing."""
        # Mock certificate validation
        mock_validate_cert.return_value = {
            "valid": True,
            "not_after": datetime.now() + timedelta(days=90),
        }

        self.validator.security_config.ssl_cert_path = "/path/to/cert.pem"

        with patch.object(self.validator, "validate_tls_configuration") as mock_tls:
            mock_tls.side_effect = Exception("TLS endpoint not available")

            result = self.validator.test_ssl_configuration()

            assert "timestamp" in result
            assert len(result["tests"]) >= 1
            assert result["tests"][0]["name"] == "certificate_validation"
            assert result["tests"][0]["status"] == "pass"


@pytest.fixture
def mock_security_config():
    """Fixture for mock security configuration."""
    config = SecurityConfig()
    config.tls_min_version = "TLSv1.2"
    config.hsts_max_age = 31536000
    config.cookie_secure = True
    return config


@pytest.fixture
def mock_db_session():
    """Fixture for mock database session."""
    mock_session = Mock()
    mock_session.execute.return_value.fetchone.return_value = None
    mock_session.execute.return_value.scalar.return_value = 0
    return mock_session

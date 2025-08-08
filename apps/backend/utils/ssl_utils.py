"""SSL/TLS utilities for certificate management and HTTPS enforcement."""

import logging
import socket
import ssl
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from config.security_config import get_security_config

logger = logging.getLogger(__name__)


class SSLCertificateManager:
    """Manager for SSL certificate operations and validation."""

    def __init__(self):
        self.security_config = get_security_config()

    def validate_certificate(self, cert_path: str) -> Dict[str, Any]:
        """Validate SSL certificate and return status information."""
        try:
            cert_file = Path(cert_path)
            if not cert_file.exists():
                return {
                    "valid": False,
                    "error": "Certificate file not found",
                    "path": cert_path,
                }

            # Use openssl to get certificate information
            result = subprocess.run(
                [
                    "openssl",
                    "x509",
                    "-in",
                    cert_path,
                    "-text",
                    "-noout",
                    "-dates",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            cert_info = self._parse_certificate_info(result.stdout)

            logger.info(
                "Certificate validation completed",
                extra={
                    "cert_path": cert_path,
                    "valid": cert_info["valid"],
                    "expires_at": cert_info.get("not_after"),
                },
            )

            return cert_info

        except subprocess.CalledProcessError as e:
            logger.error(
                "Certificate validation failed",
                extra={
                    "cert_path": cert_path,
                    "error": e.stderr,
                },
            )
            return {
                "valid": False,
                "error": f"OpenSSL validation failed: {e.stderr}",
                "path": cert_path,
            }
        except Exception as e:
            logger.error(
                "Certificate validation error",
                extra={
                    "cert_path": cert_path,
                    "error": str(e),
                },
                exc_info=True,
            )
            return {
                "valid": False,
                "error": str(e),
                "path": cert_path,
            }

    def _parse_certificate_info(self, cert_text: str) -> Dict[str, Any]:
        """Parse certificate information from openssl output."""
        info = {
            "valid": True,
            "not_before": None,
            "not_after": None,
            "subject": None,
            "issuer": None,
            "expires_soon": False,
        }

        lines = cert_text.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("notBefore="):
                date_str = line.replace("notBefore=", "")
                info["not_before"] = self._parse_cert_date(date_str)
            elif line.startswith("notAfter="):
                date_str = line.replace("notAfter=", "")
                info["not_after"] = self._parse_cert_date(date_str)
                # Check if certificate expires within 30 days
                if info["not_after"]:
                    expires_in = info["not_after"] - datetime.now()
                    info["expires_soon"] = expires_in.days <= 30
            elif "Subject:" in line:
                info["subject"] = line.split("Subject:", 1)[1].strip()
            elif "Issuer:" in line:
                info["issuer"] = line.split("Issuer:", 1)[1].strip()

        return info

    def _parse_cert_date(self, date_str: str) -> Optional[datetime]:
        """Parse certificate date string to datetime object."""
        try:
            # OpenSSL date format: "Jan 1 00:00:00 2024 GMT"
            return datetime.strptime(date_str.strip(), "%b %d %H:%M:%S %Y %Z")
        except ValueError:
            logger.warning(
                "Failed to parse certificate date",
                extra={"date_string": date_str},
            )
            return None

    def check_certificate_expiry(self, cert_path: str) -> Dict[str, Any]:
        """Check if certificate is expiring soon."""
        cert_info = self.validate_certificate(cert_path)

        if not cert_info["valid"]:
            return cert_info

        not_after = cert_info.get("not_after")
        if not not_after:
            return {
                "valid": False,
                "error": "Could not determine certificate expiry",
            }

        now = datetime.now()
        expires_in = not_after - now

        result = {
            "valid": True,
            "expires_at": not_after.isoformat(),
            "expires_in_days": expires_in.days,
            "expires_soon": expires_in.days <= 30,
            "expired": expires_in.days < 0,
        }

        if result["expires_soon"] or result["expired"]:
            logger.warning(
                "Certificate expiring soon or expired",
                extra=result,
            )

        return result


class TLSConfigValidator:
    """Validator for TLS configuration and security settings."""

    def __init__(self):
        self.security_config = get_security_config()

    def validate_tls_configuration(self, host: str, port: int = 443) -> Dict[str, Any]:
        """Validate TLS configuration for a given host and port."""
        try:
            # Create SSL context with security requirements
            context = ssl.create_default_context()
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED

            # Set minimum TLS version
            if self.security_config.tls_min_version == "TLSv1.3":
                context.minimum_version = ssl.TLSVersion.TLSv1_3
            else:
                context.minimum_version = ssl.TLSVersion.TLSv1_2

            # Test connection
            with socket.create_connection((host, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()

            result = {
                "valid": True,
                "host": host,
                "port": port,
                "tls_version": version,
                "cipher_suite": cipher[0] if cipher else None,
                "certificate_subject": cert.get("subject", []),
                "certificate_issuer": cert.get("issuer", []),
                "certificate_expires": cert.get("notAfter"),
                "meets_requirements": self._check_tls_requirements(version, cipher),
            }

            logger.info(
                "TLS configuration validated",
                extra={
                    "host": host,
                    "port": port,
                    "tls_version": version,
                    "valid": result["valid"],
                },
            )

            return result

        except Exception as e:
            logger.error(
                "TLS validation failed",
                extra={
                    "host": host,
                    "port": port,
                    "error": str(e),
                },
                exc_info=True,
            )
            return {
                "valid": False,
                "host": host,
                "port": port,
                "error": str(e),
            }

    def _check_tls_requirements(self, version: str, cipher: tuple) -> bool:
        """Check if TLS configuration meets security requirements."""
        # Check minimum TLS version
        if self.security_config.tls_min_version == "TLSv1.3":
            if version != "TLSv1.3":
                return False
        elif version not in ["TLSv1.2", "TLSv1.3"]:
            return False

        # Check cipher suite if specified
        if cipher and self.security_config.tls_ciphers:
            cipher_name = cipher[0] if isinstance(cipher, tuple) else cipher
            return cipher_name in self.security_config.tls_ciphers

        return True

    def test_ssl_configuration(self) -> Dict[str, Any]:
        """Test SSL configuration against security requirements."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "overall_status": "pass",
        }

        # Test certificate validation if paths are configured
        cert_manager = SSLCertificateManager()

        if self.security_config.ssl_cert_path:
            cert_result = cert_manager.validate_certificate(
                self.security_config.ssl_cert_path
            )
            results["tests"].append(
                {
                    "name": "certificate_validation",
                    "status": "pass" if cert_result["valid"] else "fail",
                    "details": cert_result,
                }
            )

            if not cert_result["valid"]:
                results["overall_status"] = "fail"

        # Test TLS configuration for localhost (development)
        try:
            tls_result = self.validate_tls_configuration("localhost", 8443)
            results["tests"].append(
                {
                    "name": "tls_configuration",
                    "status": "pass" if tls_result["valid"] else "fail",
                    "details": tls_result,
                }
            )

            if not tls_result["valid"]:
                results["overall_status"] = "fail"

        except Exception as e:
            results["tests"].append(
                {
                    "name": "tls_configuration",
                    "status": "skip",
                    "details": {
                        "error": str(e),
                        "reason": "TLS endpoint not available",
                    },
                }
            )

        logger.info(
            "SSL configuration test completed",
            extra={
                "overall_status": results["overall_status"],
                "tests_count": len(results["tests"]),
            },
        )

        return results


def get_ssl_certificate_manager() -> SSLCertificateManager:
    """Get SSL certificate manager instance."""
    return SSLCertificateManager()


def get_tls_config_validator() -> TLSConfigValidator:
    """Get TLS configuration validator instance."""
    return TLSConfigValidator()

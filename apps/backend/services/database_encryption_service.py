"""Database encryption service for HIPAA-compliant data at rest."""

import base64
import logging
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import text
from sqlalchemy.orm import Session

from config.security_config import get_security_config
from services.encryption_key_service import EncryptionKeyService

logger = logging.getLogger(__name__)


class DatabaseEncryptionService:
    """Service for managing database encryption at rest."""

    def __init__(self, key_service: Optional[EncryptionKeyService] = None):
        self.security_config = get_security_config()
        self.key_service = key_service or EncryptionKeyService()
        self._cipher_cache: Dict[str, Fernet] = {}

    def enable_database_encryption(self, db: Session) -> Dict[str, Any]:
        """Enable database encryption features."""
        try:
            # Enable pgcrypto extension if not already enabled
            db.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))

            # Create encryption key table if not exists
            self._create_encryption_tables(db)

            # Initialize master encryption key
            master_key = self._initialize_master_key(db)

            logger.info(
                "Database encryption enabled successfully",
                extra={
                    "encryption_enabled": True,
                    "kms_provider": self.security_config.kms_provider,
                    "key_rotation_enabled": (self.security_config.key_rotation_enabled),
                },
            )

            return {
                "status": "success",
                "encryption_enabled": True,
                "master_key_id": master_key["key_id"],
                "kms_provider": self.security_config.kms_provider,
            }

        except Exception as e:
            logger.error(
                "Failed to enable database encryption",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    def _create_encryption_tables(self, db: Session) -> None:
        """Create tables for encryption metadata."""
        # Create table for storing encrypted field metadata
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS encrypted_fields (
            id SERIAL PRIMARY KEY,
            table_name VARCHAR(255) NOT NULL,
            column_name VARCHAR(255) NOT NULL,
            encryption_key_id UUID NOT NULL,
            encryption_algorithm VARCHAR(50) DEFAULT 'AES-256-GCM',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(table_name, column_name)
        );
        """
        db.execute(text(create_table_sql))

        # Create indexes for performance
        index_sql = """
        CREATE INDEX IF NOT EXISTS idx_encrypted_fields_table
        ON encrypted_fields(table_name);
        CREATE INDEX IF NOT EXISTS idx_encrypted_fields_key
        ON encrypted_fields(encryption_key_id);
        """
        db.execute(text(index_sql))
        db.commit()

    def _initialize_master_key(self, db: Session) -> Dict[str, Any]:
        """Initialize or retrieve master encryption key."""
        try:
            # Check if master key exists
            result = db.execute(
                text(
                    "SELECT key_id, key_data FROM encryption_keys "
                    "WHERE key_type = 'master' AND is_active = true "
                    "ORDER BY created_at DESC LIMIT 1"
                )
            ).fetchone()

            if result:
                return {
                    "key_id": result[0],
                    "key_data": result[1],
                    "status": "existing",
                }

            # Create new master key
            master_key = self.key_service.create_key(
                key_type="master",
                purpose="database_encryption",
                tenant_id="system",
            )

            logger.info(
                "Master encryption key created",
                extra={
                    "key_id": master_key["key_id"],
                    "kms_provider": self.security_config.kms_provider,
                },
            )

            return master_key

        except Exception as e:
            logger.error(
                "Failed to initialize master key",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    def encrypt_field(self, value: str, key_id: str) -> str:
        """Encrypt a field value using specified key."""
        if not value:
            return value

        try:
            cipher = self._get_cipher(key_id)
            encrypted_bytes = cipher.encrypt(value.encode("utf-8"))
            return base64.b64encode(encrypted_bytes).decode("utf-8")

        except Exception as e:
            logger.error(
                "Field encryption failed",
                extra={
                    "key_id": key_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    def decrypt_field(self, encrypted_value: str, key_id: str) -> str:
        """Decrypt a field value using specified key."""
        if not encrypted_value:
            return encrypted_value

        try:
            cipher = self._get_cipher(key_id)
            encrypted_bytes = base64.b64decode(encrypted_value.encode("utf-8"))
            decrypted_bytes = cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode("utf-8")

        except Exception as e:
            logger.error(
                "Field decryption failed",
                extra={
                    "key_id": key_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    def _get_cipher(self, key_id: str) -> Fernet:
        """Get or create cipher for key ID."""
        if key_id not in self._cipher_cache:
            key_data = self.key_service.get_key(key_id)
            if not key_data:
                raise ValueError(f"Encryption key not found: {key_id}")

            # Derive Fernet key from stored key data
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"stable_salt",  # In production, use unique salt per key
                iterations=100000,
            )
            fernet_key = base64.urlsafe_b64encode(
                kdf.derive(key_data["key_data"].encode())
            )
            self._cipher_cache[key_id] = Fernet(fernet_key)

        return self._cipher_cache[key_id]

    def verify_encryption_status(self, db: Session) -> Dict[str, Any]:
        """Verify database encryption configuration."""
        try:
            # Check pgcrypto extension
            pgcrypto_result = db.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension "
                    "WHERE extname = 'pgcrypto')"
                )
            ).scalar()

            # Check encryption keys table
            keys_result = db.execute(
                text("SELECT COUNT(*) FROM encryption_keys " "WHERE is_active = true")
            ).scalar()

            # Check encrypted fields configuration
            fields_result = db.execute(
                text("SELECT COUNT(*) FROM encrypted_fields")
            ).scalar()

            status = {
                "pgcrypto_enabled": bool(pgcrypto_result),
                "active_keys_count": int(keys_result or 0),
                "encrypted_fields_count": int(fields_result or 0),
                "encryption_ready": (
                    bool(pgcrypto_result) and int(keys_result or 0) > 0
                ),
                "kms_provider": self.security_config.kms_provider,
            }

            logger.info(
                "Database encryption status verified",
                extra=status,
            )

            return status

        except Exception as e:
            logger.error(
                "Failed to verify encryption status",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    def rotate_encryption_keys(self, db: Session) -> Dict[str, Any]:
        """Rotate encryption keys according to policy."""
        try:
            if not self.security_config.key_rotation_enabled:
                return {
                    "status": "skipped",
                    "reason": "Key rotation disabled",
                }

            # Get keys due for rotation
            rotation_result = self.key_service.rotate_keys()

            logger.info(
                "Key rotation completed",
                extra={
                    "rotated_keys": rotation_result.get("rotated_count", 0),
                    "rotation_policy": (
                        self.security_config.key_rotation_interval_days
                    ),
                },
            )

            return rotation_result

        except Exception as e:
            logger.error(
                "Key rotation failed",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise


def get_database_encryption_service() -> DatabaseEncryptionService:
    """Get database encryption service instance."""
    return DatabaseEncryptionService()

"""Encryption key management model for PHI security and tenant isolation."""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship

from models.auth_token import JSONBType

from .base import BaseModel
from .types import UUID


class KeyType(str, Enum):
    """Types of encryption keys supported by the system."""

    PHI_DATA = "phi_data"  # Patient Health Information
    PII_DATA = "pii_data"  # Personally Identifiable Information
    FINANCIAL = "financial"  # Financial and billing data
    CLINICAL = "clinical"  # Clinical notes and assessments
    AUDIT_LOG = "audit_log"  # Audit trail encryption
    BACKUP = "backup"  # Database backup encryption
    COMMUNICATION = "communication"  # Secure messaging


class KeyStatus(str, Enum):
    """Status values for encryption keys."""

    ACTIVE = "active"  # Currently active and usable
    INACTIVE = "inactive"  # Temporarily disabled
    ROTATED = "rotated"  # Replaced by newer key
    EXPIRED = "expired"  # Past expiration date
    COMPROMISED = "compromised"  # Security breach detected
    PENDING = "pending"  # Awaiting activation


class KeyProvider(str, Enum):
    """External key management service providers."""

    AWS_KMS = "aws_kms"  # AWS Key Management Service
    AZURE_KV = "azure_kv"  # Azure Key Vault
    HASHICORP_VAULT = "hashicorp_vault"  # HashiCorp Vault
    GCP_KMS = "gcp_kms"  # Google Cloud KMS
    LOCAL_HSM = "local_hsm"  # Local Hardware Security Module


class EncryptionKey(BaseModel):
    """Encryption key management model for HIPAA-compliant PHI security.

    This model provides:
    - Tenant-isolated key management
    - External KMS integration (keys never stored in database)
    - Key versioning and rotation tracking
    - Comprehensive audit trails
    - HIPAA-compliant key lifecycle management
    - Rollback capabilities for key rotation
    """

    __tablename__ = "encryption_keys"

    # Key identification and metadata
    key_name = Column(String(255), nullable=False, index=True)
    key_type: Column[str] = Column(SQLEnum(KeyType), nullable=False, index=True)

    # External KMS reference (never store actual key material)
    kms_key_id = Column(String(512), nullable=False, unique=True, index=True)
    kms_provider: Column[str] = Column(SQLEnum(KeyProvider), nullable=False, index=True)
    kms_region = Column(String(100), nullable=True)  # For cloud providers
    kms_endpoint = Column(String(512), nullable=True)  # Custom endpoints

    # Key lifecycle management
    status: Column[str] = Column(
        SQLEnum(KeyStatus), default=KeyStatus.PENDING, nullable=False, index=True
    )
    version = Column(String(50), nullable=False, default="1", index=True)

    # Key rotation and expiration
    activated_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    rotated_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Key relationships for rotation
    parent_key_id: Column[UUID] = Column(
        UUID,
        ForeignKey("encryption_keys.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Rollback support
    can_rollback = Column(Boolean, default=True, nullable=False)
    rollback_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Security and compliance
    key_algorithm = Column(String(100), nullable=False, default="AES-256-GCM")
    key_purpose = Column(Text, nullable=True)  # Human-readable purpose
    compliance_tags = Column(JSONBType, nullable=True)  # HIPAA, SOC2, etc.

    # Service authorization and access control
    authorized_services = Column(JSONBType, nullable=True)  # Services allowed
    access_policy = Column(JSONBType, nullable=True)  # Fine-grained access

    # Integration with auth system
    created_by_token_id: Column[UUID] = Column(
        UUID,
        ForeignKey("auth_tokens.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rotated_by_token_id: Column[UUID] = Column(
        UUID, ForeignKey("auth_tokens.id", ondelete="SET NULL"), nullable=True
    )
    rotation_policy_id: Column[UUID] = Column(
        UUID,
        ForeignKey("key_rotation_policies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    parent_key = relationship(
        "EncryptionKey", remote_side=lambda: EncryptionKey.id, backref="child_keys"
    )
    created_by_token = relationship(
        "AuthToken", foreign_keys=[created_by_token_id], backref="created_keys"
    )
    rotated_by_token = relationship(
        "AuthToken", foreign_keys=[rotated_by_token_id], backref="rotated_keys"
    )
    rotation_policy = relationship(
        "KeyRotationPolicy",
        foreign_keys=[rotation_policy_id],
        back_populates="encryption_keys",
    )

    # Database indexes for performance
    __table_args__ = (
        # Tenant isolation and key lookup
        Index("idx_encryption_keys_tenant_type", "tenant_id", "key_type", "status"),
        Index("idx_encryption_keys_tenant_name", "tenant_id", "key_name", "version"),
        # Key lifecycle management
        Index("idx_encryption_keys_status_expires", "status", "expires_at"),
        Index("idx_encryption_keys_rotation", "parent_key_id", "rotated_at"),
        # KMS integration
        Index("idx_encryption_keys_kms", "kms_provider", "kms_key_id"),
        # Audit and compliance
        Index("idx_encryption_keys_audit", "created_at", "tenant_id", "key_type"),
        Index("idx_encryption_keys_usage", "last_used_at", "status"),
        # Rollback support
        Index("idx_encryption_keys_rollback", "can_rollback", "rollback_expires_at"),
    )

    def is_active(self) -> bool:
        """Check if the key is currently active and usable."""
        if self.status != KeyStatus.ACTIVE:
            return False

        now = datetime.now(timezone.utc)

        # Check if key is activated
        if self.activated_at:
            activated_at = self.activated_at
            if activated_at.tzinfo is None:
                activated_at = activated_at.replace(tzinfo=timezone.utc)
            if activated_at > now:
                return False

        # Check if key is expired
        if self.expires_at:
            expires_at = self.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= now:
                return False

        return True

    def can_be_rotated(self) -> bool:
        """Check if the key can be rotated."""
        return self.status in [KeyStatus.PENDING, KeyStatus.ACTIVE, KeyStatus.INACTIVE]

    def get_kms_reference(self) -> dict:
        """Get KMS reference information for external key operations."""
        return {
            "provider": self.kms_provider,
            "key_id": self.kms_key_id,
            "region": self.kms_region,
            "endpoint": self.kms_endpoint,
            "algorithm": self.key_algorithm,
        }

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding sensitive KMS details."""
        result = super().to_dict()

        # Remove sensitive KMS information from general serialization
        sensitive_fields = ["kms_key_id", "kms_endpoint"]
        for field in sensitive_fields:
            result.pop(field, None)

        # Add computed fields
        result["is_active"] = self.is_active()
        result["can_rotate"] = self.can_be_rotated()

        return result

    def __repr__(self) -> str:
        """String representation of the encryption key."""
        return (
            f"<EncryptionKey("
            f"tenant_id='{self.tenant_id}', "
            f"key_name='{self.key_name}', "
            f"key_type='{self.key_type}', "
            f"status='{self.status}', "
            f"version='{self.version}'"
            f")>"
        )

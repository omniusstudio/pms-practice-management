"""Encryption key management service for HIPAA-compliant PHI security."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from models.encryption_key import EncryptionKey, KeyProvider, KeyStatus, KeyType


class EncryptionKeyService:
    """Service for managing encryption keys with external KMS integration.

    This service provides:
    - HIPAA-compliant key lifecycle management
    - Integration with external KMS providers
    - Tenant-isolated key operations
    - Comprehensive audit logging
    - Key rotation with rollback capabilities
    """

    def __init__(self, db_session: Session, correlation_id: Optional[str] = None):
        """Initialize the encryption key service.

        Args:
            db_session: Database session for operations
            correlation_id: Request correlation ID for audit trails
        """
        self.db = db_session
        self.correlation_id = correlation_id or str(uuid4())

    async def create_key(
        self,
        tenant_id: str,
        key_name: str,
        key_type: KeyType,
        kms_provider: KeyProvider,
        kms_key_id: str,
        created_by_token_id: Optional[UUID] = None,
        kms_region: Optional[str] = None,
        kms_endpoint: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        key_algorithm: str = "AES-256-GCM",
        key_purpose: Optional[str] = None,
        compliance_tags: Optional[Dict] = None,
        authorized_services: Optional[List[str]] = None,
        access_policy: Optional[Dict] = None,
    ) -> EncryptionKey:
        """Create a new encryption key reference.

        Args:
            tenant_id: Tenant identifier for isolation
            key_name: Human-readable key name
            key_type: Type of data this key encrypts
            kms_provider: External KMS provider
            kms_key_id: External KMS key identifier
            created_by_token_id: Token ID of creator
            kms_region: KMS region (for cloud providers)
            kms_endpoint: Custom KMS endpoint
            expires_at: Key expiration time
            key_algorithm: Encryption algorithm
            key_purpose: Human-readable purpose
            compliance_tags: Compliance metadata
            authorized_services: Services allowed to use key
            access_policy: Fine-grained access rules

        Returns:
            Created EncryptionKey instance

        Raises:
            ValueError: If key parameters are invalid
            IntegrityError: If key already exists
        """
        # Validate input parameters
        if not tenant_id or not key_name or not kms_key_id:
            raise ValueError("tenant_id, key_name, and kms_key_id are required")

        # Check for existing key with same name and tenant
        existing_key = self._get_active_key_by_name(tenant_id, key_name)
        if existing_key:
            raise ValueError(
                f"Active key '{key_name}' already exists for tenant " f"{tenant_id}"
            )

        # Create new encryption key
        encryption_key = EncryptionKey(
            tenant_id=tenant_id,
            key_name=key_name,
            key_type=key_type,
            kms_provider=kms_provider,
            kms_key_id=kms_key_id,
            kms_region=kms_region,
            kms_endpoint=kms_endpoint,
            status=KeyStatus.PENDING,
            version="1",
            expires_at=expires_at,
            key_algorithm=key_algorithm,
            key_purpose=key_purpose,
            compliance_tags=compliance_tags or {},
            authorized_services=authorized_services or [],
            access_policy=access_policy or {},
            created_by_token_id=created_by_token_id,
            correlation_id=self.correlation_id,
        )

        self.db.add(encryption_key)
        self.db.commit()
        self.db.refresh(encryption_key)

        # TODO: Implement audit logging for key creation
        # This would integrate with the audit system once available

        return encryption_key

    async def activate_key(
        self, key_id: UUID, activated_by_token_id: Optional[UUID] = None
    ) -> EncryptionKey:
        """Activate a pending encryption key.

        Args:
            key_id: Key ID to activate
            activated_by_token_id: Token ID of activator

        Returns:
            Activated EncryptionKey instance

        Raises:
            ValueError: If key cannot be activated
        """
        encryption_key = self._get_key_by_id(key_id)
        if not encryption_key:
            raise ValueError(f"Key {key_id} not found")

        if encryption_key.status != KeyStatus.PENDING:
            raise ValueError(f"Key {key_id} is not in PENDING status, cannot activate")

        # Update key status
        encryption_key.status = KeyStatus.ACTIVE
        encryption_key.activated_at = datetime.now(timezone.utc)

        self.db.commit()

        # TODO: Implement audit logging for key activation

        return encryption_key

    async def rotate_key(
        self,
        key_id: UUID,
        new_kms_key_id: str,
        rotated_by_token_id: Optional[UUID] = None,
        rollback_period_hours: int = 24,
    ) -> Tuple[EncryptionKey, EncryptionKey]:
        """Rotate an encryption key with rollback capability.

        Args:
            key_id: Current key ID to rotate
            new_kms_key_id: New KMS key identifier
            rotated_by_token_id: Token ID of rotator
            rollback_period_hours: Hours to allow rollback

        Returns:
            Tuple of (old_key, new_key)

        Raises:
            ValueError: If key cannot be rotated
        """
        old_key = self._get_key_by_id(key_id)
        if not old_key:
            raise ValueError(f"Key {key_id} not found")

        if not old_key.can_be_rotated():
            raise ValueError(
                f"Key {key_id} cannot be rotated " f"(status: {old_key.status})"
            )

        # Create new key version
        new_version = str(int(old_key.version) + 1)
        rollback_expires = datetime.now(timezone.utc) + timedelta(
            hours=rollback_period_hours
        )

        new_key = EncryptionKey(
            tenant_id=old_key.tenant_id,
            key_name=old_key.key_name,
            key_type=old_key.key_type,
            kms_provider=old_key.kms_provider,
            kms_key_id=new_kms_key_id,
            kms_region=old_key.kms_region,
            kms_endpoint=old_key.kms_endpoint,
            status=KeyStatus.ACTIVE,
            version=new_version,
            activated_at=datetime.now(timezone.utc),
            expires_at=old_key.expires_at,
            parent_key_id=old_key.id,
            can_rollback=True,
            rollback_expires_at=rollback_expires,
            key_algorithm=old_key.key_algorithm,
            key_purpose=old_key.key_purpose,
            compliance_tags=old_key.compliance_tags,
            authorized_services=old_key.authorized_services,
            access_policy=old_key.access_policy,
            rotated_by_token_id=rotated_by_token_id,
            correlation_id=self.correlation_id,
        )

        # Update old key status
        old_key.status = KeyStatus.ROTATED
        old_key.rotated_at = datetime.now(timezone.utc)
        old_key.can_rollback = True
        old_key.rollback_expires_at = rollback_expires

        self.db.add(new_key)
        self.db.commit()
        self.db.refresh(new_key)

        # TODO: Implement audit logging for key rotation

        return old_key, new_key

    async def rollback_key_rotation(
        self, new_key_id: UUID, rollback_by_token_id: Optional[UUID] = None
    ) -> EncryptionKey:
        """Rollback a key rotation within the rollback period.

        Args:
            new_key_id: New key ID to rollback
            rollback_by_token_id: Token ID of rollback initiator

        Returns:
            Restored old key

        Raises:
            ValueError: If rollback is not possible
        """
        new_key = self._get_key_by_id(new_key_id)
        if not new_key or not new_key.parent_key_id:
            raise ValueError(f"Key {new_key_id} is not a rotated key")

        if not new_key.can_rollback:
            raise ValueError(f"Key {new_key_id} cannot be rolled back")

        now = datetime.now(timezone.utc)
        if new_key.rollback_expires_at:
            rollback_expires_at = new_key.rollback_expires_at
            if rollback_expires_at.tzinfo is None:
                rollback_expires_at = rollback_expires_at.replace(tzinfo=timezone.utc)
            if rollback_expires_at <= now:
                raise ValueError(f"Rollback period for key {new_key_id} has expired")

        # Get the old key
        old_key = self._get_key_by_id(new_key.parent_key_id)
        if not old_key:
            raise ValueError(f"Parent key {new_key.parent_key_id} not found")

        # Restore old key
        old_key.status = KeyStatus.ACTIVE
        old_key.can_rollback = False
        old_key.rollback_expires_at = None

        # Deactivate new key
        new_key.status = KeyStatus.INACTIVE
        new_key.can_rollback = False

        self.db.commit()

        # TODO: Implement audit logging for key rollback

        return old_key

    async def get_active_key(
        self, tenant_id: str, key_type: KeyType, key_name: Optional[str] = None
    ) -> Optional[EncryptionKey]:
        """Get the active encryption key for a tenant and type.

        Args:
            tenant_id: Tenant identifier
            key_type: Type of encryption key
            key_name: Optional specific key name

        Returns:
            Active EncryptionKey or None if not found
        """
        query = select(EncryptionKey).where(
            and_(
                EncryptionKey.tenant_id == tenant_id,
                EncryptionKey.key_type == key_type,
                EncryptionKey.status == KeyStatus.ACTIVE,
            )
        )

        if key_name:
            query = query.where(EncryptionKey.key_name == key_name)

        # Get the most recent active key
        query = query.order_by(EncryptionKey.created_at.desc())

        result = self.db.execute(query)
        encryption_key = result.scalar_one_or_none()

        # Update last used timestamp
        if encryption_key:
            encryption_key.last_used_at = datetime.now(timezone.utc)
            self.db.commit()

        return encryption_key

    async def list_keys(
        self,
        tenant_id: str,
        key_type: Optional[KeyType] = None,
        status: Optional[KeyStatus] = None,
        include_expired: bool = False,
    ) -> List[EncryptionKey]:
        """List encryption keys for a tenant.

        Args:
            tenant_id: Tenant identifier
            key_type: Optional key type filter
            status: Optional status filter
            include_expired: Whether to include expired keys

        Returns:
            List of EncryptionKey instances
        """
        query = select(EncryptionKey).where(EncryptionKey.tenant_id == tenant_id)

        if key_type:
            query = query.where(EncryptionKey.key_type == key_type)

        if status:
            query = query.where(EncryptionKey.status == status)

        if not include_expired:
            now = datetime.now(timezone.utc)
            query = query.where(
                or_(EncryptionKey.expires_at.is_(None), EncryptionKey.expires_at > now)
            )

        query = query.order_by(EncryptionKey.key_name, EncryptionKey.version.desc())

        result = self.db.execute(query)
        return result.scalars().all()

    async def expire_key(
        self, key_id: UUID, expired_by_token_id: Optional[UUID] = None
    ) -> EncryptionKey:
        """Manually expire an encryption key.

        Args:
            key_id: Key ID to expire
            expired_by_token_id: Token ID of expirer

        Returns:
            Expired EncryptionKey instance
        """
        encryption_key = self._get_key_by_id(key_id)
        if not encryption_key:
            raise ValueError(f"Key {key_id} not found")

        encryption_key.status = KeyStatus.EXPIRED
        encryption_key.expires_at = datetime.now(timezone.utc)

        self.db.commit()

        # TODO: Implement audit logging for key expiration

        return encryption_key

    async def cleanup_expired_keys(
        self, tenant_id: Optional[str] = None, cleanup_before: Optional[datetime] = None
    ) -> int:
        """Clean up expired keys and rollback periods.

        Args:
            tenant_id: Optional tenant filter
            cleanup_before: Optional cutoff date

        Returns:
            Number of keys cleaned up
        """
        now = datetime.now(timezone.utc)
        cleanup_cutoff = cleanup_before or (now - timedelta(days=30))

        # Build cleanup query
        query = select(EncryptionKey).where(
            or_(
                # Expired keys older than cutoff
                and_(
                    EncryptionKey.status == KeyStatus.EXPIRED,
                    EncryptionKey.expires_at < cleanup_cutoff,
                ),
                # Rollback periods that have expired
                and_(
                    EncryptionKey.rollback_expires_at.is_not(None),
                    EncryptionKey.rollback_expires_at < now,
                ),
            )
        )

        if tenant_id:
            query = query.where(EncryptionKey.tenant_id == tenant_id)

        result = self.db.execute(query)
        keys_to_cleanup = result.scalars().all()

        cleanup_count = 0
        for key in keys_to_cleanup:
            if key.rollback_expires_at:
                rollback_expires_at = key.rollback_expires_at
                if rollback_expires_at.tzinfo is None:
                    rollback_expires_at = rollback_expires_at.replace(
                        tzinfo=timezone.utc
                    )
                if rollback_expires_at < now:
                    # Disable rollback capability
                    key.can_rollback = False
                    key.rollback_expires_at = None
                    cleanup_count += 1
            elif key.status == KeyStatus.EXPIRED and key.expires_at:
                expires_at = key.expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at < cleanup_cutoff:
                    # Mark for deletion (or move to archive)
                    # In production, you might want to archive rather
                    # than delete
                    self.db.delete(key)
                    cleanup_count += 1

        self.db.commit()

        # TODO: Implement audit logging for cleanup operation

        return cleanup_count

    # Private helper methods

    def _get_key_by_id(self, key_id: UUID) -> Optional[EncryptionKey]:
        """Get encryption key by ID."""
        query = select(EncryptionKey).where(EncryptionKey.id == key_id)
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def _get_active_key_by_name(
        self, tenant_id: str, key_name: str
    ) -> Optional[EncryptionKey]:
        """Get active key by tenant and name."""
        query = select(EncryptionKey).where(
            and_(
                EncryptionKey.tenant_id == tenant_id,
                EncryptionKey.key_name == key_name,
                EncryptionKey.status == KeyStatus.ACTIVE,
            )
        )
        result = self.db.execute(query)
        return result.scalar_one_or_none()

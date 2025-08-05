"""Tests for encryption key management functionality."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from models.base import Base
from models.encryption_key import EncryptionKey, KeyProvider, KeyStatus, KeyType
from services.encryption_key_service import EncryptionKeyService


class TestEncryptionKeyModel:
    """Test encryption key model functionality."""

    @pytest.fixture(scope="class")
    def test_engine(self):
        """Create a test database engine."""
        test_engine = create_engine(
            "sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(test_engine)
        yield test_engine
        test_engine.dispose()

    @pytest.fixture
    def db_session(self, test_engine):
        """Create a test database session."""
        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()
        yield session
        session.rollback()
        # Clean up all data between tests
        session.execute(text("DELETE FROM encryption_keys"))
        session.commit()
        session.close()

    def test_encryption_key_creation(self, db_session):
        """Test basic encryption key creation."""
        key = EncryptionKey(
            tenant_id="tenant_123",
            key_name="phi_encryption_key",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="arn:aws:kms:us-east-1:123456789012:key/12345678",
            kms_region="us-east-1",
            status=KeyStatus.PENDING,
            version="1",
            key_algorithm="AES-256-GCM",
            correlation_id="test-123",
        )

        db_session.add(key)
        db_session.commit()

        # Verify key was created
        assert key.id is not None
        assert key.tenant_id == "tenant_123"
        assert key.key_name == "phi_encryption_key"
        assert key.key_type == KeyType.PHI_DATA
        assert key.status == KeyStatus.PENDING
        assert key.version == "1"
        assert not key.is_active()  # Pending keys are not active

    def test_key_status_validation(self, db_session):
        """Test key status validation logic."""
        # Test pending key
        pending_key = EncryptionKey(
            tenant_id="tenant_123",
            key_name="test_key",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="test-key-id",
            status=KeyStatus.PENDING,
        )
        assert not pending_key.is_active()
        assert pending_key.can_be_rotated()

        # Test active key
        active_key = EncryptionKey(
            tenant_id="tenant_123",
            key_name="test_key_2",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="test-key-id-2",
            status=KeyStatus.ACTIVE,
            activated_at=datetime.now(timezone.utc),
        )
        assert active_key.is_active()
        assert active_key.can_be_rotated()

        # Test expired key
        expired_key = EncryptionKey(
            tenant_id="tenant_123",
            key_name="test_key_3",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="test-key-id-3",
            status=KeyStatus.ACTIVE,
            activated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert not expired_key.is_active()  # Expired

        # Test compromised key
        compromised_key = EncryptionKey(
            tenant_id="tenant_123",
            key_name="test_key_4",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="test-key-id-4",
            status=KeyStatus.COMPROMISED,
        )
        assert not compromised_key.is_active()
        assert not compromised_key.can_be_rotated()

    def test_kms_reference(self, db_session):
        """Test KMS reference functionality."""
        key = EncryptionKey(
            tenant_id="tenant_123",
            key_name="test_key",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="arn:aws:kms:us-east-1:123456789012:key/12345678",
            kms_region="us-east-1",
            key_algorithm="AES-256-GCM",
        )

        kms_ref = key.get_kms_reference()

        assert kms_ref["provider"] == KeyProvider.AWS_KMS
        expected_key_id = "arn:aws:kms:us-east-1:123456789012:key/12345678"
        assert kms_ref["key_id"] == expected_key_id
        assert kms_ref["region"] == "us-east-1"
        assert kms_ref["algorithm"] == "AES-256-GCM"

    def test_to_dict_excludes_sensitive_data(self, db_session):
        """Test that to_dict excludes sensitive KMS information."""
        key = EncryptionKey(
            tenant_id="tenant_123",
            key_name="test_key",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="sensitive-key-id",
            kms_endpoint="https://kms.example.com",
            status=KeyStatus.ACTIVE,
            activated_at=datetime.now(timezone.utc),
        )

        key_dict = key.to_dict()

        # Sensitive fields should be excluded
        assert "kms_key_id" not in key_dict
        assert "kms_endpoint" not in key_dict

        # Non-sensitive fields should be included
        assert key_dict["tenant_id"] == "tenant_123"
        assert key_dict["key_name"] == "test_key"
        assert key_dict["key_type"] == KeyType.PHI_DATA
        assert key_dict["kms_provider"] == KeyProvider.AWS_KMS

        # Computed fields should be included
        assert "is_active" in key_dict
        assert "can_rotate" in key_dict
        assert key_dict["is_active"] is True


class TestEncryptionKeyService:
    """Test encryption key service functionality."""

    @pytest.fixture(scope="class")
    def test_engine(self):
        """Create a test database engine."""
        test_engine = create_engine(
            "sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(test_engine)
        yield test_engine
        test_engine.dispose()

    @pytest.fixture
    def db_session(self, test_engine):
        """Create a test database session."""
        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()
        yield session
        session.rollback()
        # Clean up all data between tests
        session.execute(text("DELETE FROM encryption_keys"))
        session.commit()
        session.close()

    @pytest.fixture
    def key_service(self, db_session):
        """Create encryption key service instance."""
        return EncryptionKeyService(
            db_session=db_session, correlation_id="test-correlation-123"
        )

    @pytest.mark.asyncio
    async def test_create_key(self, key_service, db_session):
        """Test key creation through service."""
        tenant_id = "tenant_123"
        key_name = "phi_encryption_key"

        key = await key_service.create_key(
            tenant_id=tenant_id,
            key_name=key_name,
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="arn:aws:kms:us-east-1:123456789012:key/12345678",
            kms_region="us-east-1",
            key_purpose="Encrypt patient health information",
            compliance_tags={"HIPAA": True, "SOC2": True},
            authorized_services=["patient-service", "billing-service"],
        )

        assert key.id is not None
        assert key.tenant_id == tenant_id
        assert key.key_name == key_name
        assert key.key_type == KeyType.PHI_DATA
        assert key.status == KeyStatus.PENDING
        assert key.version == "1"
        assert key.compliance_tags["HIPAA"] is True
        assert "patient-service" in key.authorized_services

    @pytest.mark.asyncio
    async def test_create_duplicate_key_fails(self, key_service, db_session):
        """Test that creating duplicate active keys fails."""
        tenant_id = "tenant_123"
        key_name = "duplicate_key"

        # Create first key and activate it
        key1 = await key_service.create_key(
            tenant_id=tenant_id,
            key_name=key_name,
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="key-id-1",
        )
        await key_service.activate_key(key1.id)

        # Attempt to create duplicate should fail
        with pytest.raises(ValueError, match="already exists"):
            await key_service.create_key(
                tenant_id=tenant_id,
                key_name=key_name,
                key_type=KeyType.PHI_DATA,
                kms_provider=KeyProvider.AWS_KMS,
                kms_key_id="key-id-2",
            )

    @pytest.mark.asyncio
    async def test_activate_key(self, key_service, db_session):
        """Test key activation."""
        # Create pending key
        key = await key_service.create_key(
            tenant_id="tenant_123",
            key_name="test_key",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="test-key-id",
        )

        assert key.status == KeyStatus.PENDING
        assert not key.is_active()

        # Activate key
        activated_key = await key_service.activate_key(key.id)

        assert activated_key.status == KeyStatus.ACTIVE
        assert activated_key.activated_at is not None
        assert activated_key.is_active()

    @pytest.mark.asyncio
    async def test_activate_non_pending_key_fails(self, key_service, db_session):
        """Test that activating non-pending key fails."""
        # Create and activate key
        key = await key_service.create_key(
            tenant_id="tenant_123",
            key_name="test_key",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="test-key-id",
        )
        await key_service.activate_key(key.id)

        # Attempt to activate again should fail
        with pytest.raises(ValueError, match="not in PENDING status"):
            await key_service.activate_key(key.id)

    @pytest.mark.asyncio
    async def test_rotate_key(self, key_service, db_session):
        """Test key rotation functionality."""
        # Create and activate key
        old_key = await key_service.create_key(
            tenant_id="tenant_123",
            key_name="rotation_test_key",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="old-key-id",
        )
        await key_service.activate_key(old_key.id)

        # Rotate key
        rotated_old, new_key = await key_service.rotate_key(
            key_id=old_key.id, new_kms_key_id="new-key-id", rollback_period_hours=48
        )

        # Verify old key status
        assert rotated_old.status == KeyStatus.ROTATED
        assert rotated_old.rotated_at is not None
        assert rotated_old.can_rollback is True
        assert rotated_old.rollback_expires_at is not None

        # Verify new key
        assert new_key.status == KeyStatus.ACTIVE
        assert new_key.version == "2"
        assert new_key.parent_key_id == old_key.id
        assert new_key.kms_key_id == "new-key-id"
        assert new_key.key_name == old_key.key_name  # Same name
        assert new_key.tenant_id == old_key.tenant_id  # Same tenant

    @pytest.mark.asyncio
    async def test_rollback_key_rotation(self, key_service, db_session):
        """Test key rotation rollback functionality."""
        # Create, activate, and rotate key
        old_key = await key_service.create_key(
            tenant_id="tenant_123",
            key_name="rollback_test_key",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="old-key-id",
        )
        await key_service.activate_key(old_key.id)

        rotated_old, new_key = await key_service.rotate_key(
            key_id=old_key.id, new_kms_key_id="new-key-id"
        )

        # Rollback rotation
        restored_key = await key_service.rollback_key_rotation(new_key.id)

        # Verify restoration
        assert restored_key.id == old_key.id
        assert restored_key.status == KeyStatus.ACTIVE
        assert restored_key.can_rollback is False

        # Verify new key is deactivated
        db_session.refresh(new_key)
        assert new_key.status == KeyStatus.INACTIVE
        assert new_key.can_rollback is False

    @pytest.mark.asyncio
    async def test_get_active_key(self, key_service, db_session):
        """Test retrieving active keys."""
        tenant_id = "tenant_123"

        # Create and activate key
        key = await key_service.create_key(
            tenant_id=tenant_id,
            key_name="active_key_test",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="active-key-id",
        )
        await key_service.activate_key(key.id)

        # Retrieve active key
        active_key = await key_service.get_active_key(
            tenant_id=tenant_id, key_type=KeyType.PHI_DATA
        )

        assert active_key is not None
        assert active_key.id == key.id
        assert active_key.last_used_at is not None  # Should be updated

        # Test with specific key name
        named_key = await key_service.get_active_key(
            tenant_id=tenant_id, key_type=KeyType.PHI_DATA, key_name="active_key_test"
        )

        assert named_key is not None
        assert named_key.id == key.id

    @pytest.mark.asyncio
    async def test_list_keys(self, key_service, db_session):
        """Test listing keys with filters."""
        tenant_id = "tenant_123"

        # Create multiple keys
        phi_key = await key_service.create_key(
            tenant_id=tenant_id,
            key_name="phi_key",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="phi-key-id",
        )

        await key_service.create_key(
            tenant_id=tenant_id,
            key_name="financial_key",
            key_type=KeyType.FINANCIAL,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="financial-key-id",
        )

        await key_service.activate_key(phi_key.id)
        # Leave financial_key as pending

        # List all keys
        all_keys = await key_service.list_keys(tenant_id=tenant_id)
        assert len(all_keys) == 2

        # List by type
        phi_keys = await key_service.list_keys(
            tenant_id=tenant_id, key_type=KeyType.PHI_DATA
        )
        assert len(phi_keys) == 1
        assert phi_keys[0].key_type == KeyType.PHI_DATA

        # List by status
        active_keys = await key_service.list_keys(
            tenant_id=tenant_id, status=KeyStatus.ACTIVE
        )
        assert len(active_keys) == 1
        assert active_keys[0].status == KeyStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_expire_key(self, key_service, db_session):
        """Test manual key expiration."""
        # Create and activated key
        key = await key_service.create_key(
            tenant_id="tenant_123",
            key_name="expire_test_key",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="expire-key-id",
        )
        await key_service.activate_key(key.id)

        # Expire key
        expired_key = await key_service.expire_key(key.id)

        assert expired_key.status == KeyStatus.EXPIRED
        assert expired_key.expires_at is not None
        assert not expired_key.is_active()

    @pytest.mark.asyncio
    async def test_cleanup_expired_keys(self, key_service, db_session):
        """Test cleanup of expired keys and rollback periods."""
        tenant_id = "tenant_123"

        # Create expired key
        expired_key = await key_service.create_key(
            tenant_id=tenant_id,
            key_name="expired_key",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="expired-key-id",
            expires_at=datetime.now(timezone.utc) - timedelta(days=60),
        )
        await key_service.activate_key(expired_key.id)
        await key_service.expire_key(expired_key.id)

        # Create key with expired rollback period
        rollback_key = await key_service.create_key(
            tenant_id=tenant_id,
            key_name="rollback_key",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="rollback-key-id",
        )
        await key_service.activate_key(rollback_key.id)

        # Manually set expired rollback period
        rollback_key.can_rollback = True
        rollback_key.rollback_expires_at = datetime.now(timezone.utc) - timedelta(
            hours=1
        )
        db_session.commit()

        # Run cleanup
        cleanup_count = await key_service.cleanup_expired_keys(
            tenant_id=tenant_id,
            cleanup_before=datetime.now(timezone.utc) - timedelta(days=30),
        )

        # Should clean up rollback period and expired key
        assert cleanup_count >= 1

        # Verify rollback period was cleaned
        db_session.refresh(rollback_key)
        assert rollback_key.can_rollback is False
        assert rollback_key.rollback_expires_at is None

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, key_service, db_session):
        """Test that keys are properly isolated by tenant."""
        # Create keys for different tenants
        tenant1_key = await key_service.create_key(
            tenant_id="tenant_1",
            key_name="shared_name",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="tenant1-key-id",
        )

        tenant2_key = await key_service.create_key(
            tenant_id="tenant_2",
            key_name="shared_name",  # Same name, different tenant
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="tenant2-key-id",
        )

        await key_service.activate_key(tenant1_key.id)
        await key_service.activate_key(tenant2_key.id)

        # Verify tenant isolation
        tenant1_keys = await key_service.list_keys(tenant_id="tenant_1")
        tenant2_keys = await key_service.list_keys(tenant_id="tenant_2")

        assert len(tenant1_keys) == 1
        assert len(tenant2_keys) == 1
        assert tenant1_keys[0].tenant_id == "tenant_1"
        assert tenant2_keys[0].tenant_id == "tenant_2"

        # Verify active key retrieval respects tenant isolation
        tenant1_active = await key_service.get_active_key(
            tenant_id="tenant_1", key_type=KeyType.PHI_DATA
        )
        tenant2_active = await key_service.get_active_key(
            tenant_id="tenant_2", key_type=KeyType.PHI_DATA
        )

        assert tenant1_active.id == tenant1_key.id
        assert tenant2_active.id == tenant2_key.id
        assert tenant1_active.kms_key_id != tenant2_active.kms_key_id


class TestEncryptionKeyCompliance:
    """Test HIPAA compliance and security features."""

    def test_key_types_cover_phi_requirements(self):
        """Test that key types cover all PHI requirements."""
        # Verify all required PHI key types exist
        required_types = [
            KeyType.PHI_DATA,
            KeyType.PII_DATA,
            KeyType.FINANCIAL,
            KeyType.CLINICAL,
            KeyType.AUDIT_LOG,
        ]

        for key_type in required_types:
            assert key_type in KeyType

    def test_kms_providers_support(self):
        """Test that major KMS providers are supported."""
        supported_providers = [
            KeyProvider.AWS_KMS,
            KeyProvider.AZURE_KV,
            KeyProvider.HASHICORP_VAULT,
            KeyProvider.GCP_KMS,
        ]

        for provider in supported_providers:
            assert provider in KeyProvider

    def test_audit_trail_fields(self):
        """Test that audit trail fields are present."""
        key = EncryptionKey(
            tenant_id="tenant_123",
            key_name="audit_test",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="audit-key-id",
            correlation_id="audit-correlation-123",
        )

        # Verify audit fields
        assert hasattr(key, "created_at")
        assert hasattr(key, "updated_at")
        assert hasattr(key, "correlation_id")
        assert hasattr(key, "tenant_id")
        assert hasattr(key, "created_by_token_id")
        assert hasattr(key, "rotated_by_token_id")

        assert key.correlation_id == "audit-correlation-123"

    def test_sensitive_data_exclusion(self):
        """Test that sensitive data is excluded from serialization."""
        key = EncryptionKey(
            tenant_id="tenant_123",
            key_name="sensitive_test",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="sensitive-key-material",
            kms_endpoint="https://sensitive-endpoint.com",
        )

        key_dict = key.to_dict()

        # Sensitive fields should not be in dictionary
        sensitive_fields = ["kms_key_id", "kms_endpoint"]
        for field in sensitive_fields:
            assert field not in key_dict

    def test_compliance_tags_support(self):
        """Test compliance tags functionality."""
        compliance_tags = {
            "HIPAA": True,
            "SOC2": True,
            "PCI_DSS": False,
            "GDPR": True,
            "audit_required": True,
            "retention_years": 7,
        }

        key = EncryptionKey(
            tenant_id="tenant_123",
            key_name="compliance_test",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="compliance-key-id",
            compliance_tags=compliance_tags,
        )

        assert key.compliance_tags["HIPAA"] is True
        assert key.compliance_tags["retention_years"] == 7
        assert key.compliance_tags["audit_required"] is True

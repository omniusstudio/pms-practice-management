"""Tests for automated key rotation functionality."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.auth_token import AuthToken, TokenStatus, TokenType
from models.base import Base
from models.encryption_key import EncryptionKey, KeyProvider, KeyStatus, KeyType
from models.key_rotation_policy import KeyRotationPolicy, PolicyStatus, RotationTrigger
from services.key_rotation_scheduler import KeyRotationScheduler


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_auth_token(db_session):
    """Create a sample auth token for testing."""
    token = AuthToken(
        user_id=uuid4(),
        token_type=TokenType.ACCESS,
        token_hash="test_hash",
        status=TokenStatus.ACTIVE,
        issued_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        scopes=["read", "write"],
    )
    db_session.add(token)
    db_session.commit()
    db_session.refresh(token)
    return token


@pytest.fixture
def sample_encryption_key(db_session, sample_auth_token):
    """Create a sample encryption key for testing."""
    key = EncryptionKey(
        tenant_id="test-tenant",
        key_name="test-key",
        key_type=KeyType.PHI_DATA,
        kms_provider=KeyProvider.AWS_KMS,
        kms_key_id="test-kms-key-123",
        kms_region="us-east-1",
        status=KeyStatus.ACTIVE,
        version=1,
        activated_at=datetime.now(timezone.utc),
        key_algorithm="AES-256-GCM",
        key_purpose="PHI encryption",
        created_by_token_id=sample_auth_token.id,
    )
    db_session.add(key)
    db_session.commit()
    db_session.refresh(key)
    return key


@pytest.fixture
def sample_rotation_policy(db_session, sample_auth_token):
    """Create a sample rotation policy for testing."""
    policy = KeyRotationPolicy(
        tenant_id="test-tenant",
        policy_name="Daily PHI Key Rotation",
        description="Rotate PHI keys daily for compliance",
        key_type=KeyType.PHI_DATA,
        kms_provider=KeyProvider.AWS_KMS,
        rotation_trigger=RotationTrigger.TIME_BASED,
        status=PolicyStatus.ACTIVE,
        rotation_interval_days=1,
        rotation_time_of_day="02:00:00",
        timezone="UTC",
        enable_rollback=True,
        rollback_period_hours=24,
        retain_old_keys_days=30,
        created_by_token_id=sample_auth_token.id,
        last_modified_by_token_id=sample_auth_token.id,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


class TestKeyRotationPolicy:
    """Test cases for KeyRotationPolicy model."""

    def test_policy_creation(self, db_session, sample_auth_token):
        """Test creating a rotation policy."""
        policy = KeyRotationPolicy(
            tenant_id="test-tenant",
            policy_name="Test Policy",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            rotation_trigger=RotationTrigger.TIME_BASED,
            rotation_interval_days=7,
            created_by_token_id=sample_auth_token.id,
            last_modified_by_token_id=sample_auth_token.id,
        )

        db_session.add(policy)
        db_session.commit()

        assert policy.id is not None
        assert policy.tenant_id == "test-tenant"
        assert policy.policy_name == "Test Policy"
        assert policy.is_active()

    def test_should_rotate_now_time_based(self, sample_rotation_policy):
        """Test time-based rotation logic."""
        policy = sample_rotation_policy

        # Set next rotation to past time
        policy.next_rotation_at = datetime.now(timezone.utc) - timedelta(hours=1)
        assert policy.should_rotate_now()

        # Set next rotation to future time
        policy.next_rotation_at = datetime.now(timezone.utc) + timedelta(hours=1)
        assert not policy.should_rotate_now()

    def test_should_rotate_now_manual(self, sample_rotation_policy):
        """Test manual rotation logic."""
        policy = sample_rotation_policy
        policy.rotation_trigger = RotationTrigger.MANUAL

        # Manual policies should never auto-rotate
        policy.next_rotation_at = datetime.now(timezone.utc) - timedelta(hours=1)
        assert not policy.should_rotate_now()

    def test_calculate_next_rotation(self, sample_rotation_policy, db_session):
        """Test next rotation calculation."""
        policy = sample_rotation_policy
        policy.rotation_interval_days = 7
        policy.last_rotation_at = datetime.now(timezone.utc)
        db_session.commit()

        next_rotation = policy.calculate_next_rotation()
        assert next_rotation is not None

        # Expected time should account for rotation_time_of_day setting
        expected_base = policy.last_rotation_at + timedelta(days=7)
        # The policy has rotation_time_of_day="02:00:00", adjust expected time
        expected_time = expected_base.replace(hour=2, minute=0, second=0, microsecond=0)
        # Ensure both times are timezone-aware for comparison
        if next_rotation.tzinfo is None:
            next_rotation = next_rotation.replace(tzinfo=timezone.utc)
        if expected_time.tzinfo is None:
            expected_time = expected_time.replace(tzinfo=timezone.utc)
        # Allow for small time differences due to execution time
        expected_diff = (next_rotation - expected_time).total_seconds()
        time_diff = abs(expected_diff)
        assert time_diff < 1

    def test_update_rotation_schedule(self, sample_rotation_policy):
        """Test rotation schedule update."""
        policy = sample_rotation_policy
        policy.rotation_interval_days = 1
        current_time = datetime.now(timezone.utc)
        policy.last_rotation_at = current_time

        policy.update_rotation_schedule()
        assert policy.next_rotation_at is not None


class TestKeyRotationScheduler:
    """Test cases for KeyRotationScheduler service."""

    @pytest.fixture
    def scheduler(self, db_session):
        """Create a scheduler instance for testing."""
        return KeyRotationScheduler(db_session)

    @pytest.mark.asyncio
    async def test_create_rotation_policy(
        self, scheduler, db_session, sample_auth_token
    ):
        """Test creating a rotation policy through the scheduler."""
        policy = await scheduler.create_rotation_policy(
            tenant_id="test-tenant",
            policy_name="Test Automated Policy",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            rotation_trigger=RotationTrigger.TIME_BASED,
            rotation_interval_days=30,
            created_by_token_id=sample_auth_token.id,
        )

        assert policy.id is not None
        assert policy.tenant_id == "test-tenant"
        assert policy.policy_name == "Test Automated Policy"
        assert policy.rotation_interval_days == 30
        assert policy.next_rotation_at is not None

    @pytest.mark.asyncio
    async def test_get_active_policies(self, scheduler, sample_rotation_policy):
        """Test retrieving active policies."""
        policies = await scheduler._get_active_policies()
        assert len(policies) == 1
        assert policies[0].id == sample_rotation_policy.id

        # Test with inactive policy
        sample_rotation_policy.status = PolicyStatus.INACTIVE
        scheduler.db.commit()

        policies = await scheduler._get_active_policies()
        assert len(policies) == 0

    @pytest.mark.asyncio
    async def test_get_keys_for_policy(
        self, scheduler, sample_rotation_policy, sample_encryption_key
    ):
        """Test retrieving keys for a specific policy."""
        # Link key to policy
        sample_encryption_key.rotation_policy_id = sample_rotation_policy.id
        scheduler.db.commit()

        keys = await scheduler._get_keys_for_policy(sample_rotation_policy)
        assert len(keys) == 1
        assert keys[0].id == sample_encryption_key.id

    @pytest.mark.asyncio
    async def test_update_policy_status(self, scheduler, sample_rotation_policy):
        """Test updating policy status."""
        updated_policy = await scheduler.update_policy_status(
            sample_rotation_policy.id, PolicyStatus.SUSPENDED
        )

        assert str(updated_policy.status) == PolicyStatus.SUSPENDED

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, scheduler):
        """Test scheduler start and stop functionality."""
        assert not scheduler._running

        # Start scheduler
        await scheduler.start_scheduler(check_interval_minutes=1)
        assert scheduler._running
        assert scheduler._scheduler_task is not None

        # Stop scheduler
        await scheduler.stop_scheduler()
        assert not scheduler._running

    @pytest.mark.asyncio
    async def test_check_and_rotate_keys_no_policies(self, scheduler):
        """Test rotation check with no active policies."""
        results = await scheduler.check_and_rotate_keys()
        assert results == []

    @pytest.mark.asyncio
    @patch("services.encryption_key_service.EncryptionKeyService.rotate_key")
    async def test_rotate_key_success(
        self, mock_rotate_key, scheduler, sample_rotation_policy, sample_encryption_key
    ):
        """Test successful key rotation."""
        # Setup mock
        new_key = EncryptionKey(
            id=uuid4(),
            tenant_id=sample_encryption_key.tenant_id,
            key_name=sample_encryption_key.key_name,
            key_type=sample_encryption_key.key_type,
            kms_provider=sample_encryption_key.kms_provider,
            kms_key_id="new-kms-key-456",
            status=KeyStatus.ACTIVE,
            version=2,
        )
        mock_rotate_key.return_value = (sample_encryption_key, new_key)

        # Link key to policy
        sample_encryption_key.rotation_policy_id = sample_rotation_policy.id
        scheduler.db.commit()

        # Perform rotation
        result = await scheduler._rotate_key(
            sample_encryption_key, sample_rotation_policy
        )

        assert result["status"] == "success"
        assert result["key_id"] == str(sample_encryption_key.id)
        assert result["new_key_id"] == str(new_key.id)
        mock_rotate_key.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.encryption_key_service.EncryptionKeyService.rotate_key")
    async def test_rotate_key_failure(
        self, mock_rotate_key, scheduler, sample_rotation_policy, sample_encryption_key
    ):
        """Test failed key rotation."""
        # Setup mock to raise exception
        mock_rotate_key.side_effect = Exception("KMS rotation failed")

        # Link key to policy
        sample_encryption_key.rotation_policy_id = sample_rotation_policy.id
        scheduler.db.commit()

        # Perform rotation
        result = await scheduler._rotate_key(
            sample_encryption_key, sample_rotation_policy
        )

        assert result["status"] == "error"
        assert result["key_id"] == str(sample_encryption_key.id)
        assert "KMS rotation failed" in result["error"]

    @pytest.mark.asyncio
    async def test_get_rotation_history(self, scheduler, db_session):
        """Test retrieving rotation history."""
        # Create a rotated key
        rotated_key = EncryptionKey(
            tenant_id="test-tenant",
            key_name="rotated-key",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="rotated-kms-key",
            status=KeyStatus.ROTATED,
            version=1,
            rotated_at=datetime.now(timezone.utc),
        )
        db_session.add(rotated_key)
        db_session.commit()

        history = await scheduler.get_rotation_history("test-tenant")
        assert len(history) == 1
        assert history[0]["key_id"] == str(rotated_key.id)
        assert history[0]["status"] == KeyStatus.ROTATED
        assert history[0]["rotated_at"] is not None


class TestIntegration:
    """Integration tests for the complete rotation system."""

    @pytest.mark.asyncio
    @patch("services.encryption_key_service.EncryptionKeyService.rotate_key")
    async def test_end_to_end_rotation(
        self, mock_rotate_key, db_session, sample_auth_token
    ):
        """Test complete end-to-end rotation process."""
        # Create scheduler
        scheduler = KeyRotationScheduler(db_session)

        # Create policy
        policy = await scheduler.create_rotation_policy(
            tenant_id="test-tenant",
            policy_name="E2E Test Policy",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            rotation_trigger=RotationTrigger.TIME_BASED,
            rotation_interval_days=1,
            created_by_token_id=sample_auth_token.id,
        )

        # Create key linked to policy
        key = EncryptionKey(
            tenant_id="test-tenant",
            key_name="e2e-test-key",
            key_type=KeyType.PHI_DATA,
            kms_provider=KeyProvider.AWS_KMS,
            kms_key_id="e2e-kms-key",
            status=KeyStatus.ACTIVE,
            version=1,
            rotation_policy_id=policy.id,
            created_by_token_id=sample_auth_token.id,
        )
        db_session.add(key)
        db_session.commit()

        # Set policy to need rotation
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        policy.next_rotation_at = past_time
        db_session.commit()

        # Setup mock for successful rotation
        new_key = EncryptionKey(
            id=uuid4(),
            tenant_id=key.tenant_id,
            key_name=key.key_name,
            key_type=key.key_type,
            kms_provider=key.kms_provider,
            kms_key_id="new-e2e-kms-key",
            status=KeyStatus.ACTIVE,
            version=2,
        )
        mock_rotate_key.return_value = (key, new_key)

        # Run rotation check
        results = await scheduler.check_and_rotate_keys()

        # Verify results
        assert len(results) == 1
        result = results[0]
        assert result["status"] == "completed"
        assert result["rotated_keys"] == 1
        assert result["failed_keys"] == 0

        # Verify policy was updated
        db_session.refresh(policy)
        assert policy.last_rotation_at is not None

        # Ensure timezone-aware comparison
        now = datetime.now(timezone.utc)
        next_rotation = policy.next_rotation_at
        if next_rotation.tzinfo is None:
            next_rotation = next_rotation.replace(tzinfo=timezone.utc)
        assert next_rotation > now


if __name__ == "__main__":
    pytest.main([__file__])

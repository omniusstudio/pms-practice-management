"""Tests for KeyRotationScheduler service."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from models.encryption_key import EncryptionKey, KeyStatus
from models.key_rotation_policy import KeyRotationPolicy, PolicyStatus, RotationTrigger
from services.encryption_key_service import EncryptionKeyService
from services.key_rotation_scheduler import KeyRotationScheduler


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock(spec=Session)
    db.execute.return_value.scalars.return_value.all.return_value = []
    db.execute.return_value.scalar_one_or_none.return_value = None
    return db


@pytest.fixture
def scheduler(mock_db):
    """Create KeyRotationScheduler instance."""
    return KeyRotationScheduler(mock_db)


@pytest.fixture
def sample_policy():
    """Create sample rotation policy."""
    policy = KeyRotationPolicy(
        id=uuid4(),
        tenant_id="test-tenant",
        policy_name="test-policy",
        key_type="encryption",
        kms_provider="aws",
        rotation_trigger=RotationTrigger.TIME_BASED,
        rotation_interval_days=30,
        status=PolicyStatus.ACTIVE,
        created_by_token_id=uuid4(),
    )
    policy.should_rotate_now = MagicMock(return_value=True)
    policy.update_rotation_schedule = MagicMock()
    return policy


@pytest.fixture
def sample_key():
    """Create sample encryption key."""
    return EncryptionKey(
        id=uuid4(),
        tenant_id="test-tenant",
        key_name="test-key",
        key_type="encryption",
        kms_provider="aws",
        kms_key_id="test-kms-key",
        status=KeyStatus.ACTIVE,
        rotation_policy_id=uuid4(),
    )


class TestKeyRotationScheduler:
    """Test cases for KeyRotationScheduler."""

    def test_init(self, mock_db):
        """Test scheduler initialization."""
        scheduler = KeyRotationScheduler(mock_db)

        assert scheduler.db == mock_db
        assert scheduler.correlation_id is not None
        assert not scheduler._running
        assert scheduler._scheduler_task is None

    @pytest.mark.asyncio
    async def test_start_scheduler(self, scheduler):
        """Test starting the scheduler."""
        with patch("asyncio.create_task") as mock_create_task:
            mock_task = AsyncMock()
            mock_create_task.return_value = mock_task

            await scheduler.start_scheduler(check_interval_minutes=5)

            assert scheduler._running
            assert scheduler._scheduler_task == mock_task
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_scheduler_not_running(self, scheduler):
        """Test stopping scheduler when not running."""
        await scheduler.stop_scheduler()
        assert not scheduler._running

    @pytest.mark.asyncio
    async def test_stop_scheduler_running(self, scheduler):
        """Test stopping running scheduler."""

        # Create a simple task that can be cancelled
        async def dummy_task():
            await asyncio.sleep(1)

        scheduler._running = True
        scheduler._scheduler_task = asyncio.create_task(dummy_task())

        await scheduler.stop_scheduler()

        assert not scheduler._running
        assert scheduler._scheduler_task.cancelled()

    @pytest.mark.asyncio
    async def test_scheduler_loop(self, scheduler):
        """Test scheduler loop execution."""
        scheduler._running = True

        with patch.object(
            scheduler, "check_and_rotate_keys", new_callable=AsyncMock
        ) as mock_check:
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                # Stop after first iteration
                async def stop_after_first():
                    scheduler._running = False

                mock_check.side_effect = stop_after_first

                # 1 minute interval
                await scheduler._scheduler_loop(1)

                mock_check.assert_called_once()
                mock_sleep.assert_called_once_with(60)

    @pytest.mark.asyncio
    async def test_scheduler_loop_with_error(self, scheduler):
        """Test scheduler loop handles errors gracefully."""
        scheduler._running = True
        call_count = 0

        with patch.object(
            scheduler, "check_and_rotate_keys", new_callable=AsyncMock
        ) as mock_check:
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

                async def raise_error_then_stop():
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        raise Exception("Test error")
                    scheduler._running = False

                mock_check.side_effect = raise_error_then_stop

                await scheduler._scheduler_loop(1)

                assert mock_check.call_count == 2
                # Should sleep 60 seconds on error, then normal interval
                mock_sleep.assert_any_call(60)

    @pytest.mark.asyncio
    async def test_get_active_policies(self, scheduler, mock_db, sample_policy):
        """Test getting active policies."""
        mock_db.execute.return_value.scalars.return_value.all.return_value = [
            sample_policy
        ]

        policies = await scheduler._get_active_policies()

        assert len(policies) == 1
        assert policies[0] == sample_policy
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_keys_for_policy(
        self, scheduler, mock_db, sample_policy, sample_key
    ):
        """Test getting keys for a policy."""
        mock_db.execute.return_value.scalars.return_value.all.return_value = [
            sample_key
        ]

        keys = await scheduler._get_keys_for_policy(sample_policy)

        assert len(keys) == 1
        assert keys[0] == sample_key
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_and_rotate_keys_no_policies(self, scheduler):
        """Test check_and_rotate_keys with no active policies."""
        with patch.object(
            scheduler, "_get_active_policies", new_callable=AsyncMock
        ) as mock_get_policies:
            mock_get_policies.return_value = []

            results = await scheduler.check_and_rotate_keys()

            assert results == []
            mock_get_policies.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_and_rotate_keys_success(self, scheduler, sample_policy):
        """Test successful key rotation."""
        expected_result = {
            "policy_id": str(sample_policy.id),
            "policy_name": sample_policy.policy_name,
            "status": "completed",
            "rotated_keys": 1,
            "failed_keys": 0,
            "results": [{"status": "success"}],
        }

        with patch.object(
            scheduler, "_get_active_policies", new_callable=AsyncMock
        ) as mock_get_policies:
            with patch.object(
                scheduler, "_process_policy", new_callable=AsyncMock
            ) as mock_process:
                mock_get_policies.return_value = [sample_policy]
                mock_process.return_value = expected_result

                results = await scheduler.check_and_rotate_keys()

                assert len(results) == 1
                assert results[0] == expected_result
                mock_get_policies.assert_called_once()
                mock_process.assert_called_once_with(sample_policy)

    @pytest.mark.asyncio
    async def test_process_policy_no_rotation_needed(self, scheduler, sample_policy):
        """Test processing policy when no rotation is needed."""
        sample_policy.should_rotate_now.return_value = False

        result = await scheduler._process_policy(sample_policy)

        assert result is None
        sample_policy.should_rotate_now.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_policy_no_keys(self, scheduler, sample_policy):
        """Test processing policy with no keys to rotate."""
        with patch.object(
            scheduler, "_get_keys_for_policy", new_callable=AsyncMock
        ) as mock_get_keys:
            mock_get_keys.return_value = []

            result = await scheduler._process_policy(sample_policy)

            assert result is None
            mock_get_keys.assert_called_once_with(sample_policy)

    @pytest.mark.asyncio
    async def test_rotate_key_success(self, scheduler, sample_key, sample_policy):
        """Test successful key rotation."""
        new_key = EncryptionKey(
            id=uuid4(),
            tenant_id=sample_key.tenant_id,
            key_name="rotated-key",
            key_type=sample_key.key_type,
            kms_provider=sample_key.kms_provider,
            kms_key_id="new-kms-key",
            status=KeyStatus.ACTIVE,
        )

        with patch.object(
            EncryptionKeyService, "rotate_key", new_callable=AsyncMock
        ) as mock_rotate:
            mock_rotate.return_value = (sample_key, new_key)

            result = await scheduler._rotate_key(sample_key, sample_policy)

            assert result["status"] == "success"
            assert result["key_id"] == str(sample_key.id)
            assert result["new_key_id"] == str(new_key.id)
            assert "rotated_at" in result
            mock_rotate.assert_called_once()

    @pytest.mark.asyncio
    async def test_rotate_key_failure(self, scheduler, sample_key, sample_policy):
        """Test key rotation failure."""
        error_msg = "Rotation failed"

        with patch.object(
            EncryptionKeyService, "rotate_key", new_callable=AsyncMock
        ) as mock_rotate:
            mock_rotate.side_effect = Exception(error_msg)

            result = await scheduler._rotate_key(sample_key, sample_policy)

            assert result["status"] == "error"
            assert result["key_id"] == str(sample_key.id)
            assert result["error"] == error_msg
            mock_rotate.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_rotation_policy(self, scheduler, mock_db):
        """Test creating a rotation policy."""
        tenant_id = "test-tenant"
        policy_name = "test-policy"
        key_type = "encryption"
        kms_provider = "aws"
        rotation_trigger = RotationTrigger.TIME_BASED
        rotation_interval_days = 30
        created_by_token_id = uuid4()

        policy = await scheduler.create_rotation_policy(
            tenant_id=tenant_id,
            policy_name=policy_name,
            key_type=key_type,
            kms_provider=kms_provider,
            rotation_trigger=rotation_trigger,
            rotation_interval_days=rotation_interval_days,
            created_by_token_id=created_by_token_id,
        )

        assert policy.tenant_id == tenant_id
        assert policy.policy_name == policy_name
        assert policy.key_type == key_type
        assert policy.kms_provider == kms_provider
        assert policy.rotation_trigger == rotation_trigger
        assert policy.rotation_interval_days == rotation_interval_days
        assert policy.created_by_token_id == created_by_token_id

        mock_db.add.assert_called_once_with(policy)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(policy)

    @pytest.mark.asyncio
    async def test_update_policy_status(self, scheduler, mock_db, sample_policy):
        """Test updating policy status."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_policy
        new_status = PolicyStatus.INACTIVE

        updated_policy = await scheduler.update_policy_status(
            sample_policy.id, new_status
        )

        assert updated_policy == sample_policy
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(sample_policy)

    @pytest.mark.asyncio
    async def test_update_policy_status_not_found(self, scheduler, mock_db):
        """Test updating non-existent policy status."""
        policy_id = uuid4()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(ValueError, match=f"Policy {policy_id} not found"):
            await scheduler.update_policy_status(policy_id, PolicyStatus.INACTIVE)

    @pytest.mark.asyncio
    async def test_get_rotation_history(self, scheduler, mock_db):
        """Test getting rotation history."""
        rotated_key = EncryptionKey(
            id=uuid4(),
            tenant_id="test-tenant",
            key_name="rotated-key",
            key_type="encryption",
            kms_provider="aws",
            kms_key_id="test-kms-key",
            status=KeyStatus.ROTATED,
            rotated_at=datetime.now(timezone.utc),
            parent_key_id=uuid4(),
        )

        mock_db.execute.return_value.scalars.return_value.all.return_value = [
            rotated_key
        ]

        history = await scheduler.get_rotation_history("test-tenant", limit=10)

        assert len(history) == 1
        assert history[0]["key_id"] == str(rotated_key.id)
        assert history[0]["key_name"] == rotated_key.key_name
        assert history[0]["key_type"] == rotated_key.key_type
        assert history[0]["status"] == rotated_key.status
        assert "rotated_at" in history[0]
        assert "parent_key_id" in history[0]

        mock_db.execute.assert_called_once()

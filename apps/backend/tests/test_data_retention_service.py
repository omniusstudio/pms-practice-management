"""Tests for data retention service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.data_retention_policy import DataRetentionPolicy, DataType, PolicyStatus
from models.legal_hold import HoldStatus, LegalHold
from services.data_retention_service import DataRetentionService


class TestDataRetentionService:
    """Test cases for data retention service."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Create a DataRetentionService instance with mocked session."""
        return DataRetentionService(mock_session)

    @pytest.mark.asyncio
    async def test_get_active_policies(self, service, mock_session):
        """Test getting active policies for a tenant."""
        # Create mock policies
        policy1 = Mock(spec=DataRetentionPolicy)
        policy1.policy_id = "policy-1"
        policy1.status = PolicyStatus.ACTIVE

        policy2 = Mock(spec=DataRetentionPolicy)
        policy2.policy_id = "policy-2"
        policy2.status = PolicyStatus.ACTIVE

        # Mock query result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [policy1, policy2]
        mock_session.execute.return_value = mock_result

        # Test
        result = await service.get_active_policies("test-tenant")

        # Verify
        assert len(result) == 2
        assert result[0].policy_id == "policy-1"
        assert result[1].policy_id == "policy-2"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_legal_holds(self, service, mock_session):
        """Test getting legal holds for a resource."""
        # Create mock legal hold
        hold = Mock(spec=LegalHold)
        hold.hold_name = "Test Hold"
        hold.status = HoldStatus.ACTIVE

        # Mock query result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [hold]
        mock_session.execute.return_value = mock_result

        # Test
        result = await service.get_legal_holds("test-tenant", "clients", "client-123")

        # Verify
        assert len(result) == 1
        assert result[0].hold_name == "Test Hold"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_resource_on_legal_hold_true(self, service):
        """Test resource is on legal hold."""
        # Mock active legal hold
        hold = Mock(spec=LegalHold)
        hold.is_active.return_value = True

        with patch.object(service, "get_legal_holds", return_value=[hold]):
            # Test
            result = await service.is_resource_on_legal_hold(
                "test-tenant", "clients", "client-123"
            )

            # Verify
            assert result is True
            hold.is_active.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_resource_on_legal_hold_false(self, service):
        """Test resource not on legal hold."""
        with patch.object(service, "get_legal_holds", return_value=[]):
            # Test
            result = await service.is_resource_on_legal_hold(
                "test-tenant", "clients", "client-123"
            )

            # Verify
            assert result is False

    @pytest.mark.asyncio
    async def test_is_resource_on_legal_hold_inactive(self, service):
        """Test resource with inactive legal hold."""
        # Mock inactive legal hold
        hold = Mock(spec=LegalHold)
        hold.is_active.return_value = False

        with patch.object(service, "get_legal_holds", return_value=[hold]):
            # Test
            result = await service.is_resource_on_legal_hold(
                "test-tenant", "clients", "client-123"
            )

            # Verify
            assert result is False
            hold.is_active.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_eligible_records(self, service, mock_session):
        """Test counting eligible records for purging."""
        # Create mock policy
        policy = Mock(spec=DataRetentionPolicy)
        policy.tenant_id = "test-tenant"
        policy.data_type = DataType.APPOINTMENTS
        policy.calculate_retention_cutoff.return_value = datetime.now(timezone.utc)
        policy.legal_hold_exempt = False

        # Mock query result
        mock_result = Mock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        # Test
        result = await service.count_eligible_records(policy)

        # Verify
        assert result == 5
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_purge_records_dry_run(self, service, mock_session):
        """Test purging records in dry run mode."""
        # Create mock policy
        policy = Mock(spec=DataRetentionPolicy)
        policy.tenant_id = "test-tenant"
        policy.data_type = DataType.APPOINTMENTS
        policy.calculate_retention_cutoff.return_value = datetime.now(timezone.utc)
        policy.legal_hold_exempt = True
        policy.batch_size = 100

        # Mock records
        record1 = Mock()
        record1.id = "record-1"
        record2 = Mock()
        record2.id = "record-2"

        # Mock query results - first batch has records, second is empty
        mock_result1 = Mock()
        mock_result1.scalars.return_value.all.return_value = [record1, record2]
        mock_result2 = Mock()
        mock_result2.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_result1, mock_result2]

        with patch.object(service, "_log_purge_action", new_callable=AsyncMock):
            # Test
            result = await service.purge_records(policy, dry_run=True)

            # Verify
            assert result["success"] is True
            assert result["records_purged"] == 2
            assert result["dry_run"] is True

    @pytest.mark.asyncio
    async def test_execute_retention_policies(self, service):
        """Test executing retention policies for a tenant."""
        # Create mock policy
        policy = Mock(spec=DataRetentionPolicy)
        policy.policy_name = "Test Policy"
        policy.should_execute_now.return_value = True
        policy.update_execution_schedule = Mock()

        with patch.object(
            service, "get_active_policies", return_value=[policy]
        ), patch.object(
            service, "purge_records", new_callable=AsyncMock
        ) as mock_purge, patch.object(
            service.feature_flags, "is_enabled", return_value=True
        ):
            mock_purge.return_value = {
                "success": True,
                "records_processed": 10,
                "dry_run": True,
            }

            # Test
            result = await service.execute_retention_policies(
                "test-tenant", dry_run=True
            )

            # Verify
            assert result["success"] is True
            assert result["policies_executed"] == 1
            mock_purge.assert_called_once_with(policy, True)

    @pytest.mark.asyncio
    async def test_execute_retention_policies_feature_disabled(self, service):
        """Test executing policies when feature is disabled."""
        with patch.object(service.feature_flags, "is_enabled", return_value=False):
            # Test
            result = await service.execute_retention_policies(
                "test-tenant", dry_run=True
            )

            # Verify
            assert result["success"] is False
            assert "disabled" in result["error"]
            assert result["policies_executed"] == 0

    @pytest.mark.asyncio
    async def test_release_expired_legal_holds(self, service, mock_session):
        """Test releasing expired legal holds."""
        # Create mock expired hold
        hold = Mock(spec=LegalHold)
        hold.should_auto_release.return_value = True
        hold.release_hold = Mock()

        # Mock query result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [hold]
        mock_session.execute.return_value = mock_result

        # Test
        result = await service.release_expired_legal_holds("test-tenant")

        # Verify
        assert result["success"] is True
        assert result["holds_released"] == 1
        hold.release_hold.assert_called_once_with("system")
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_expired_legal_holds_none_expired(
        self, service, mock_session
    ):
        """Test releasing legal holds when none are expired."""
        # Create mock non-expired hold
        hold = Mock(spec=LegalHold)
        hold.should_auto_release.return_value = False

        # Mock query result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [hold]
        mock_session.execute.return_value = mock_result

        # Test
        result = await service.release_expired_legal_holds("test-tenant")

        # Verify
        assert result["success"] is True
        assert result["holds_released"] == 0
        mock_session.commit.assert_not_called()

"""Tests for data retention policy model."""

from datetime import datetime, timedelta, timezone

import pytest

from models.data_retention_policy import (
    DataRetentionPolicy,
    DataType,
    PolicyStatus,
    RetentionPeriodUnit,
)


class TestDataRetentionPolicy:
    """Test cases for DataRetentionPolicy model."""

    def test_create_policy(self):
        """Test creating a data retention policy."""
        policy = DataRetentionPolicy(
            tenant_id="test-tenant",
            policy_name="Test Policy",
            description="Test retention policy",
            data_type=DataType.APPOINTMENTS,
            retention_period=7,
            retention_unit=RetentionPeriodUnit.YEARS,
            status=PolicyStatus.ACTIVE,
        )

        assert policy.policy_name == "Test Policy"
        assert policy.data_type == DataType.APPOINTMENTS
        assert policy.retention_period == 7
        assert policy.retention_unit == RetentionPeriodUnit.YEARS
        assert policy.status == PolicyStatus.ACTIVE
        assert policy.legal_hold_exempt is False
        assert policy.dry_run_only is True  # Default
        assert policy.batch_size == 1000  # Default

    def test_calculate_retention_cutoff_years(self):
        """Test calculating retention cutoff for years."""
        policy = DataRetentionPolicy(
            tenant_id="test-tenant",
            policy_name="Test Policy",
            data_type=DataType.APPOINTMENTS,
            retention_period=7,
            retention_unit=RetentionPeriodUnit.YEARS,
        )

        cutoff = policy.calculate_retention_cutoff()
        expected_cutoff = datetime.now(timezone.utc) - timedelta(days=7 * 365)

        # Allow for small time differences in test execution
        assert abs((cutoff - expected_cutoff).total_seconds()) < 60

    def test_calculate_retention_cutoff_months(self):
        """Test calculating retention cutoff for months."""
        policy = DataRetentionPolicy(
            tenant_id="test-tenant",
            policy_name="Test Policy",
            data_type=DataType.APPOINTMENTS,
            retention_period=6,
            retention_unit=RetentionPeriodUnit.MONTHS,
        )

        cutoff = policy.calculate_retention_cutoff()
        expected_cutoff = datetime.now(timezone.utc) - timedelta(days=6 * 30)

        # Allow for small time differences in test execution
        assert abs((cutoff - expected_cutoff).total_seconds()) < 60

    def test_calculate_retention_cutoff_days(self):
        """Test calculating retention cutoff for days."""
        policy = DataRetentionPolicy(
            tenant_id="test-tenant",
            policy_name="Test Policy",
            data_type=DataType.AUTH_TOKENS,
            retention_period=90,
            retention_unit=RetentionPeriodUnit.DAYS,
        )

        cutoff = policy.calculate_retention_cutoff()
        expected_cutoff = datetime.now(timezone.utc) - timedelta(days=90)

        # Allow for small time differences in test execution
        assert abs((cutoff - expected_cutoff).total_seconds()) < 60

    def test_should_execute_now_active_no_schedule(self):
        """Test should_execute_now for active policy with no schedule."""
        policy = DataRetentionPolicy(
            tenant_id="test-tenant",
            policy_name="Test Policy",
            data_type=DataType.APPOINTMENTS,
            retention_period=7,
            retention_unit=RetentionPeriodUnit.YEARS,
            status=PolicyStatus.ACTIVE,
            next_execution_at=None,
        )

        assert policy.should_execute_now() is True

    def test_should_execute_now_inactive(self):
        """Test should_execute_now for inactive policy."""
        policy = DataRetentionPolicy(
            tenant_id="test-tenant",
            policy_name="Test Policy",
            data_type=DataType.APPOINTMENTS,
            retention_period=7,
            retention_unit=RetentionPeriodUnit.YEARS,
            status=PolicyStatus.INACTIVE,
        )

        assert policy.should_execute_now() is False

    def test_should_execute_now_scheduled_future(self):
        """Test should_execute_now for policy scheduled in future."""
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)

        policy = DataRetentionPolicy(
            tenant_id="test-tenant",
            policy_name="Test Policy",
            data_type=DataType.APPOINTMENTS,
            retention_period=7,
            retention_unit=RetentionPeriodUnit.YEARS,
            status=PolicyStatus.ACTIVE,
            next_execution_at=future_time,
        )

        assert policy.should_execute_now() is False

    def test_should_execute_now_scheduled_past(self):
        """Test should_execute_now for policy scheduled in past."""
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)

        policy = DataRetentionPolicy(
            tenant_id="test-tenant",
            policy_name="Test Policy",
            data_type=DataType.APPOINTMENTS,
            retention_period=7,
            retention_unit=RetentionPeriodUnit.YEARS,
            status=PolicyStatus.ACTIVE,
            next_execution_at=past_time,
        )

        assert policy.should_execute_now() is True

    def test_update_execution_schedule(self):
        """Test updating execution schedule."""
        policy = DataRetentionPolicy(
            tenant_id="test-tenant",
            policy_name="Test Policy",
            data_type=DataType.APPOINTMENTS,
            retention_period=7,
            retention_unit=RetentionPeriodUnit.YEARS,
        )

        before_update = datetime.now(timezone.utc)
        policy.update_execution_schedule(24)
        after_update = datetime.now(timezone.utc)

        # Check that last_executed_at is set to now
        assert policy.last_executed_at is not None
        assert before_update <= policy.last_executed_at <= after_update

        # Check that next_execution_at is set to 24 hours from now
        expected_next = policy.last_executed_at + timedelta(hours=24)
        assert policy.next_execution_at == expected_next

    def test_update_execution_schedule_custom_interval(self):
        """Test updating execution schedule with custom interval."""
        policy = DataRetentionPolicy(
            tenant_id="test-tenant",
            policy_name="Test Policy",
            data_type=DataType.APPOINTMENTS,
            retention_period=7,
            retention_unit=RetentionPeriodUnit.YEARS,
        )

        policy.update_execution_schedule(12)  # 12 hours

        expected_next = policy.last_executed_at + timedelta(hours=12)
        assert policy.next_execution_at == expected_next

    def test_repr_without_phi(self):
        """Test string representation doesn't contain PHI."""
        policy = DataRetentionPolicy(
            tenant_id="test-tenant",
            policy_name="Test Policy",
            data_type=DataType.APPOINTMENTS,
            retention_period=7,
            retention_unit=RetentionPeriodUnit.YEARS,
        )

        repr_str = repr(policy)

        # Should contain basic info
        assert "Test Policy" in repr_str
        assert "appointments" in repr_str
        assert "7 years" in repr_str

        # Should not contain tenant_id (could be PHI)
        assert "test-tenant" not in repr_str

    def test_invalid_retention_unit(self):
        """Test handling of invalid retention unit."""
        policy = DataRetentionPolicy(
            tenant_id="test-tenant",
            policy_name="Test Policy",
            data_type=DataType.APPOINTMENTS,
            retention_period=7,
            retention_unit="invalid_unit",  # Invalid unit
        )

        with pytest.raises(ValueError, match="Unknown retention unit"):
            policy.calculate_retention_cutoff()

    def test_all_data_types_supported(self):
        """Test that all data types can be used in policies."""
        for data_type in DataType:
            policy = DataRetentionPolicy(
                tenant_id="test-tenant",
                policy_name=f"Test {data_type.value} Policy",
                data_type=data_type,
                retention_period=1,
                retention_unit=RetentionPeriodUnit.YEARS,
            )

            # Should not raise an exception
            cutoff = policy.calculate_retention_cutoff()
            assert isinstance(cutoff, datetime)

    def test_all_retention_units_supported(self):
        """Test that all retention units work correctly."""
        base_time = datetime.now(timezone.utc)

        for unit in RetentionPeriodUnit:
            policy = DataRetentionPolicy(
                tenant_id="test-tenant",
                policy_name="Test Policy",
                data_type=DataType.APPOINTMENTS,
                retention_period=1,
                retention_unit=unit,
            )

            cutoff = policy.calculate_retention_cutoff()
            assert cutoff < base_time  # Should be in the past

    def test_policy_status_transitions(self):
        """Test policy status transitions."""
        policy = DataRetentionPolicy(
            tenant_id="test-tenant",
            policy_name="Test Policy",
            data_type=DataType.APPOINTMENTS,
            retention_period=7,
            retention_unit=RetentionPeriodUnit.YEARS,
            status=PolicyStatus.DRAFT,
        )

        # Draft policy should not execute
        assert policy.should_execute_now() is False

        # Activate policy
        policy.status = PolicyStatus.ACTIVE
        assert policy.should_execute_now() is True

        # Deactivate policy
        policy.status = PolicyStatus.INACTIVE
        assert policy.should_execute_now() is False

    def test_legal_hold_exempt_flag(self):
        """Test legal hold exempt flag."""
        # Default should be False
        policy = DataRetentionPolicy(
            tenant_id="test-tenant",
            policy_name="Test Policy",
            data_type=DataType.APPOINTMENTS,
            retention_period=7,
            retention_unit=RetentionPeriodUnit.YEARS,
        )

        assert policy.legal_hold_exempt is False

        # Can be set to True
        policy.legal_hold_exempt = True
        assert policy.legal_hold_exempt is True

    def test_batch_size_configuration(self):
        """Test batch size configuration."""
        policy = DataRetentionPolicy(
            tenant_id="test-tenant",
            policy_name="Test Policy",
            data_type=DataType.APPOINTMENTS,
            retention_period=7,
            retention_unit=RetentionPeriodUnit.YEARS,
            batch_size=500,
        )

        assert policy.batch_size == 500

    def test_dry_run_configuration(self):
        """Test dry run configuration."""
        # Default should be True for safety
        policy = DataRetentionPolicy(
            tenant_id="test-tenant",
            policy_name="Test Policy",
            data_type=DataType.APPOINTMENTS,
            retention_period=7,
            retention_unit=RetentionPeriodUnit.YEARS,
        )

        assert policy.dry_run_only is True

        # Can be disabled
        policy.dry_run_only = False
        assert policy.dry_run_only is False

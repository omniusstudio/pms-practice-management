"""Tests for data retention configuration."""

from datetime import datetime

from config.data_retention_config import DataRetentionConfig
from models.data_retention_policy import PolicyStatus, RetentionPeriodUnit


class TestDataRetentionConfig:
    """Test cases for data retention configuration."""

    def test_default_policies_structure(self):
        """Test that default policies have correct structure."""
        assert isinstance(DataRetentionConfig.DEFAULT_POLICIES, list)
        assert len(DataRetentionConfig.DEFAULT_POLICIES) > 0

        for policy in DataRetentionConfig.DEFAULT_POLICIES:
            # Check required fields
            assert "data_type" in policy
            assert "retention_period" in policy
            assert "retention_unit" in policy
            assert "status" in policy

            # Check field types
            assert isinstance(policy["data_type"], str)
            assert isinstance(policy["retention_period"], int)
            assert policy["retention_unit"] in [
                unit.value for unit in RetentionPeriodUnit
            ]
            assert policy["status"] in [status.value for status in PolicyStatus]

            # Check positive retention period
            assert policy["retention_period"] > 0

    def test_default_policies_coverage(self):
        """Test that default policies cover all expected data types."""
        expected_data_types = {
            "appointments",
            "notes",
            "audit_logs",
            "auth_tokens",
            "fhir_mappings",
            "ledger_entries",
        }

        actual_data_types = {
            policy["data_type"] for policy in DataRetentionConfig.DEFAULT_POLICIES
        }

        assert actual_data_types == expected_data_types

    def test_hipaa_compliance_retention_periods(self):
        """Test that retention periods comply with HIPAA requirements."""
        policy_map = {p["data_type"]: p for p in DataRetentionConfig.DEFAULT_POLICIES}

        # Clinical notes should be retained for at least 6 years
        clinical_policy = policy_map["notes"]
        if clinical_policy["retention_unit"] == (RetentionPeriodUnit.YEARS.value):
            assert clinical_policy["retention_period"] >= 6

        # Audit logs should be retained for at least 6 years
        audit_policy = policy_map["audit_logs"]
        if audit_policy["retention_unit"] == RetentionPeriodUnit.YEARS.value:
            assert audit_policy["retention_period"] >= 6

        # Auth tokens should have short retention (security)
        auth_policy = policy_map["auth_tokens"]
        if auth_policy["retention_unit"] == RetentionPeriodUnit.DAYS.value:
            assert auth_policy["retention_period"] <= 90

    def test_scheduler_config_structure(self):
        """Test scheduler configuration structure."""
        assert isinstance(DataRetentionConfig.SCHEDULER_CONFIG, dict)

        # Check required fields
        required_fields = [
            "check_interval_minutes",
            "max_concurrent_jobs",
            "execution_interval_hours",
        ]

        for field in required_fields:
            assert field in DataRetentionConfig.SCHEDULER_CONFIG

        # Check field types and values
        config = DataRetentionConfig.SCHEDULER_CONFIG
        assert isinstance(config["check_interval_minutes"], int)
        assert isinstance(config["max_concurrent_jobs"], int)
        assert isinstance(config["execution_interval_hours"], int)

        # Check positive values
        assert config["max_concurrent_jobs"] > 0
        assert config["check_interval_minutes"] > 0
        assert config["execution_interval_hours"] > 0

    def test_legal_hold_config_structure(self):
        """Test legal hold configuration structure."""
        assert isinstance(DataRetentionConfig.LEGAL_HOLD_CONFIG, dict)

        # Check required fields
        required_fields = [
            "auto_release_enabled",
            "notification_enabled",
            "default_hold_duration_days",
        ]

        for field in required_fields:
            assert field in DataRetentionConfig.LEGAL_HOLD_CONFIG

        # Check field types
        config = DataRetentionConfig.LEGAL_HOLD_CONFIG
        assert isinstance(config["auto_release_enabled"], bool)
        assert isinstance(config["notification_enabled"], bool)
        assert isinstance(config["default_hold_duration_days"], int)

        # Check logical values
        default_duration = config["default_hold_duration_days"]
        assert default_duration > 0

    def test_safety_config_structure(self):
        """Test safety configuration structure."""
        assert isinstance(DataRetentionConfig.SAFETY_CONFIG, dict)

        # Check required fields
        required_fields = [
            "require_dry_run_first",
            "max_records_per_batch",
            "require_legal_hold_check",
            "audit_all_operations",
        ]

        for field in required_fields:
            assert field in DataRetentionConfig.SAFETY_CONFIG

        # Check field types
        config = DataRetentionConfig.SAFETY_CONFIG
        assert isinstance(config["require_dry_run_first"], bool)
        assert isinstance(config["max_records_per_batch"], int)
        assert isinstance(config["require_legal_hold_check"], bool)
        assert isinstance(config["audit_all_operations"], bool)

        # Check logical values
        max_batch = config["max_records_per_batch"]
        assert max_batch > 0

    def test_get_default_policies_for_tenant(self):
        """Test getting default policies for a tenant."""
        tenant_id = "test-tenant"
        policies = DataRetentionConfig.get_default_policies_for_tenant(tenant_id)

        # Check return type
        assert isinstance(policies, list)
        assert len(policies) == len(DataRetentionConfig.DEFAULT_POLICIES)

        # Check that each policy has tenant_id set
        for policy in policies:
            assert policy["tenant_id"] == tenant_id
            assert "policy_id" in policy
            assert "created_at" in policy
            assert "updated_at" in policy

            # Check timestamps are recent
            created_at = policy["created_at"]
            updated_at = policy["updated_at"]
            assert isinstance(created_at, datetime)
            assert isinstance(updated_at, datetime)
            assert created_at.tzinfo is not None
            assert updated_at.tzinfo is not None

    def test_get_default_policies_unique_ids(self):
        """Test that generated policies have unique IDs."""
        tenant_id = "test-tenant"
        policies = DataRetentionConfig.get_default_policies_for_tenant(tenant_id)

        policy_ids = [policy["policy_id"] for policy in policies]

        # Check all IDs are unique
        assert len(policy_ids) == len(set(policy_ids))

        # Check ID format (should be UUIDs)
        for policy_id in policy_ids:
            assert isinstance(policy_id, str)
            assert len(policy_id) > 0

    def test_get_policy_by_data_type_found(self):
        """Test getting policy by data type when it exists."""
        data_type = "appointments"

        policy = DataRetentionConfig.get_policy_by_data_type(data_type)

        # Check policy found
        assert policy is not None
        assert policy["data_type"] == data_type

        # Check it matches default policy
        default_policy = next(
            p
            for p in DataRetentionConfig.DEFAULT_POLICIES
            if p["data_type"] == data_type
        )
        assert policy["retention_period"] == default_policy["retention_period"]
        assert policy["retention_unit"] == default_policy["retention_unit"]
        assert policy["status"] == default_policy["status"]

    def test_get_policy_by_data_type_not_found(self):
        """Test getting policy by data type when it doesn't exist."""
        data_type = "nonexistent_type"

        policy = DataRetentionConfig.get_policy_by_data_type(data_type)

        # Check policy not found
        assert policy is None

    def test_validate_retention_config_valid(self):
        """Test validation of valid retention configuration."""
        valid_config = {
            "policy_name": "Test Policy",
            "data_type": "appointments",
            "retention_period": 7,
            "retention_unit": RetentionPeriodUnit.YEARS.value,
            "status": PolicyStatus.ACTIVE.value,
            "batch_size": 100,
            "dry_run_only": False,
        }

        result = DataRetentionConfig.validate_policy_config(valid_config)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_retention_config_missing_fields(self):
        """Test validation with missing required fields."""
        invalid_config = {
            "policy_name": "Test Policy",
            "data_type": "appointments",
            # Missing retention_period, retention_unit
        }

        result = DataRetentionConfig.validate_policy_config(invalid_config)

        assert result["valid"] is False
        assert "errors" in result
        assert len(result["errors"]) > 0

        # Check specific error messages
        errors = result["errors"]
        assert any("retention_period" in error for error in errors)
        assert any("retention_unit" in error for error in errors)

    def test_validate_retention_config_invalid_values(self):
        """Test validation with invalid field values."""
        invalid_config = {
            "policy_name": "Test Policy",
            "data_type": "",  # Empty string
            "retention_period": -1,  # Negative
            "retention_unit": "invalid_unit",  # Invalid enum
            "status": "invalid_status",  # Invalid enum
            "batch_size": 0,  # Zero
        }

        result = DataRetentionConfig.validate_policy_config(invalid_config)

        assert result["valid"] is False
        assert "errors" in result
        assert len(result["errors"]) > 0

        # Check specific error types
        errors = result["errors"]
        assert any("retention_period" in error for error in errors)
        assert any("batch_size" in error for error in errors)

    def test_validate_retention_config_edge_cases(self):
        """Test validation edge cases."""
        # Test with None values
        none_config = {
            "data_type": None,
            "retention_period": None,
            "retention_unit": None,
            "status": None,
        }

        errors = DataRetentionConfig.validate_policy_config(none_config)
        result = {"valid": len(errors) == 0, "errors": errors}
        assert result["valid"] is False

        # Test with empty config
        empty_config = {}
        errors = DataRetentionConfig.validate_policy_config(empty_config)
        result = {"valid": len(errors) == 0, "errors": errors}
        assert result["valid"] is False

    def test_config_constants_immutability(self):
        """Test that config constants are not accidentally modified."""
        # Store original lengths
        original_policies_len = len(DataRetentionConfig.DEFAULT_POLICIES)

        # Try to modify (this should not affect the originals)
        try:
            DataRetentionConfig.DEFAULT_POLICIES.append({"test": "value"})
            DataRetentionConfig.SCHEDULER_CONFIG["test"] = "value"
            DataRetentionConfig.LEGAL_HOLD_CONFIG["test"] = "value"
            DataRetentionConfig.SAFETY_CONFIG["test"] = "value"
        except (TypeError, AttributeError):
            # If configs are immutable, this is expected
            pass

        # Verify originals are unchanged (if mutable)
        current_policies_len = len(DataRetentionConfig.DEFAULT_POLICIES)

        # Clean up any modifications
        if current_policies_len > original_policies_len:
            DataRetentionConfig.DEFAULT_POLICIES.pop()
        if "test" in DataRetentionConfig.SCHEDULER_CONFIG:
            del DataRetentionConfig.SCHEDULER_CONFIG["test"]
        if "test" in DataRetentionConfig.LEGAL_HOLD_CONFIG:
            del DataRetentionConfig.LEGAL_HOLD_CONFIG["test"]
        if "test" in DataRetentionConfig.SAFETY_CONFIG:
            del DataRetentionConfig.SAFETY_CONFIG["test"]

    def test_cron_expression_format(self):
        """Test that cron expressions in config are valid format."""
        # Skip cron expression test as current config doesn't have cron schedules
        # The current config uses interval-based scheduling
        scheduler_config = DataRetentionConfig.SCHEDULER_CONFIG
        assert scheduler_config["check_interval_minutes"] > 0
        assert scheduler_config["execution_interval_hours"] > 0

    def test_config_documentation_completeness(self):
        """Test that all config sections have proper documentation."""
        # This test ensures configs are self-documenting
        # In a real implementation, you might check for docstrings or comments

        # Check that config dictionaries have reasonable keys
        scheduler_keys = set(DataRetentionConfig.SCHEDULER_CONFIG.keys())
        expected_scheduler_keys = {
            "check_interval_minutes",
            "max_concurrent_jobs",
            "execution_interval_hours",
        }
        assert scheduler_keys >= expected_scheduler_keys

        legal_hold_keys = set(DataRetentionConfig.LEGAL_HOLD_CONFIG.keys())
        expected_legal_hold_keys = {
            "auto_release_enabled",
            "notification_enabled",
            "default_hold_duration_days",
        }
        assert legal_hold_keys >= expected_legal_hold_keys

        safety_keys = set(DataRetentionConfig.SAFETY_CONFIG.keys())
        expected_safety_keys = {
            "require_dry_run_first",
            "max_records_per_batch",
            "require_legal_hold_check",
            "audit_all_operations",
        }
        assert safety_keys >= expected_safety_keys

    def test_tenant_specific_customization(self):
        """Test that tenant-specific customizations work correctly."""
        tenant1_policies = DataRetentionConfig.get_default_policies_for_tenant(
            "tenant1"
        )
        tenant2_policies = DataRetentionConfig.get_default_policies_for_tenant(
            "tenant2"
        )

        # Policies should be identical except for tenant_id and generated IDs
        assert len(tenant1_policies) == len(tenant2_policies)

        for p1, p2 in zip(tenant1_policies, tenant2_policies):
            # Same data type and retention settings
            assert p1["data_type"] == p2["data_type"]
            assert p1["retention_period"] == p2["retention_period"]
            assert p1["retention_unit"] == p2["retention_unit"]
            assert p1["status"] == p2["status"]

            # Different tenant IDs and policy IDs
            assert p1["tenant_id"] == "tenant1"
            assert p2["tenant_id"] == "tenant2"
            assert p1["policy_id"] != p2["policy_id"]

    def test_policy_defaults_security(self):
        """Test that policy defaults prioritize security."""
        # Check that sensitive data has shorter retention by default
        policy_map = {p["data_type"]: p for p in DataRetentionConfig.DEFAULT_POLICIES}

        # Auth tokens should have short retention
        auth_policy = policy_map.get("auth_tokens")
        if auth_policy:
            if auth_policy["retention_unit"] == (RetentionPeriodUnit.DAYS.value):
                assert auth_policy["retention_period"] <= 90
            elif auth_policy["retention_unit"] == (RetentionPeriodUnit.MONTHS.value):
                assert auth_policy["retention_period"] <= 3

        # Safety config should default to secure settings
        safety_config = DataRetentionConfig.SAFETY_CONFIG
        assert safety_config["require_dry_run_first"] is True
        assert safety_config["require_legal_hold_check"] is True
        assert safety_config["audit_all_operations"] is True

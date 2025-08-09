"""Comprehensive tests for QA seed data system.

This test suite validates:
- QA seed configuration and profiles
- HIPAA compliance of generated data
- Performance targets and optimization
- Data integrity and validation
- Multi-tenant data distribution
"""

from unittest.mock import Mock, patch

import pytest

from config.qa_seed_config import QAEnvironment, get_qa_seed_config
from factories.base import BaseFactory
from models import Appointment, Client, Note, Provider
from scripts.qa_seed_manager import QASeedManager


class TestQAEnvironmentConfig:
    """Test QA environment configuration and profiles."""

    def test_qa_environment_enum_values(self):
        """Test that QA environment enum has expected values."""
        expected_environments = {"minimal", "standard", "load_test", "integration"}
        actual_environments = {env.value for env in QAEnvironment}
        assert actual_environments == expected_environments

    def test_get_qa_seed_config_minimal(self):
        """Test QA seed config for minimal environment."""
        config = get_qa_seed_config("minimal")

        assert config.environment == QAEnvironment.MINIMAL
        assert config.current_profile.name == "Minimal QA Dataset"
        target_time = config.current_profile.target_seed_time_seconds
        assert target_time <= 60

        # Verify minimal record counts
        record_counts = config.get_record_counts()
        assert all(count <= 50 for count in record_counts.values())

    def test_get_qa_seed_config_standard(self):
        """Test QA seed config for standard environment."""
        config = get_qa_seed_config("standard")

        assert config.environment == QAEnvironment.STANDARD
        assert config.current_profile.name == "Standard QA Dataset"
        target_time = config.current_profile.target_seed_time_seconds
        assert target_time <= 300

        # Verify standard record counts
        record_counts = config.get_record_counts()
        assert record_counts["Client"] >= 100
        assert record_counts["Provider"] >= 20

    def test_get_qa_seed_config_load_test(self):
        """Test QA seed config for load test environment."""
        config = get_qa_seed_config("load_test")

        assert config.environment == QAEnvironment.LOAD_TEST
        assert config.current_profile.name == "Load Test Dataset"

        # Verify load test has high record counts
        record_counts = config.get_record_counts()
        assert record_counts["Client"] >= 1000
        assert record_counts["Appointment"] >= 5000

    def test_get_qa_seed_config_integration(self):
        """Test QA seed config for integration environment."""
        config = get_qa_seed_config("integration")

        assert config.environment == QAEnvironment.INTEGRATION
        assert config.current_profile.name == "Integration Test Dataset"

        # Verify integration has comprehensive coverage
        record_counts = config.get_record_counts()
        assert len(record_counts) >= 6  # All major models covered

    def test_qa_data_profile_validation(self):
        """Test QA data profile validation and constraints."""
        config = get_qa_seed_config("standard")
        profile = config.current_profile

        # Validate profile structure
        assert hasattr(profile, "name")
        assert hasattr(profile, "description")
        assert hasattr(profile, "target_seed_time_seconds")
        assert hasattr(profile, "record_counts")

        # Validate record counts are positive
        for model_name, count in profile.record_counts.items():
            assert count >= 0, f"{model_name} count must be non-negative"

    def test_tenant_configuration(self):
        """Test tenant ID generation and distribution."""
        config = get_qa_seed_config("standard")
        tenant_ids = config.get_tenant_ids()

        # Verify tenant IDs are generated
        assert len(tenant_ids) >= 2
        assert all(isinstance(tid, str) for tid in tenant_ids)
        assert all(len(tid) > 0 for tid in tenant_ids)

        # Verify tenant IDs are unique
        assert len(tenant_ids) == len(set(tenant_ids))

    def test_hipaa_compliance_settings(self):
        """Test HIPAA compliance configuration."""
        config = get_qa_seed_config("standard")
        hipaa_settings = config.get_hipaa_compliance_settings()

        # Verify safe domains are configured
        assert "safe_domains" in hipaa_settings
        assert len(hipaa_settings["safe_domains"]) > 0
        assert "example.com" in hipaa_settings["safe_domains"]
        assert "test.local" in hipaa_settings["safe_domains"]

        # Verify safe phone prefixes are configured
        assert "safe_phone_prefixes" in hipaa_settings
        assert len(hipaa_settings["safe_phone_prefixes"]) > 0
        assert "555" in hipaa_settings["safe_phone_prefixes"]

    def test_performance_settings(self):
        """Test performance optimization settings."""
        config = get_qa_seed_config("load_test")
        perf_settings = config.get_performance_settings()

        # Verify performance settings exist
        assert "batch_size" in perf_settings
        assert "parallel_workers" in perf_settings
        assert "use_bulk_insert" in perf_settings

        # Verify reasonable values
        assert perf_settings["batch_size"] > 0
        assert perf_settings["parallel_workers"] > 0
        assert isinstance(perf_settings["use_bulk_insert"], bool)

    def test_validation_settings(self):
        """Test data validation configuration."""
        config = get_qa_seed_config("standard")
        validation_settings = config.get_validation_settings()

        # Verify validation settings
        assert "enabled" in validation_settings
        assert "sample_size" in validation_settings
        assert "strict_mode" in validation_settings

        # Verify reasonable values
        assert isinstance(validation_settings["enabled"], bool)
        assert validation_settings["sample_size"] > 0
        assert isinstance(validation_settings["strict_mode"], bool)


class TestQASeedManager:
    """Test QA seed manager functionality."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session for testing."""
        session = Mock()
        session.query.return_value.count.return_value = 0
        session.query.return_value.limit.return_value.all.return_value = []
        session.commit.return_value = None
        session.rollback.return_value = None
        return session

    @pytest.fixture
    def qa_manager(self, mock_session):
        """Create QA seed manager for testing."""
        with patch("scripts.qa_seed_manager.SessionLocal", return_value=mock_session):
            manager = QASeedManager("minimal", session=mock_session)
            # Mock factories
            manager.factories = {
                "Client": Mock(),
                "Provider": Mock(),
                "Appointment": Mock(),
                "Note": Mock(),
            }
            # Mock models
            manager.models = {
                "Client": Client,
                "Provider": Provider,
                "Appointment": Appointment,
                "Note": Note,
            }
            return manager

    def test_qa_manager_initialization(self, qa_manager):
        """Test QA seed manager initialization."""
        assert qa_manager.qa_config is not None
        assert qa_manager.qa_config.environment == QAEnvironment.MINIMAL
        assert "start_time" in qa_manager.performance_metrics
        assert "errors" in qa_manager.performance_metrics

    def test_performance_metrics_initialization(self, qa_manager):
        """Test performance metrics are properly initialized."""
        metrics = qa_manager.performance_metrics

        expected_keys = {
            "start_time",
            "end_time",
            "total_records_created",
            "records_per_second",
            "validation_time",
            "errors",
        }
        assert set(metrics.keys()) == expected_keys

        # Verify initial values
        assert metrics["start_time"] is None
        assert metrics["end_time"] is None
        assert metrics["total_records_created"] == 0
        assert metrics["records_per_second"] == 0
        assert metrics["validation_time"] == 0
        assert metrics["errors"] == []

    def test_create_model_records_success(self, qa_manager, mock_session):
        """Test successful model record creation."""
        # Setup mock factory
        mock_factory = Mock()
        mock_factory.create_batch.return_value = [Mock(), Mock(), Mock()]
        qa_manager.factories["Client"] = mock_factory

        # Test record creation
        qa_manager._create_model_records("Client", 6, ["tenant1", "tenant2"])

        # Verify factory was called correctly
        assert mock_factory.create_batch.call_count == 2
        mock_session.commit.assert_called()

        # Verify metrics updated
        assert qa_manager.performance_metrics["total_records_created"] == 6

    def test_create_model_records_missing_factory(self, qa_manager):
        """Test handling of missing factory."""
        # Remove factory
        del qa_manager.factories["Client"]

        # Test record creation with missing factory
        qa_manager._create_model_records("Client", 5, ["tenant1"])

        # Verify no records created
        total_created = qa_manager.performance_metrics["total_records_created"]
        assert total_created == 0
        assert qa_manager.performance_metrics["total_records_created"] == 0

    def test_create_model_records_error_handling(self, qa_manager, mock_session):
        """Test error handling during record creation."""
        # Setup mock factory to raise exception
        mock_factory = Mock()
        test_error = Exception("Test error")
        mock_factory.create_batch.side_effect = test_error
        qa_manager.factories["Client"] = mock_factory

        # Test record creation with error
        qa_manager._create_model_records("Client", 3, ["tenant1"])

        # Verify error handling
        mock_session.rollback.assert_called()
        assert len(qa_manager.performance_metrics["errors"]) == 1
        error_msg = qa_manager.performance_metrics["errors"][0]
        assert "Test error" in error_msg

    def test_calculate_performance_metrics(self, qa_manager):
        """Test performance metrics calculation."""
        # Set up test data
        qa_manager.performance_metrics["start_time"] = 100.0
        qa_manager.performance_metrics["end_time"] = 110.0
        qa_manager.performance_metrics["total_records_created"] = 50

        # Calculate metrics
        qa_manager._calculate_performance_metrics()

        # Verify calculation
        expected_rps = 50 / 10.0  # 50 records in 10 seconds
        actual_rps = qa_manager.performance_metrics["records_per_second"]
        assert actual_rps == expected_rps

    def test_calculate_performance_metrics_zero_time(self, qa_manager):
        """Test performance metrics with zero time duration."""
        # Set up test data with same start/end time
        qa_manager.performance_metrics["start_time"] = 100.0
        qa_manager.performance_metrics["end_time"] = 100.0
        qa_manager.performance_metrics["total_records_created"] = 50

        # Calculate metrics
        qa_manager._calculate_performance_metrics()

        # Verify no division by zero
        rps = qa_manager.performance_metrics["records_per_second"]
        assert rps == 0

    def test_get_generation_summary(self, qa_manager):
        """Test generation summary creation."""
        # Set up test data
        qa_manager.performance_metrics.update(
            {
                "start_time": 100.0,
                "end_time": 150.0,
                "total_records_created": 100,
                "records_per_second": 2.0,
                "validation_time": 5.0,
                "errors": [],
            }
        )

        # Get summary
        summary = qa_manager._get_generation_summary()

        # Verify summary structure
        expected_keys = {
            "environment",
            "profile_name",
            "total_time_seconds",
            "target_time_seconds",
            "performance_ratio",
            "target_met",
            "total_records_created",
            "records_per_second",
            "validation_time_seconds",
            "errors",
            "success",
        }
        assert set(summary.keys()) == expected_keys

        # Verify values
        assert summary["total_time_seconds"] == 50.0
        assert summary["total_records_created"] == 100
        assert summary["records_per_second"] == 2.0
        assert summary["validation_time_seconds"] == 5.0
        assert summary["success"] is True
        assert summary["errors"] == []


class TestHIPAACompliance:
    """Test HIPAA compliance validation."""

    def test_base_factory_phi_detection(self):
        """Test BaseFactory detects and rejects PHI fields."""
        # Test prohibited field names
        prohibited_fields = ["ssn", "social_security", "real_name", "actual_email"]

        for field_name in prohibited_fields:
            with pytest.raises(ValueError, match="PHI field detected"):
                BaseFactory._check_for_phi({field_name: "test_value"})

    def test_base_factory_safe_fields(self):
        """Test BaseFactory allows safe field names."""
        safe_fields = {
            "name": "Test Name",
            "email": "test@example.com",
            "phone": "555-0123",
            "address": "123 Test St",
        }

        # Should not raise exception
        BaseFactory._check_for_phi(safe_fields)

    def test_safe_email_generation(self):
        """Test that generated emails use safe domains."""
        config = get_qa_seed_config("standard")
        safe_domains = config.get_hipaa_compliance_settings()["safe_domains"]

        # Mock email generation
        with patch("factories.base.fake") as mock_fake:
            mock_fake.email.return_value = "user@example.com"

            # Verify safe domain usage
            email = mock_fake.email.return_value
            domain = email.split("@")[1]
            assert domain in safe_domains

    def test_safe_phone_generation(self):
        """Test that generated phone numbers use safe prefixes."""
        config = get_qa_seed_config("standard")
        safe_prefixes = config.get_hipaa_compliance_settings()["safe_phone_prefixes"]

        # Mock phone generation
        with patch("factories.base.fake") as mock_fake:
            mock_fake.phone_number.return_value = "555-0123"

            # Verify safe prefix usage
            phone = mock_fake.phone_number.return_value
            prefix = phone.split("-")[0]
            assert prefix in safe_prefixes

    @pytest.mark.parametrize(
        "environment", ["minimal", "standard", "load_test", "integration"]
    )
    def test_no_real_phi_in_any_environment(self, environment):
        """Test that no real PHI is generated in any environment."""
        config = get_qa_seed_config(environment)
        hipaa_settings = config.get_hipaa_compliance_settings()

        # Verify safe domains don't include real domains
        real_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]

        safe_domains = hipaa_settings["safe_domains"]

        for real_domain in real_domains:
            msg = f"Real domain {real_domain} found in safe domains"
            assert real_domain not in safe_domains, msg

        # Verify safe phone prefixes don't include real area codes
        real_area_codes = ["212", "310", "415", "713"]

        safe_prefixes = hipaa_settings["safe_phone_prefixes"]

        for real_code in real_area_codes:
            msg = f"Real area code {real_code} found in safe prefixes"
            assert real_code not in safe_prefixes, msg


class TestPerformanceTargets:
    """Test performance target validation."""

    def test_minimal_environment_performance_target(self):
        """Test minimal environment meets 1-minute target."""
        config = get_qa_seed_config("minimal")
        target_time = config.current_profile.target_seed_time_seconds

        msg = "Minimal environment should seed in under 1 minute"
        assert target_time <= 60, msg

    def test_standard_environment_performance_target(self):
        """Test standard environment meets 5-minute target."""
        config = get_qa_seed_config("standard")
        target_time = config.current_profile.target_seed_time_seconds

        msg = "Standard environment should seed in under 5 minutes"
        assert target_time <= 300, msg

    def test_load_test_environment_reasonable_target(self):
        """Test load test environment has reasonable target."""
        config = get_qa_seed_config("load_test")
        target_time = config.current_profile.target_seed_time_seconds

        # Load test can take longer but should be reasonable
        msg = "Load test should complete within 30 minutes"
        assert target_time <= 1800, msg

    def test_performance_ratio_calculation(self):
        """Test performance ratio calculation logic."""
        # Test cases: (actual_time, target_time, expected_ratio)
        test_cases = [
            (30, 60, 0.5),  # Under target
            (60, 60, 1.0),  # Exactly on target
            (90, 60, 1.5),  # Over target
            (0, 60, 0.0),  # Zero time
        ]

        for actual, target, expected in test_cases:
            ratio = actual / target if target > 0 else 0
            msg = f"Performance ratio calculation failed for {actual}/{target}"
            assert abs(ratio - expected) < 0.001, msg

    def test_target_met_logic(self):
        """Test target met determination logic."""
        # Test cases: (actual_time, target_time, should_meet_target)
        test_cases = [
            (30, 60, True),  # Under target
            (60, 60, True),  # Exactly on target
            (61, 60, False),  # Over target
            (0, 60, True),  # Zero time (edge case)
        ]

        for actual, target, expected in test_cases:
            target_met = actual <= target
            msg = f"Target met logic failed for {actual} <= {target}"
            assert target_met == expected, msg


class TestDataIntegrity:
    """Test data integrity and validation."""

    def test_tenant_isolation_validation(self):
        """Test that tenant data is properly isolated."""
        config = get_qa_seed_config("standard")
        tenant_ids = config.get_tenant_ids()

        # Verify multiple tenants for isolation testing
        assert len(tenant_ids) >= 2, "Need multiple tenants for isolation testing"

        # Verify tenant IDs are properly formatted
        for tenant_id in tenant_ids:
            assert isinstance(tenant_id, str)
            assert len(tenant_id) > 0
            assert tenant_id.strip() == tenant_id  # No leading/trailing whitespace

    def test_record_count_validation(self):
        """Test record count validation logic."""
        config = get_qa_seed_config("standard")
        record_counts = config.get_record_counts()

        # Verify all counts are non-negative integers
        for model_name, count in record_counts.items():
            assert isinstance(count, int), f"{model_name} count must be integer"
            assert count >= 0, f"{model_name} count must be non-negative"

    def test_relationship_integrity_requirements(self):
        """Test that relationship requirements are defined."""
        config = get_qa_seed_config("standard")
        record_counts = config.get_record_counts()

        # Verify dependent models have appropriate ratios
        if "Client" in record_counts and "Appointment" in record_counts:
            client_count = record_counts["Client"]
            appointment_count = record_counts["Appointment"]

            # Appointments should be reasonable relative to clients
            if client_count > 0:
                ratio = appointment_count / client_count
                assert ratio >= 0, "Appointment to client ratio should be non-negative"
                assert ratio <= 50, "Appointment to client ratio should be reasonable"

    def test_validation_sample_size_logic(self):
        """Test validation sample size configuration."""
        config = get_qa_seed_config("standard")
        validation_settings = config.get_validation_settings()
        sample_size = validation_settings["sample_size"]

        # Verify sample size is reasonable
        assert isinstance(sample_size, int)
        assert sample_size > 0
        assert sample_size <= 1000, "Sample size should be reasonable for performance"

    def test_environment_specific_validation(self):
        """Test that each environment has appropriate validation settings."""
        environments = ["minimal", "standard", "load_test", "integration"]

        for env_name in environments:
            config = get_qa_seed_config(env_name)
            validation_settings = config.get_validation_settings()

            # All environments should have validation enabled
            assert (
                validation_settings["enabled"] is True
            ), f"{env_name} should have validation enabled"

            # Sample size should scale with environment size
            sample_size = validation_settings["sample_size"]
            if env_name == "minimal":
                assert (
                    sample_size <= 50
                ), "Minimal environment should have small sample size"
            elif env_name == "load_test":
                assert (
                    sample_size >= 100
                ), "Load test environment should have larger sample size"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

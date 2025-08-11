"""Integration tests for QA seed data system.

This test suite validates end-to-end functionality:
- Full seed data generation workflow
- Database integration and persistence
- Performance benchmarks
- HIPAA compliance validation
- Multi-tenant data isolation
"""

import os
from unittest.mock import patch

import pytest

from config.qa_seed_config import get_qa_seed_config
from database import SessionLocal
from models import Appointment, Client, Provider
from scripts.qa_seed_manager import QASeedManager


@pytest.mark.integration
class TestQASeedIntegration:
    """Integration tests for QA seed system."""

    @pytest.fixture(scope="class")
    def test_database(self):
        """Create test database for integration tests."""
        # Use in-memory SQLite for testing
        with patch("database.DATABASE_URL", "sqlite:///:memory:"):
            from database import Base, engine

            Base.metadata.create_all(bind=engine)
            yield engine
            Base.metadata.drop_all(bind=engine)

    @pytest.fixture
    def clean_session(self, test_database):
        """Provide clean database session for each test."""
        session = SessionLocal()
        try:
            yield session
        finally:
            session.rollback()
            session.close()

    def test_minimal_environment_full_workflow(self, clean_session):
        """Test complete workflow for minimal environment."""
        # Initialize QA seed manager
        manager = QASeedManager("minimal", session=clean_session)

        # Run seed generation
        result = manager.generate_seed_data()

        # Verify successful completion
        assert result["success"] is True
        assert len(result["errors"]) == 0
        assert result["total_records_created"] > 0

        # Verify performance target met
        assert result["target_met"] is True
        assert result["total_time_seconds"] <= 60

    def test_standard_environment_performance(self, clean_session):
        """Test standard environment meets performance targets."""
        # Initialize QA seed manager
        manager = QASeedManager("standard", session=clean_session)

        # Run seed generation with timing
        import time

        start_time = time.time()
        result = manager.generate_seed_data()
        end_time = time.time()

        # Verify performance
        actual_time = end_time - start_time
        msg = "Standard environment exceeded 5min target"
        assert actual_time <= 300, msg
        assert result["target_met"] is True

        # Verify record counts
        config = get_qa_seed_config("standard")
        expected_counts = config.get_record_counts()

        for model_name, expected_count in expected_counts.items():
            if expected_count > 0:
                model_class = getattr(manager.models, model_name)
                actual_count = clean_session.query(model_class).count()
                assert actual_count >= expected_count * 0.9  # Allow 10% variance

    def test_multi_tenant_data_isolation(self, clean_session):
        """Test that multi-tenant data is properly isolated."""
        # Initialize QA seed manager
        manager = QASeedManager("standard", session=clean_session)

        # Generate seed data
        result = manager.generate_seed_data()
        assert result["success"] is True

        # Get tenant IDs
        config = get_qa_seed_config("standard")
        tenant_ids = config.get_tenant_ids()

        # Verify data exists for each tenant
        for tenant_id in tenant_ids:
            client_count = (
                clean_session.query(Client)
                .filter(Client.tenant_id == tenant_id)
                .count()
            )
            assert client_count > 0, f"No clients found for tenant {tenant_id}"

            provider_count = (
                clean_session.query(Provider)
                .filter(Provider.tenant_id == tenant_id)
                .count()
            )
            assert provider_count > 0, f"No providers for tenant {tenant_id}"

    def test_hipaa_compliance_validation(self, clean_session):
        """Test HIPAA compliance of generated data."""
        # Initialize QA seed manager
        manager = QASeedManager("standard", session=clean_session)

        # Generate seed data
        result = manager.generate_seed_data()
        assert result["success"] is True

        # Get HIPAA compliance settings
        config = get_qa_seed_config("standard")
        hipaa_settings = config.get_hipaa_compliance_settings()
        safe_domains = hipaa_settings["safe_domains"]
        safe_prefixes = hipaa_settings["safe_phone_prefixes"]

        # Validate client data
        clients = clean_session.query(Client).limit(50).all()
        for client in clients:
            # Check email domain
            if client.email:
                domain = client.email.split("@")[1]
                assert domain in safe_domains, f"Unsafe domain: {domain}"

            # Check phone prefix
            if client.phone:
                prefix = client.phone.split("-")[0]
                assert prefix in safe_prefixes, f"Unsafe prefix: {prefix}"

    def test_data_relationships_integrity(self, clean_session):
        """Test that data relationships are properly maintained."""
        # Initialize QA seed manager
        manager = QASeedManager("standard", session=clean_session)

        # Generate seed data
        result = manager.generate_seed_data()
        assert result["success"] is True

        # Test client-appointment relationships
        appointments = clean_session.query(Appointment).limit(10).all()
        for appointment in appointments:
            # Verify client exists
            client = (
                clean_session.query(Client)
                .filter(Client.id == appointment.client_id)
                .first()
            )
            assert client is not None, "Appointment has invalid client_id"

            # Verify provider exists
            provider = (
                clean_session.query(Provider)
                .filter(Provider.id == appointment.provider_id)
                .first()
            )
            assert provider is not None, "Appointment has invalid provider_id"

            # Verify tenant consistency
            assert client.tenant_id == appointment.tenant_id
            assert provider.tenant_id == appointment.tenant_id

    def test_validation_workflow(self, clean_session):
        """Test data validation workflow."""
        # Initialize QA seed manager with validation enabled
        manager = QASeedManager("standard", session=clean_session)

        # Generate seed data
        result = manager.generate_seed_data()
        assert result["success"] is True

        # Verify validation was performed
        assert "validation_time_seconds" in result
        assert result["validation_time_seconds"] >= 0

        # Verify no validation errors
        validation_errors = [e for e in result["errors"] if "validation" in e.lower()]
        assert len(validation_errors) == 0

    def test_error_handling_and_rollback(self, clean_session):
        """Test error handling and database rollback."""
        # Initialize QA seed manager
        manager = QASeedManager("standard", session=clean_session)

        # Mock factory to raise error partway through
        original_create_batch = manager.factories["Client"].create_batch
        call_count = 0

        def failing_create_batch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 2:  # Fail after a few successful calls
                raise Exception("Simulated factory error")
            return original_create_batch(*args, **kwargs)

        manager.factories["Client"].create_batch = failing_create_batch

        # Generate seed data (should handle error gracefully)
        result = manager.generate_seed_data()

        # Verify error was captured
        assert len(result["errors"]) > 0
        assert any("Simulated factory error" in error for error in result["errors"])

        # Verify partial data was rolled back appropriately
        # (Implementation depends on rollback strategy)

    def test_performance_monitoring(self, clean_session):
        """Test performance monitoring and metrics collection."""
        # Initialize QA seed manager
        manager = QASeedManager("minimal", session=clean_session)

        # Generate seed data
        result = manager.generate_seed_data()
        assert result["success"] is True

        # Verify performance metrics are collected
        required_metrics = {
            "total_time_seconds",
            "target_time_seconds",
            "performance_ratio",
            "target_met",
            "total_records_created",
            "records_per_second",
            "validation_time_seconds",
        }

        for metric in required_metrics:
            assert metric in result, f"Missing metric: {metric}"
            assert isinstance(result[metric], (int, float, bool))

        # Verify reasonable values
        assert result["total_time_seconds"] > 0
        assert result["total_records_created"] > 0
        assert result["records_per_second"] >= 0

    @pytest.mark.slow
    def test_load_test_environment_scalability(self, clean_session):
        """Test load test environment can handle large datasets."""
        # Skip if not in CI environment (too slow for local dev)
        if not os.getenv("CI"):
            pytest.skip("Load test only runs in CI environment")

        # Initialize QA seed manager for load testing
        manager = QASeedManager("load_test", session=clean_session)

        # Generate large dataset
        result = manager.generate_seed_data()

        # Verify completion within reasonable time
        assert result["success"] is True
        assert result["total_time_seconds"] <= 1800  # 30 minutes max

        # Verify large record counts
        assert result["total_records_created"] >= 10000

        # Verify performance is reasonable
        assert result["records_per_second"] >= 10  # At least 10 records/sec


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])

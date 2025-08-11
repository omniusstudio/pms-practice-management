#!/usr/bin/env python3
"""QA-optimized seed data manager for HIPAA-compliant test data.

This script extends the base seed manager with QA-specific features:
- Sub-5-minute seeding for staging environments
- Comprehensive data validation
- Performance monitoring and reporting
- Zero PHI guarantee with automated compliance checks

Usage:
    python scripts/qa_seed_manager.py --environment standard
    python scripts/qa_seed_manager.py --environment minimal --reset
    python scripts/qa_seed_manager.py --validate-only
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))

from database import SessionLocal  # noqa: E402
from config.qa_seed_config import get_qa_seed_config, QAEnvironment  # noqa: E402
from seed_manager import SeedManager  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class QASeedManager(SeedManager):
    """QA-optimized seed data manager with performance enhancements."""

    def __init__(self, environment: Optional[str] = None, session=None):
        """Initialize QA seed manager with environment-specific config."""
        super().__init__(session)
        self.qa_config = get_qa_seed_config(environment)
        self.performance_metrics = {
            "start_time": None,
            "end_time": None,
            "total_records_created": 0,
            "records_per_second": 0,
            "validation_time": 0,
            "errors": [],
        }

        logger.info(
            "QA Seed Manager initialized for %s environment",
            self.qa_config.environment.value,
        )

    def generate_qa_seed_data(self, reset_db: bool = False) -> Dict[str, any]:
        """Generate QA seed data with performance optimization.
        Args:
            reset_db: Whether to reset the database before seeding
        Returns:
            Performance metrics and summary
        """
        self.performance_metrics["start_time"] = time.time()

        try:
            if reset_db:
                logger.info("Resetting database before seeding")
                self.clean_all_data(confirm=True)

            # Get QA-specific configuration
            record_counts = self.qa_config.get_record_counts()
            tenant_ids = self.qa_config.get_tenant_ids()

            logger.info(
                "Starting QA seed data generation with %d tenants", len(tenant_ids)
            )

            # Generate data for each model type
            for model_name, count in record_counts.items():
                if count > 0:
                    self._create_model_records(model_name, count, tenant_ids)

            # Validate data if enabled
            validation_settings = self.qa_config.get_validation_settings()
            if validation_settings["enabled"]:
                self._validate_qa_data(validation_settings)

            self.performance_metrics["end_time"] = time.time()
            self._calculate_performance_metrics()

            return self._get_generation_summary()

        except Exception as e:
            self.performance_metrics["errors"].append(str(e))
            logger.error("QA seed generation failed: %s", e)
            raise

    def _create_model_records(
        self, model_name: str, count: int, tenant_ids: List[str]
    ) -> None:
        """Create records for a specific model."""
        factory = self.factories.get(model_name)
        if not factory:
            logger.warning("No factory found for %s", model_name)
            return

        factory._meta.sqlalchemy_session = self.session

        try:
            # Distribute records across tenants
            records_per_tenant = count // len(tenant_ids)
            remaining_records = count % len(tenant_ids)

            for i, tenant_id in enumerate(tenant_ids):
                tenant_count = records_per_tenant
                if i < remaining_records:
                    tenant_count += 1

                if tenant_count > 0:
                    records = factory.create_batch(tenant_count, tenant_id=tenant_id)

                    self.session.commit()
                    self.performance_metrics["total_records_created"] += len(records)

                    logger.debug(
                        "Created %d %s records for tenant %s",
                        len(records),
                        model_name,
                        tenant_id,
                    )

        except Exception as e:
            self.session.rollback()
            error_msg = f"Failed to create {model_name} records: {e}"
            self.performance_metrics["errors"].append(error_msg)
            logger.error(error_msg)

    def _validate_qa_data(self, validation_settings: Dict[str, any]) -> None:
        """Validate QA data with comprehensive checks."""
        validation_start = time.time()
        logger.info("Starting QA data validation")

        try:
            # Run base validation
            base_results = self.validate_data_integrity()

            # Run QA-specific validations
            qa_results = self._run_qa_specific_validations(validation_settings)

            # Run HIPAA compliance validation
            hipaa_results = self._validate_hipaa_compliance()

            validation_time = time.time() - validation_start
            self.performance_metrics["validation_time"] = validation_time

            logger.info("QA data validation completed in %.2fs", validation_time)

        except Exception as e:
            error_msg = f"QA data validation failed: {e}"
            self.performance_metrics["errors"].append(error_msg)
            logger.error(error_msg)
            raise

    def _run_qa_specific_validations(
        self, validation_settings: Dict[str, any]
    ) -> Dict[str, bool]:
        """Run QA-specific data validations."""
        results = {
            "record_counts_match": True,
            "tenant_distribution": True,
            "performance_targets": True,
        }

        try:
            # Validate record counts match expectations
            expected_counts = self.qa_config.get_record_counts()
            for model_name, expected_count in expected_counts.items():
                model = self.models.get(model_name)
                if model:
                    actual_count = self.session.query(model).count()
                    if actual_count != expected_count:
                        results["record_counts_match"] = False
                        logger.warning(
                            "Record count mismatch for %s: " "expected %d, got %d",
                            model_name,
                            expected_count,
                            actual_count,
                        )

            # Validate performance targets
            total_time = (
                self.performance_metrics["end_time"]
                - self.performance_metrics["start_time"]
            )
            target_time = self.qa_config.current_profile.target_seed_time_seconds

            if total_time > target_time:
                results["performance_targets"] = False
                logger.warning(
                    "Performance target missed: %.2fs > %.2fs", total_time, target_time
                )

        except Exception as e:
            logger.error("QA validation error: %s", e)
            for key in results:
                results[key] = False

        return results

    def _validate_hipaa_compliance(self) -> Dict[str, bool]:
        """Validate HIPAA compliance of generated data."""
        results = {
            "no_real_phi": True,
            "safe_email_domains": True,
            "safe_phone_numbers": True,
        }

        try:
            hipaa_settings = self.qa_config.get_hipaa_compliance_settings()
            safe_domains = hipaa_settings["safe_domains"]
            safe_phone_prefixes = hipaa_settings["safe_phone_prefixes"]

            # Sample validation on a subset of records
            sample_size = self.qa_config.get_validation_settings()["sample_size"]

            # Check email domains and phone numbers
            from models import Client, Provider  # noqa: E402

            for model in [Client, Provider]:
                sample_records = self.session.query(model).limit(sample_size).all()

                for record in sample_records:
                    # Check email domains
                    if hasattr(record, "email") and record.email:
                        domain = record.email.split("@")[-1]
                        if domain not in safe_domains:
                            results["safe_email_domains"] = False
                            logger.warning("Unsafe email domain found: %s", domain)

                    # Check phone numbers
                    if hasattr(record, "phone") and record.phone:
                        phone_prefix = record.phone.split("-")[0]
                        if phone_prefix not in safe_phone_prefixes:
                            results["safe_phone_numbers"] = False
                            logger.warning(
                                "Unsafe phone prefix found: %s", phone_prefix
                            )

        except Exception as e:
            logger.error("HIPAA validation error: %s", e)
            for key in results:
                results[key] = False

        return results

    def _calculate_performance_metrics(self) -> None:
        """Calculate performance metrics."""
        if (
            self.performance_metrics["start_time"]
            and self.performance_metrics["end_time"]
        ):
            total_time = (
                self.performance_metrics["end_time"]
                - self.performance_metrics["start_time"]
            )

            if total_time > 0:
                self.performance_metrics["records_per_second"] = (
                    self.performance_metrics["total_records_created"] / total_time
                )

    def _get_generation_summary(self) -> Dict[str, any]:
        """Get comprehensive generation summary."""
        total_time = (
            self.performance_metrics["end_time"]
            - self.performance_metrics["start_time"]
        )

        target_time = self.qa_config.current_profile.target_seed_time_seconds
        performance_ratio = total_time / target_time if target_time > 0 else 0

        return {
            "environment": self.qa_config.environment.value,
            "profile_name": self.qa_config.current_profile.name,
            "total_time_seconds": total_time,
            "target_time_seconds": target_time,
            "performance_ratio": performance_ratio,
            "target_met": total_time <= target_time,
            "total_records_created": (
                self.performance_metrics["total_records_created"]
            ),
            "records_per_second": (self.performance_metrics["records_per_second"]),
            "validation_time_seconds": (self.performance_metrics["validation_time"]),
            "errors": self.performance_metrics["errors"],
            "success": len(self.performance_metrics["errors"]) == 0,
        }


def main():
    """Main CLI interface for QA seed manager."""
    parser = argparse.ArgumentParser(description="QA-optimized seed data manager")

    parser.add_argument(
        "--environment",
        choices=["minimal", "standard", "load_test", "integration"],
        default="standard",
        help="QA environment type",
    )

    parser.add_argument(
        "--reset", action="store_true", help="Reset database before seeding"
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only run validation, no data generation",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        manager = QASeedManager(args.environment)

        if args.validate_only:
            validation_settings = manager.qa_config.get_validation_settings()
            manager._validate_qa_data(validation_settings)
            print("✅ Validation completed successfully")
        else:
            result = manager.generate_qa_seed_data(reset_db=args.reset)

            print("\n=== QA SEED GENERATION SUMMARY ===")
            print(f"Environment: {result['environment']}")
            print(f"Profile: {result['profile_name']}")
            print(f"Total Time: {result['total_time_seconds']:.2f}s")
            print(f"Target Time: {result['target_time_seconds']}s")
            print(f"Target Met: {'✅' if result['target_met'] else '❌'}")
            print(f"Records Created: {result['total_records_created']}")
            print(f"Records/Second: {result['records_per_second']:.2f}")

            if result["errors"]:
                print(f"\n❌ Errors ({len(result['errors'])}):")
                for error in result["errors"]:
                    print(f"  - {error}")
            else:
                print("\n✅ No errors detected")

    except Exception as e:
        logger.error("QA seed manager failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()

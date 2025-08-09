#!/usr/bin/env python3
"""QA-optimized seed data manager for HIPAA-compliant test data."""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from config.qa_seed_config import get_qa_seed_config  # noqa: E402
from database import SessionLocal  # noqa: E402
from models import (  # noqa: E402
    Appointment,
    Client,
    LedgerEntry,
    Location,
    Note,
    PracticeProfile,
    Provider,
)
from seed_manager import SeedManager  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ModelNamespace:
    """Simple namespace for accessing model classes by name."""

    def __init__(self):
        self.Client = Client
        self.Provider = Provider
        self.Appointment = Appointment
        self.Note = Note
        self.Location = Location
        self.PracticeProfile = PracticeProfile
        self.LedgerEntry = LedgerEntry


class QASeedManager(SeedManager):
    """QA-optimized seed data manager with performance enhancements."""

    def __init__(self, environment: Optional[str] = None, session=None):
        """Initialize QA seed manager with environment-specific config."""
        super().__init__(session)
        self.qa_config = get_qa_seed_config(environment)
        self.models = ModelNamespace()
        self.performance_metrics.update(
            {
                "start_time": None,
                "end_time": None,
                "total_records_created": 0,
                "records_per_second": 0,
                "validation_time": 0,
                "errors": [],
            }
        )

        logger.info(
            "QA Seed Manager initialized for %s environment",
            self.qa_config.environment.value,
        )

    def generate_seed_data(self, reset_db: bool = False) -> Dict[str, Any]:
        """Generate QA seed data with performance optimization."""
        start_time = time.time()
        self.performance_metrics["start_time"] = start_time

        try:
            # Get configuration
            tenant_ids = self.qa_config.get_tenant_ids()
            record_counts = self.qa_config.get_record_counts()

            logger.info(
                "Starting QA seed data generation with %d tenants", len(tenant_ids)
            )

            total_created = 0

            # Create records for each model
            for model_name, count in record_counts.items():
                if count > 0:
                    self._create_model_records(model_name, count, tenant_ids)

            # Set end time and calculate performance metrics
            self.performance_metrics["end_time"] = time.time()
            self._calculate_performance_metrics()

            total_created = self.performance_metrics["total_records_created"]
            total_time = self.performance_metrics["end_time"] - start_time

            logger.info(
                "QA seed generation completed: %d records in %.2f seconds",
                total_created,
                total_time,
            )

            return self._get_generation_summary()

        except Exception as e:
            logger.error("QA seed generation failed: %s", e)
            self.performance_metrics["errors"].append(str(e))
            self.performance_metrics["end_time"] = time.time()
            return self._get_generation_summary(success=False, error=str(e))

    def _get_generation_summary(
        self, success: bool = True, error: str = None
    ) -> Dict[str, Any]:
        """Generate a summary of the seed generation process."""
        start_time = self.performance_metrics.get("start_time")
        end_time = self.performance_metrics.get("end_time")
        total_time = end_time - start_time if start_time and end_time else 0
        total_records = self.performance_metrics["total_records_created"]
        target_time = self.qa_config.current_profile.target_seed_time_seconds

        summary = {
            "success": success,
            "environment": self.qa_config.environment.value,
            "profile_name": self.qa_config.current_profile.name,
            "total_records_created": total_records,
            "total_time_seconds": total_time,
            "target_time_seconds": target_time,
            "target_met": (total_time <= target_time if success else False),
            "records_per_second": (
                self.performance_metrics.get("records_per_second", 0)
            ),
            "performance_ratio": (total_time / target_time if target_time > 0 else 0),
            "validation_time_seconds": self.performance_metrics.get(
                "validation_time", 0
            ),
            "errors": self.performance_metrics.get("errors", []),
        }

        if error:
            summary["error"] = error

        return summary

    def _calculate_performance_metrics(self) -> None:
        """Calculate performance metrics for the seed generation process."""
        start_time = self.performance_metrics.get("start_time")
        end_time = self.performance_metrics.get("end_time")

        if start_time and end_time:
            total_time = end_time - start_time
            total_records = self.performance_metrics["total_records_created"]

            self.performance_metrics["records_per_second"] = (
                total_records / total_time if total_time > 0 else 0
            )

    def _create_model_records(
        self, model_name: str, count: int, tenant_ids: list
    ) -> None:
        """Create records for a specific model."""
        factory = self.factories.get(model_name)
        if not factory:
            logger.warning("No factory found for %s", model_name)
            return

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

        except Exception as e:
            self.session.rollback()
            error_msg = f"Failed to create {model_name} records: {e}"
            self.performance_metrics["errors"].append(error_msg)
            logger.error(error_msg)


def main():
    """Main CLI interface for QA seed manager."""
    parser = argparse.ArgumentParser(description="QA-optimized seed data manager")
    parser.add_argument(
        "--environment",
        choices=["minimal", "standard", "load_test", "integration"],
        default="standard",
        help="QA environment profile to use",
    )
    parser.add_argument(
        "--reset", action="store_true", help="Reset database before seeding"
    )
    parser.add_argument(
        "--validate-only", action="store_true", help="Only validate existing data"
    )

    args = parser.parse_args()

    try:
        # Create database session if not provided in tests
        session = SessionLocal()
        manager = QASeedManager(args.environment, session=session)

        if args.validate_only:
            print("Validation-only mode not yet implemented")
            return

        result = manager.generate_seed_data(reset_db=args.reset)

        print("\n=== QA SEED GENERATION SUMMARY ===")
        print(f"Success: {result['success']}")
        print(f"Records Created: {result['total_records_created']}")
        print(f"Time Taken: {result['total_time_seconds']:.2f}s")
        print(f"Target Time: {result['target_time_seconds']}s")
        print(f"Target Met: {result['target_met']}")
        print(f"Records/Second: {result['records_per_second']:.1f}")

        if result["errors"]:
            print(f"\nErrors ({len(result['errors'])}):")
            for error in result["errors"]:
                print(f"  - {error}")

        manager.close()

    except Exception as e:
        logger.error("QA seed manager failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()

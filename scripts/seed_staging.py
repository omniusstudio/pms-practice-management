#!/usr/bin/env python3
"""Staging environment seed data script.

This script generates comprehensive seed data for staging environment,
with larger datasets that mirror production-like scenarios while
maintaining HIPAA compliance.

Usage:
    python scripts/seed_staging.py
    python scripts/seed_staging.py --reset
    python scripts/seed_staging.py --validate
"""

import argparse
import logging
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))

from seed_manager import SeedManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Staging environment configuration
STAGING_CONFIG = {
    'counts': {
        'practice_profiles': 5,
        'locations': 12,
        'clients': 100,
        'providers': 20,
        'appointments': 200,
        'notes': 300,
        'ledger_entries': 400,
        'auth_tokens': 30,
        'encryption_keys': 20,
        'fhir_mappings': 250
    },
    'tenant_ids': [
        'staging_tenant_001',
        'staging_tenant_002',
        'staging_tenant_003',
        'staging_tenant_004',
        'staging_tenant_005'
    ]
}


def seed_staging_data(reset: bool = False) -> None:
    """Generate seed data for staging environment.

    Args:
        reset: If True, clean existing data before seeding
    """
    logger.info("Starting staging environment seed data generation...")

    seed_manager = SeedManager()

    try:
        if reset:
            logger.info("Resetting staging database...")
            seed_manager.clean_seed_data(confirm=True)

        # Generate seed data
        logger.info("Generating staging seed data...")
        generated_data = seed_manager.generate_seed_data(
            counts=STAGING_CONFIG['counts'],
            tenant_ids=STAGING_CONFIG['tenant_ids']
        )

        # Log summary
        logger.info("\n=== STAGING SEED DATA SUMMARY ===")
        total_records = 0
        for model_type, objects in generated_data.items():
            count = len(objects)
            total_records += count
            logger.info(f"{model_type.replace('_', ' ').title()}: {count}")

        logger.info(f"\nTotal records generated: {total_records}")
        logger.info(f"Tenants: {len(STAGING_CONFIG['tenant_ids'])} tenants")

        # Validate data integrity
        logger.info("\n=== VALIDATING DATA INTEGRITY ===")
        validation_results = seed_manager.validate_data_integrity()

        all_passed = True
        for check, passed in validation_results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            logger.info(f"{check.replace('_', ' ').title()}: {status}")
            if not passed:
                all_passed = False

        if all_passed:
            logger.info("\n🎉 Staging seed data generation completed!")
            logger.info("Staging environment is ready for testing.")
        else:
            logger.warning("\n⚠️  Some validation checks failed.")
            logger.warning("Please review the data before proceeding.")

        # Log performance metrics
        logger.info("\n=== PERFORMANCE METRICS ===")
        logger.info(f"Multi-tenant setup: {len(STAGING_CONFIG['tenant_ids'])} tenants")
        logger.info(f"Total database records: {total_records}")
        logger.info("Data distribution ensures realistic load testing.")

    except Exception as e:
        logger.error(f"Failed to generate staging seed data: {e}")
        raise

    finally:
        seed_manager.close()


def validate_staging_data() -> bool:
    """Validate existing staging seed data.

    Returns:
        True if all validations pass, False otherwise
    """
    logger.info("Validating staging seed data...")

    seed_manager = SeedManager()

    try:
        validation_results = seed_manager.validate_data_integrity()

        logger.info("\n=== VALIDATION RESULTS ===")
        all_passed = True
        for check, passed in validation_results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            logger.info(f"{check.replace('_', ' ').title()}: {status}")
            if not passed:
                all_passed = False

        if all_passed:
            logger.info("\n✅ All validations passed!")
            logger.info("Staging environment data integrity confirmed.")
        else:
            logger.error("\n❌ Some validations failed!")
            logger.error("Staging environment requires data review.")

        return all_passed

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False

    finally:
        seed_manager.close()


def cleanup_staging_data() -> None:
    """Clean up staging data (for CI/CD pipeline use)."""
    logger.info("Cleaning up staging seed data...")

    seed_manager = SeedManager()

    try:
        seed_manager.clean_seed_data(confirm=True)
        logger.info("✅ Staging data cleanup completed.")

    except Exception as e:
        logger.error(f"Failed to clean staging data: {e}")
        raise

    finally:
        seed_manager.close()


def main():
    """Main CLI interface for staging seed data management."""
    parser = argparse.ArgumentParser(
        description="Staging environment seed data management"
    )

    parser.add_argument(
        '--reset', action='store_true',
        help='Clean existing data before seeding'
    )

    parser.add_argument(
        '--validate', action='store_true',
        help='Only validate existing data without generating new data'
    )

    parser.add_argument(
        '--cleanup', action='store_true',
        help='Clean up all staging data (for CI/CD use)'
    )

    parser.add_argument(
        '--quiet', action='store_true',
        help='Reduce logging output'
    )

    args = parser.parse_args()

    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    try:
        if args.cleanup:
            cleanup_staging_data()
        elif args.validate:
            success = validate_staging_data()
            sys.exit(0 if success else 1)
        else:
            seed_staging_data(reset=args.reset)

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Local development seed data script.

This script generates comprehensive seed data for local development,
including all core models with realistic anonymized data.

Usage:
    python scripts/seed_local.py
    python scripts/seed_local.py --reset
    python scripts/seed_local.py --validate
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

# Local development configuration
LOCAL_CONFIG = {
    'counts': {
        'practice_profiles': 3,
        'locations': 6,
        'clients': 25,
        'providers': 8,
        'appointments': 50,
        'notes': 75,
        'ledger_entries': 100,
        'auth_tokens': 15,
        'encryption_keys': 10,
        'fhir_mappings': 80
    },
    'tenant_ids': [
        'dev_tenant_001',
        'dev_tenant_002',
        'dev_tenant_003'
    ]
}


def seed_local_data(reset: bool = False) -> None:
    """Generate seed data for local development.

    Args:
        reset: If True, clean existing data before seeding
    """
    logger.info("Starting local development seed data generation...")

    seed_manager = SeedManager()

    try:
        if reset:
            logger.info("Resetting local database...")
            seed_manager.clean_seed_data(confirm=True)

        # Generate seed data
        logger.info("Generating local seed data...")
        generated_data = seed_manager.generate_seed_data(
            counts=LOCAL_CONFIG['counts'],
            tenant_ids=LOCAL_CONFIG['tenant_ids']
        )

        # Log summary
        logger.info("\n=== LOCAL SEED DATA SUMMARY ===")
        total_records = 0
        for model_type, objects in generated_data.items():
            count = len(objects)
            total_records += count
            logger.info(f"{model_type.replace('_', ' ').title()}: {count}")

        logger.info(f"\nTotal records generated: {total_records}")
        logger.info(f"Tenants: {', '.join(LOCAL_CONFIG['tenant_ids'])}")

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
            logger.info("\n🎉 Local seed data generation completed successfully!")
            logger.info("Your local database is ready for development.")
        else:
            logger.warning("\n⚠️  Some validation checks failed.")
            logger.warning("Please review the data before proceeding.")

    except Exception as e:
        logger.error(f"Failed to generate local seed data: {e}")
        raise

    finally:
        seed_manager.close()


def validate_local_data() -> bool:
    """Validate existing local seed data.

    Returns:
        True if all validations pass, False otherwise
    """
    logger.info("Validating local seed data...")

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
        else:
            logger.error("\n❌ Some validations failed!")

        return all_passed

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False

    finally:
        seed_manager.close()


def main():
    """Main CLI interface for local seed data management."""
    parser = argparse.ArgumentParser(
        description="Local development seed data management"
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
        '--quiet', action='store_true',
        help='Reduce logging output'
    )

    args = parser.parse_args()

    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    try:
        if args.validate:
            success = validate_local_data()
            sys.exit(0 if success else 1)
        else:
            seed_local_data(reset=args.reset)

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

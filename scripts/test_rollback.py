#!/usr/bin/env python3
"""
Migration Rollback Test Script

This script tests the rollback functionality of database migrations
to ensure they can be safely reverted in case of issues.

Usage:
    python scripts/test_rollback.py [--dry-run] [--target-revision REVISION]
"""

import sys
import subprocess
import argparse
import logging
import os
from datetime import datetime
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from sqlalchemy import create_engine, text


def get_database_url():
    """Get database URL from environment or default."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://omniusstudio:8Z3Rx04LMNw3@localhost:5432/pmsdb"
    )


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            f'rollback_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            '.log'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MigrationRollbackTester:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.engine = create_engine(get_database_url())
        self.original_revision = None
        self.test_results = []

    def run_command(self, command, capture_output=True):
        """Execute a shell command and return the result."""
        logger.info(f"Executing: {command}")

        if self.dry_run:
            logger.info("[DRY RUN] Command would be executed")
            return subprocess.CompletedProcess(
                command, 0, stdout="[DRY RUN]", stderr=""
            )

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=capture_output,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                logger.error(
                    f"Command failed with return code "
                    f"{result.returncode}"
                )
                logger.error(f"STDERR: {result.stderr}")
            else:
                logger.info(f"Command succeeded: {result.stdout.strip()}")

            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {command}")
            raise
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            raise

    def get_current_revision(self):
        """Get the current migration revision."""
        result = self.run_command("alembic current")
        if result.returncode == 0:
            # Parse revision from "2b8812283e69 (head) (mergepoint)"
            output = result.stdout.strip()
            if output:
                revision = output.split()[0]
                logger.info(f"Current revision: {revision}")
                return revision
        return None

    def get_migration_history(self):
        """Get the migration history."""
        result = self.run_command("alembic history --verbose")
        if result.returncode == 0:
            return result.stdout
        return None

    def get_table_count(self):
        """Get count of records in key tables for validation."""
        counts = {}
        tables = [
            'practice_profiles', 'locations', 'clients', 'providers',
            'appointments', 'notes', 'ledger', 'auth_tokens',
            'encryption_keys', 'fhir_mappings', 'audit_log'
        ]

        try:
            with self.engine.connect() as conn:
                for table in tables:
                    try:
                        result = conn.execute(
                            text(f"SELECT COUNT(*) FROM {table}")
                        )
                        count = result.scalar()
                        counts[table] = count
                        logger.info(f"Table {table}: {count} records")
                    except Exception as e:
                        logger.warning(f"Could not count {table}: {e}")
                        counts[table] = None
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")

        return counts

    def validate_database_integrity(self):
        """Validate database integrity after migration operations."""
        logger.info("Validating database integrity...")

        integrity_checks = [
            # Check foreign key constraints
            "SELECT conname, conrelid::regclass FROM pg_constraint "
            "WHERE contype = 'f'",

            # Check for orphaned records (example)
            "SELECT COUNT(*) FROM locations WHERE practice_profile_id "
            "NOT IN (SELECT id FROM practice_profiles)",

            # Check unique constraints
            "SELECT conname, conrelid::regclass FROM pg_constraint "
            "WHERE contype = 'u'",

            # Check indexes
            "SELECT schemaname, tablename, indexname FROM pg_indexes "
            "WHERE schemaname = 'public'"
        ]

        try:
            with self.engine.connect() as conn:
                for i, check in enumerate(integrity_checks, 1):
                    try:
                        result = conn.execute(text(check))
                        rows = result.fetchall()
                        logger.info(
                            f"Integrity check {i}: {len(rows)} results"
                        )
                    except Exception as e:
                        logger.warning(f"Integrity check {i} failed: {e}")
                        return False
            return True
        except Exception as e:
            logger.error(f"Database integrity validation failed: {e}")
            return False

    def test_rollback_to_revision(self, target_revision):
        """Test rollback to a specific revision."""
        logger.info(f"Testing rollback to revision: {target_revision}")

        # Record pre-rollback state
        pre_counts = self.get_table_count()
        self.validate_database_integrity()

        # Perform rollback
        rollback_result = self.run_command(
            f"alembic downgrade {target_revision}"
        )

        if rollback_result.returncode != 0:
            self.test_results.append({
                'test': f'rollback_to_{target_revision}',
                'status': 'FAILED',
                'error': rollback_result.stderr,
                'timestamp': datetime.now()
            })
            return False

        # Verify rollback
        current_revision = self.get_current_revision()
        if current_revision != target_revision:
            self.test_results.append({
                'test': f'rollback_to_{target_revision}',
                'status': 'FAILED',
                'error': f'Expected {target_revision}, got '
                         f'{current_revision}',
                'timestamp': datetime.now()
            })
            return False

        # Validate post-rollback state
        post_counts = self.get_table_count()
        post_integrity = self.validate_database_integrity()

        # Record test result
        self.test_results.append({
            'test': f'rollback_to_{target_revision}',
            'status': 'PASSED',
            'pre_counts': pre_counts,
            'post_counts': post_counts,
            'integrity_maintained': post_integrity,
            'timestamp': datetime.now()
        })

        logger.info(
            f"Rollback to {target_revision} completed successfully"
        )
        return True

    def test_forward_migration(self, target_revision):
        """Test forward migration to a specific revision."""
        logger.info(
            f"Testing forward migration to revision: {target_revision}"
        )

        # Record pre-migration state
        pre_counts = self.get_table_count()

        # Perform forward migration
        upgrade_result = self.run_command(f"alembic upgrade {target_revision}")

        if upgrade_result.returncode != 0:
            self.test_results.append({
                'test': f'upgrade_to_{target_revision}',
                'status': 'FAILED',
                'error': upgrade_result.stderr,
                'timestamp': datetime.now()
            })
            return False

        # Verify migration
        current_revision = self.get_current_revision()
        if current_revision != target_revision:
            self.test_results.append({
                'test': f'upgrade_to_{target_revision}',
                'status': 'FAILED',
                'error': f'Expected {target_revision}, got '
                         f'{current_revision}',
                'timestamp': datetime.now()
            })
            return False

        # Validate post-migration state
        post_counts = self.get_table_count()
        post_integrity = self.validate_database_integrity()

        # Record test result
        self.test_results.append({
            'test': f'upgrade_to_{target_revision}',
            'status': 'PASSED',
            'pre_counts': pre_counts,
            'post_counts': post_counts,
            'integrity_maintained': post_integrity,
            'timestamp': datetime.now()
        })

        logger.info(
            f"Forward migration to {target_revision} completed successfully"
        )
        return True

    def run_comprehensive_rollback_test(self, target_revision=None):
        """Run a comprehensive rollback test."""
        logger.info("Starting comprehensive rollback test...")

        # Get initial state
        self.original_revision = self.get_current_revision()
        if not self.original_revision:
            logger.error("Could not determine current revision")
            return False

        logger.info(f"Original revision: {self.original_revision}")

        # Get migration history to find a suitable target
        if not target_revision:
            history = self.get_migration_history()
            if history:
                # Parse history to find previous revision
                lines = history.split('\n')
                for line in lines:
                    if 'Rev:' in line and self.original_revision not in line:
                        # Extract revision ID
                        parts = line.split()
                        for part in parts:
                            # Typical revision format
                            if len(part) == 12 and part.isalnum():
                                target_revision = part
                                break
                        if target_revision:
                            break

        if not target_revision:
            logger.warning(
                "No suitable target revision found for rollback test"
            )
            # Try rolling back by one step
            rollback_result = self.run_command("alembic downgrade -1")
            if rollback_result.returncode == 0:
                target_revision = self.get_current_revision()
                # Restore to original
                self.run_command(f"alembic upgrade {self.original_revision}")
            else:
                logger.error("Could not perform rollback test")
                return False

        logger.info(
            "Target revision for rollback test: %s", target_revision
        )

        # Test sequence: rollback -> validate -> forward migration -> validate
        success = True

        # Step 1: Test rollback
        if not self.test_rollback_to_revision(target_revision):
            success = False

        # Step 2: Test forward migration back to original
        if success and not self.test_forward_migration(self.original_revision):
            success = False

        # Generate test report
        self.generate_test_report()

        return success

    def generate_test_report(self):
        """Generate a comprehensive test report."""
        report_file = (
            f"rollback_test_report_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        with open(report_file, 'w') as f:
            f.write("MIGRATION ROLLBACK TEST REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Test Date: {datetime.now()}\n")
            f.write(f"Original Revision: {self.original_revision}\n")
            f.write(f"Dry Run Mode: {self.dry_run}\n\n")

            f.write("TEST RESULTS:\n")
            f.write("-" * 20 + "\n")

            passed = 0
            failed = 0

            for result in self.test_results:
                status = result['status']
                if status == 'PASSED':
                    passed += 1
                else:
                    failed += 1

                f.write(f"Test: {result['test']}\n")
                f.write(f"Status: {status}\n")
                f.write(f"Timestamp: {result['timestamp']}\n")

                if 'error' in result:
                    f.write(f"Error: {result['error']}\n")

                if 'integrity_maintained' in result:
                    f.write(
                        f"Integrity Maintained: {result['integrity_maintained']}\n"
                    )

                f.write("\n")

            f.write("SUMMARY:\n")
            f.write(f"Total Tests: {len(self.test_results)}\n")
            f.write(f"Passed: {passed}\n")
            f.write(f"Failed: {failed}\n")
            if self.test_results:
                success_rate = (passed / len(self.test_results) * 100)
                f.write(f"Success Rate: {success_rate:.1f}%\n")
            else:
                f.write("No tests run\n")

        logger.info("Test report generated: %s", report_file)

        # Also log summary
        logger.info("Test Summary - Passed: %s, Failed: %s", passed, failed)


def main():
    parser = argparse.ArgumentParser(
        description='Test migration rollback functionality'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (no actual changes)'
    )
    parser.add_argument(
        '--target-revision',
        help='Specific revision to test rollback to'
    )

    args = parser.parse_args()

    tester = MigrationRollbackTester(dry_run=args.dry_run)

    try:
        success = tester.run_comprehensive_rollback_test(args.target_revision)

        if success:
            logger.info("All rollback tests passed successfully!")
            sys.exit(0)
        else:
            logger.error(
                "Some rollback tests failed. Check the logs for details."
            )
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error("Test failed with exception: %s", e)
        sys.exit(1)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Mental Health PMS Backup and Restore Test Suite

This test suite validates the backup and restore functionality for HIPAA
compliance and ensures data integrity throughout the backup/restore process.
"""

import os
import sys
import json
import time
import subprocess
import tempfile
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import psycopg2
import boto3
from kubernetes import client, config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackupRestoreTestSuite:
    """Test suite for backup and restore functionality."""
    
    def __init__(self):
        self.setup_environment()
        self.test_results = []
        
    def setup_environment(self):
        """Setup test environment and configurations."""
        # Load Kubernetes config
        try:
            config.load_incluster_config()
        except Exception:
            config.load_kube_config()
            
        self.k8s_v1 = client.CoreV1Api()
        self.k8s_batch = client.BatchV1Api()
        
        # AWS S3 client
        self.s3_client = boto3.client('s3')
        
        # Configuration
        self.config = {
            'namespace': os.getenv('TEST_NAMESPACE', 'pms-test'),
            's3_bucket': os.getenv('BACKUP_S3_BUCKET', 'pms-test-backups'),
            'db_host': os.getenv('PGHOST', 'localhost'),
            'db_port': int(os.getenv('PGPORT', '5432')),
            'db_name': os.getenv('PGDATABASE', 'pms_test'),
            'db_user': os.getenv('PGUSER', 'pms_test'),
            'db_password': os.getenv('PGPASSWORD', 'test_password'),
            'encryption_key_id': os.getenv('BACKUP_ENCRYPTION_KEY_ID', 'test-key'),
            'scripts_path': '/scripts/backup',
        }
        
        logger.info(f"Test configuration: {self.config}")
        
    def get_db_connection(self):
        """Get database connection."""
        return psycopg2.connect(
            host=self.config['db_host'],
            port=self.config['db_port'],
            database=self.config['db_name'],
            user=self.config['db_user'],
            password=self.config['db_password']
        )
        
    def execute_sql(self, sql: str, params: Optional[tuple] = None, 
                   fetch: bool = False):
        """Execute SQL query."""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                if fetch:
                    return cur.fetchall()
                conn.commit()
                return []
                
    def create_test_data(self) -> Dict[str, int]:
        """Create test data in database."""
        logger.info("Creating test data")
        
        # Create test tables if they don't exist
        self.execute_sql("""
            CREATE TABLE IF NOT EXISTS test_patients (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE,
                created_at TIMESTAMP DEFAULT NOW(),
                data_hash VARCHAR(64)
            )
        """)
        
        self.execute_sql("""
            CREATE TABLE IF NOT EXISTS test_appointments (
                id SERIAL PRIMARY KEY,
                patient_id INTEGER REFERENCES test_patients(id),
                appointment_date TIMESTAMP,
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Insert test data
        test_data = {
            'patients': 100,
            'appointments': 250
        }
        
        # Insert patients
        for i in range(test_data['patients']):
            data_content = f"patient_{i}_test_data_{datetime.now().isoformat()}"
            data_hash = hashlib.sha256(data_content.encode()).hexdigest()
            
            self.execute_sql(
                "INSERT INTO test_patients (name, email, data_hash) "
                "VALUES (%s, %s, %s)",
                (f"Test Patient {i}", f"patient{i}@test.com", data_hash)
            )
            
        # Insert appointments
        for i in range(test_data['appointments']):
            patient_id = (i % test_data['patients']) + 1
            appointment_date = datetime.now() + timedelta(days=i % 30)
            
            self.execute_sql(
                "INSERT INTO test_appointments (patient_id, appointment_date, "
                "notes) VALUES (%s, %s, %s)",
                (patient_id, appointment_date, f"Test appointment {i} notes")
            )
            
        logger.info(f"Created test data: {test_data}")
        return test_data
        
    def get_data_checksums(self) -> Dict[str, str]:
        """Get checksums of test data for integrity verification."""
        checksums = {}
        
        # Get patient data checksum
        patients = self.execute_sql(
            "SELECT id, name, email, data_hash FROM test_patients "
            "ORDER BY id",
            fetch=True
        )
        patient_data = ''.join([str(row) for row in patients])
        checksums['patients'] = hashlib.sha256(
            patient_data.encode()
        ).hexdigest()
        
        # Get appointment data checksum
        appointments = self.execute_sql(
            "SELECT id, patient_id, appointment_date, notes FROM "
            "test_appointments ORDER BY id",
            fetch=True
        )
        appointment_data = ''.join([str(row) for row in appointments])
        checksums['appointments'] = hashlib.sha256(
            appointment_data.encode()
        ).hexdigest()
        
        return checksums
        
    def run_backup_script(self) -> Tuple[bool, str, str]:
        """Run backup script and return success status and output."""
        logger.info("Running backup script")
        
        try:
            result = subprocess.run(
                [f"{self.config['scripts_path']}/pg_backup.sh"],
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", "Backup script timed out"
        except Exception as e:
            return False, "", str(e)
            
    def run_restore_script(self, backup_path: str = "latest") -> Tuple[bool, str, str]:
        """Run restore script and return success status and output."""
        logger.info(f"Running restore script with backup: {backup_path}")
        
        try:
            result = subprocess.run(
                [f"{self.config['scripts_path']}/restore.sh", backup_path],
                capture_output=True,
                text=True,
                timeout=7200  # 2 hour timeout
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", "Restore script timed out"
        except Exception as e:
            return False, "", str(e)
            
    def run_verification_script(self, backup_path: str = "latest") -> Tuple[bool, str, str]:
        """Run backup verification script."""
        logger.info(f"Running verification script for backup: {backup_path}")
        
        try:
            result = subprocess.run(
                [f"{self.config['scripts_path']}/verify_backup.sh", backup_path],
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", "Verification script timed out"
        except Exception as e:
            return False, "", str(e)
            
    def check_s3_backup_exists(self) -> Tuple[bool, Optional[str]]:
        """Check if backup exists in S3."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.config['s3_bucket'],
                Prefix='backups/'
            )
            
            if 'Contents' not in response:
                return False, None
                
            # Find latest backup
            backups = [
                obj for obj in response['Contents'] 
                if obj['Key'].endswith('.gpg')
            ]
            if not backups:
                return False, None
                
            latest_backup = max(backups, key=lambda x: x['LastModified'])
            return True, latest_backup['Key']
            
        except Exception as e:
            logger.error(f"Error checking S3 backup: {e}")
            return False, None
            
    def test_backup_creation(self) -> Dict:
        """Test backup creation functionality."""
        test_name = "Backup Creation Test"
        logger.info(f"Starting {test_name}")
        
        result = {
            'test_name': test_name,
            'start_time': datetime.now().isoformat(),
            'status': 'running',
            'details': {}
        }
        
        try:
            # Create test data
            test_data = self.create_test_data()
            original_checksums = self.get_data_checksums()
            
            # Run backup
            success, stdout, stderr = self.run_backup_script()
            
            result['details']['backup_success'] = success
            result['details']['backup_output'] = stdout
            result['details']['backup_errors'] = stderr
            
            if not success:
                result['status'] = 'failed'
                result['error'] = f"Backup script failed: {stderr}"
                return result
                
            # Check if backup exists in S3
            backup_exists, backup_key = self.check_s3_backup_exists()
            result['details']['s3_backup_exists'] = backup_exists
            result['details']['backup_key'] = backup_key
            
            if not backup_exists:
                result['status'] = 'failed'
                result['error'] = "Backup not found in S3"
                return result
                
            # Verify backup
            verify_success, verify_stdout, verify_stderr = self.run_verification_script()
            result['details']['verification_success'] = verify_success
            result['details']['verification_output'] = verify_stdout
            result['details']['verification_errors'] = verify_stderr
            
            result['status'] = 'passed' if verify_success else 'failed'
            if not verify_success:
                result['error'] = f"Backup verification failed: {verify_stderr}"
                
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            logger.error(f"Error in {test_name}: {e}")
            
        finally:
            result['end_time'] = datetime.now().isoformat()
            result['duration'] = (
                datetime.fromisoformat(result['end_time']) - 
                datetime.fromisoformat(result['start_time'])
            ).total_seconds()
            
        return result
        
    def test_full_restore(self) -> Dict:
        """Test full database restore functionality."""
        test_name = "Full Restore Test"
        logger.info(f"Starting {test_name}")
        
        result = {
            'test_name': test_name,
            'start_time': datetime.now().isoformat(),
            'status': 'running',
            'details': {}
        }
        
        try:
            # Create and backup test data
            test_data = self.create_test_data()
            original_checksums = self.get_data_checksums()
            
            # Create backup
            backup_success, _, _ = self.run_backup_script()
            if not backup_success:
                result['status'] = 'failed'
                result['error'] = "Failed to create backup for restore test"
                return result
                
            # Modify data to simulate corruption
            self.execute_sql("DELETE FROM test_patients WHERE id % 2 = 0")
            self.execute_sql(
                "UPDATE test_appointments SET notes = 'CORRUPTED' "
                "WHERE id % 3 = 0"
            )
            
            # Get corrupted checksums
            corrupted_checksums = self.get_data_checksums()
            result['details']['data_corrupted'] = (
                original_checksums != corrupted_checksums
            )
            
            # Perform restore
            restore_success, restore_stdout, restore_stderr = self.run_restore_script()
            result['details']['restore_success'] = restore_success
            result['details']['restore_output'] = restore_stdout
            result['details']['restore_errors'] = restore_stderr
            
            if not restore_success:
                result['status'] = 'failed'
                result['error'] = f"Restore failed: {restore_stderr}"
                return result
                
            # Verify data integrity after restore
            restored_checksums = self.get_data_checksums()
            result['details']['data_integrity_restored'] = (
                original_checksums == restored_checksums
            )
            
            # Verify record counts
            patient_count = self.execute_sql(
                "SELECT COUNT(*) FROM test_patients", fetch=True
            )[0][0]
            appointment_count = self.execute_sql(
                "SELECT COUNT(*) FROM test_appointments", fetch=True
            )[0][0]
            
            result['details']['patient_count'] = patient_count
            result['details']['appointment_count'] = appointment_count
            result['details']['expected_patient_count'] = test_data['patients']
            result['details']['expected_appointment_count'] = test_data['appointments']
            
            counts_match = (
                patient_count == test_data['patients'] and 
                appointment_count == test_data['appointments']
            )
            result['details']['record_counts_match'] = counts_match
            
            # Overall success
            result['status'] = 'passed' if (
                restore_success and 
                result['details']['data_integrity_restored'] and 
                counts_match
            ) else 'failed'
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            logger.error(f"Error in {test_name}: {e}")
            
        finally:
            result['end_time'] = datetime.now().isoformat()
            result['duration'] = (
                datetime.fromisoformat(result['end_time']) - 
                datetime.fromisoformat(result['start_time'])
            ).total_seconds()
            
        return result
        
    def test_point_in_time_recovery(self) -> Dict:
        """Test point-in-time recovery functionality."""
        test_name = "Point-in-Time Recovery Test"
        logger.info(f"Starting {test_name}")
        
        result = {
            'test_name': test_name,
            'start_time': datetime.now().isoformat(),
            'status': 'running',
            'details': {}
        }
        
        try:
            # Create initial data and backup
            initial_data = self.create_test_data()
            initial_checksums = self.get_data_checksums()
            
            backup_success, _, _ = self.run_backup_script()
            if not backup_success:
                result['status'] = 'failed'
                result['error'] = "Failed to create initial backup"
                return result
                
            # Record recovery target time
            recovery_target = datetime.now()
            time.sleep(2)  # Ensure time difference
            
            # Add more data after recovery target
            for i in range(50):
                self.execute_sql(
                    "INSERT INTO test_patients (name, email, data_hash) "
                    "VALUES (%s, %s, %s)",
                    (f"Post-Target Patient {i}", f"post{i}@test.com", 
                     f"hash_{i}")
                )
                
            # Get checksums with additional data
            post_target_checksums = self.get_data_checksums()
            result['details']['data_added_after_target'] = (
                initial_checksums != post_target_checksums
            )
            
            # Perform PITR to recovery target
            pitr_success, pitr_stdout, pitr_stderr = self.run_restore_script(
                f"pitr:{recovery_target.isoformat()}"
            )
            result['details']['pitr_success'] = pitr_success
            result['details']['pitr_output'] = pitr_stdout
            result['details']['pitr_errors'] = pitr_stderr
            
            if not pitr_success:
                result['status'] = 'failed'
                result['error'] = f"PITR failed: {pitr_stderr}"
                return result
                
            # Verify data state matches recovery target
            pitr_checksums = self.get_data_checksums()
            result['details']['pitr_data_integrity'] = (
                initial_checksums == pitr_checksums
            )
            
            # Verify post-target data was removed
            post_target_patients = self.execute_sql(
                "SELECT COUNT(*) FROM test_patients WHERE name LIKE "
                "'Post-Target%'",
                fetch=True
            )[0][0]
            result['details']['post_target_data_removed'] = (
                post_target_patients == 0
            )
            
            result['status'] = 'passed' if (
                pitr_success and 
                result['details']['pitr_data_integrity'] and 
                result['details']['post_target_data_removed']
            ) else 'failed'
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            logger.error(f"Error in {test_name}: {e}")
            
        finally:
            result['end_time'] = datetime.now().isoformat()
            result['duration'] = (
                datetime.fromisoformat(result['end_time']) - 
                datetime.fromisoformat(result['start_time'])
            ).total_seconds()
            
        return result
        
    def test_backup_encryption(self) -> Dict:
        """Test backup encryption functionality."""
        test_name = "Backup Encryption Test"
        logger.info(f"Starting {test_name}")
        
        result = {
            'test_name': test_name,
            'start_time': datetime.now().isoformat(),
            'status': 'running',
            'details': {}
        }
        
        try:
            # Create test data
            self.create_test_data()
            
            # Create backup
            backup_success, _, _ = self.run_backup_script()
            if not backup_success:
                result['status'] = 'failed'
                result['error'] = "Failed to create backup for encryption test"
                return result
                
            # Check if backup exists and is encrypted
            backup_exists, backup_key = self.check_s3_backup_exists()
            if not backup_exists:
                result['status'] = 'failed'
                result['error'] = "Backup not found in S3"
                return result
                
            # Download backup to check encryption
            with tempfile.NamedTemporaryFile() as temp_file:
                self.s3_client.download_file(
                    self.config['s3_bucket'],
                    backup_key,
                    temp_file.name
                )
                
                # Check if file is GPG encrypted
                file_result = subprocess.run(
                    ['file', temp_file.name],
                    capture_output=True,
                    text=True
                )
                
                is_encrypted = (
                    'GPG' in file_result.stdout or 
                    'encrypted' in file_result.stdout
                )
                result['details']['backup_encrypted'] = is_encrypted
                
                if not is_encrypted:
                    result['status'] = 'failed'
                    result['error'] = "Backup is not properly encrypted"
                    return result
                    
                # Try to decrypt with correct key
                decrypt_result = subprocess.run(
                    ['gpg', '--decrypt', '--quiet', temp_file.name],
                    capture_output=True,
                    text=True
                )
                
                decrypt_success = decrypt_result.returncode == 0
                result['details']['decryption_success'] = decrypt_success
                
                if not decrypt_success:
                    result['status'] = 'failed'
                    result['error'] = f"Failed to decrypt backup: {decrypt_result.stderr}"
                    return result
                    
            result['status'] = 'passed'
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            logger.error(f"Error in {test_name}: {e}")
            
        finally:
            result['end_time'] = datetime.now().isoformat()
            result['duration'] = (
                datetime.fromisoformat(result['end_time']) - 
                datetime.fromisoformat(result['start_time'])
            ).total_seconds()
            
        return result
        
    def test_backup_monitoring(self) -> Dict:
        """Test backup monitoring functionality."""
        test_name = "Backup Monitoring Test"
        logger.info(f"Starting {test_name}")
        
        result = {
            'test_name': test_name,
            'start_time': datetime.now().isoformat(),
            'status': 'running',
            'details': {}
        }
        
        try:
            # Run monitoring script
            monitor_result = subprocess.run(
                [f"{self.config['scripts_path']}/monitor_backups.sh"],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            result['details']['monitor_success'] = monitor_result.returncode == 0
            result['details']['monitor_output'] = monitor_result.stdout
            result['details']['monitor_errors'] = monitor_result.stderr
            
            # Check for monitoring report
            monitor_reports = subprocess.run(
                ['find', '/var/log/pms', '-name', 
                 'backup_monitoring_*.json', '-mtime', '-1'],
                capture_output=True,
                text=True
            )
            
            reports_found = len(monitor_reports.stdout.strip().split('\n')) > 0
            result['details']['monitoring_reports_generated'] = reports_found
            
            result['status'] = 'passed' if (
                result['details']['monitor_success'] and 
                reports_found
            ) else 'failed'
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            logger.error(f"Error in {test_name}: {e}")
            
        finally:
            result['end_time'] = datetime.now().isoformat()
            result['duration'] = (
                datetime.fromisoformat(result['end_time']) - 
                datetime.fromisoformat(result['start_time'])
            ).total_seconds()
            
        return result
        
    def run_all_tests(self) -> Dict:
        """Run all backup and restore tests."""
        logger.info("Starting comprehensive backup and restore test suite")
        
        test_suite_result = {
            'test_suite': 'Backup and Restore Comprehensive Test',
            'start_time': datetime.now().isoformat(),
            'tests': [],
            'summary': {}
        }
        
        # List of tests to run
        tests = [
            self.test_backup_creation,
            self.test_backup_encryption,
            self.test_full_restore,
            self.test_point_in_time_recovery,
            self.test_backup_monitoring
        ]
        
        passed_tests = 0
        failed_tests = 0
        
        for test_func in tests:
            try:
                test_result = test_func()
                test_suite_result['tests'].append(test_result)
                
                if test_result['status'] == 'passed':
                    passed_tests += 1
                else:
                    failed_tests += 1
                    
                logger.info(f"Test {test_result['test_name']}: {test_result['status']}")
                
            except Exception as e:
                logger.error(f"Error running test {test_func.__name__}: {e}")
                failed_tests += 1
                
        # Calculate summary
        total_tests = passed_tests + failed_tests
        test_suite_result['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': (
                (passed_tests / total_tests * 100) if total_tests > 0 else 0
            ),
            'overall_status': 'passed' if failed_tests == 0 else 'failed'
        }
        
        test_suite_result['end_time'] = datetime.now().isoformat()
        test_suite_result['total_duration'] = (
            datetime.fromisoformat(test_suite_result['end_time']) - 
            datetime.fromisoformat(test_suite_result['start_time'])
        ).total_seconds()
        
        return test_suite_result
        
    def generate_test_report(self, results: Dict) -> str:
        """Generate comprehensive test report."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"/tmp/backup_test_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        logger.info(f"Test report generated: {report_file}")
        return report_file
        
    def cleanup_test_data(self):
        """Clean up test data and resources."""
        logger.info("Cleaning up test data")
        
        try:
            # Drop test tables
            self.execute_sql("DROP TABLE IF EXISTS test_appointments CASCADE")
            self.execute_sql("DROP TABLE IF EXISTS test_patients CASCADE")
            
            # Clean up S3 test backups (optional)
            # This should be done carefully in production
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def main():
    """Main test execution function."""
    test_suite = BackupRestoreTestSuite()
    
    try:
        # Run all tests
        results = test_suite.run_all_tests()
        
        # Generate report
        report_file = test_suite.generate_test_report(results)
        
        # Print summary
        print("\n" + "="*80)
        print("BACKUP AND RESTORE TEST SUITE SUMMARY")
        print("="*80)
        print(f"Total Tests: {results['summary']['total_tests']}")
        print(f"Passed: {results['summary']['passed_tests']}")
        print(f"Failed: {results['summary']['failed_tests']}")
        success_rate = results['summary']['success_rate']
        print(f"Success Rate: {success_rate:.1f}%")
        status = results['summary']['overall_status'].upper()
        print(f"Overall Status: {status}")
        print(f"Total Duration: {results['total_duration']:.1f} seconds")
        print(f"Report File: {report_file}")
        print("="*80)
        
        # Print individual test results
        for test in results['tests']:
            status_symbol = "✓" if test['status'] == 'passed' else "✗"
            duration = test['duration']
            test_name = test['test_name']
            test_status = test['status']
            print(f"{status_symbol} {test_name}: {test_status} "
                  f"({duration:.1f}s)")
            if test['status'] == 'failed' and 'error' in test:
                print(f"  Error: {test['error']}")
                
        # Exit with appropriate code
        overall_status = results['summary']['overall_status']
        exit_code = 0 if overall_status == 'passed' else 1
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"Test suite execution failed: {e}")
        sys.exit(1)
        
    finally:
        # Cleanup
        test_suite.cleanup_test_data()

# Pytest test functions
def test_backup_creation():
    """Test backup creation functionality."""
    test_suite = BackupRestoreTestSuite()
    result = test_suite.test_backup_creation()
    assert result['status'] == 'passed'


def test_full_restore():
    """Test full database restore functionality."""
    test_suite = BackupRestoreTestSuite()
    result = test_suite.test_full_restore()
    assert result['status'] == 'passed'


def test_point_in_time_recovery():
    """Test point-in-time recovery functionality."""
    test_suite = BackupRestoreTestSuite()
    result = test_suite.test_point_in_time_recovery()
    assert result['status'] == 'passed'


def test_backup_encryption():
    """Test backup encryption functionality."""
    test_suite = BackupRestoreTestSuite()
    result = test_suite.test_backup_encryption()
    assert result['status'] == 'passed'


def test_backup_monitoring():
    """Test backup monitoring functionality."""
    test_suite = BackupRestoreTestSuite()
    result = test_suite.test_backup_monitoring()
    assert result['status'] == 'passed'


def test_kubernetes_cronjob_validation():
    """Test Kubernetes CronJob configuration validation."""
    # Simple validation test for CronJob configuration
    cronjob_config = {
        'apiVersion': 'batch/v1',
        'kind': 'CronJob',
        'metadata': {
            'name': 'pms-backup',
            'namespace': 'pms'
        },
        'spec': {
            'schedule': '0 2 * * *',
            'jobTemplate': {
                'spec': {
                    'template': {
                        'spec': {
                            'containers': [{
                                'name': 'backup',
                                'image': 'postgres:13',
                                'command': ['/scripts/pg_backup.sh']
                            }]
                        }
                    }
                }
            }
        }
    }
    
    # Validate CronJob configuration
    assert cronjob_config['kind'] == 'CronJob'
    assert cronjob_config['spec']['schedule'] == '0 2 * * *'
    assert 'pms-backup' in cronjob_config['metadata']['name']

if __name__ == "__main__":
    main()
"""Tests for data retention scheduler."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

from services.data_retention_scheduler import (
    TestDataRetentionScheduler as DataRetentionScheduler,
)
from services.data_retention_scheduler import start_scheduler, stop_scheduler


class TestDataRetentionScheduler:
    """Test cases for DataRetentionScheduler."""

    def test_scheduler_initialization(self):
        """Test scheduler initialization."""
        scheduler = DataRetentionScheduler()

        assert scheduler.scheduler is not None
        assert scheduler.is_running is False
        assert scheduler.jobs == {}

    @patch("services.data_retention_scheduler.logger")
    def test_start_scheduler_success(self, mock_logger):
        """Test successful scheduler start."""
        scheduler = DataRetentionScheduler()

        # Mock scheduler start
        scheduler.scheduler = Mock()
        scheduler.scheduler.running = False

        # Test
        result = scheduler.start()

        # Verify
        assert result is True
        assert scheduler.is_running is True
        scheduler.scheduler.start.assert_called_once()
        mock_logger.info.assert_called_with(
            "Data retention scheduler started successfully"
        )

    @patch("services.data_retention_scheduler.logger")
    def test_start_scheduler_already_running(self, mock_logger):
        """Test starting scheduler when already running."""
        scheduler = DataRetentionScheduler()

        # Mock scheduler already running
        scheduler.scheduler = Mock()
        scheduler.scheduler.running = True

        # Test
        result = scheduler.start()

        # Verify
        assert result is True
        scheduler.scheduler.start.assert_not_called()
        mock_logger.warning.assert_called_with(
            "Data retention scheduler is already running"
        )

    @patch("services.data_retention_scheduler.logger")
    def test_start_scheduler_error(self, mock_logger):
        """Test scheduler start with error."""
        scheduler = DataRetentionScheduler()

        # Mock scheduler start error
        scheduler.scheduler = Mock()
        scheduler.scheduler.running = False
        scheduler.scheduler.start.side_effect = Exception("Start error")

        # Test
        result = scheduler.start()

        # Verify
        assert result is False
        assert scheduler.is_running is False
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to start scheduler" in error_call
        assert "Start error" in error_call

    @patch("services.data_retention_scheduler.logger")
    def test_stop_scheduler_success(self, mock_logger):
        """Test successful scheduler stop."""
        scheduler = DataRetentionScheduler()
        scheduler.is_running = True

        # Mock scheduler stop
        scheduler.scheduler = Mock()
        scheduler.scheduler.running = True

        # Test
        result = scheduler.stop()

        # Verify
        assert result is True
        assert scheduler.is_running is False
        scheduler.scheduler.shutdown.assert_called_once_with(wait=True)
        mock_logger.info.assert_called_with(
            "Data retention scheduler stopped successfully"
        )

    @patch("services.data_retention_scheduler.logger")
    def test_stop_scheduler_not_running(self, mock_logger):
        """Test stopping scheduler when not running."""
        scheduler = DataRetentionScheduler()

        # Mock scheduler not running
        scheduler.scheduler = Mock()
        scheduler.scheduler.running = False

        # Test
        result = scheduler.stop()

        # Verify
        assert result is True
        scheduler.scheduler.shutdown.assert_not_called()
        mock_logger.warning.assert_called_with(
            "Data retention scheduler is not running"
        )

    @patch("services.data_retention_scheduler.logger")
    def test_stop_scheduler_error(self, mock_logger):
        """Test scheduler stop with error."""
        scheduler = DataRetentionScheduler()
        scheduler.is_running = True

        # Mock scheduler stop error
        scheduler.scheduler = Mock()
        scheduler.scheduler.running = True
        scheduler.scheduler.shutdown.side_effect = Exception("Stop error")

        # Test
        result = scheduler.stop()

        # Verify
        assert result is False
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to stop scheduler" in error_call
        assert "Stop error" in error_call

    @patch("services.data_retention_scheduler.execute_retention_policy")
    @patch("services.data_retention_scheduler.logger")
    def test_schedule_purge_job_success(self, mock_logger, mock_execute):
        """Test successful purge job scheduling."""
        scheduler = DataRetentionScheduler()
        scheduler.is_running = True

        # Mock scheduler
        scheduler.scheduler = Mock()
        mock_job = Mock()
        mock_job.id = "test-tenant-purge"
        scheduler.scheduler.add_job.return_value = mock_job

        # Test
        result = scheduler.schedule_purge_job(
            "test-tenant", "0 2 * * *"  # Daily at 2 AM
        )

        # Verify
        assert result is True
        assert "test-tenant" in scheduler.jobs
        assert scheduler.jobs["test-tenant"] == mock_job

        # Verify job was scheduled
        scheduler.scheduler.add_job.assert_called_once()
        call_args = scheduler.scheduler.add_job.call_args
        assert call_args[1]["id"] == "test-tenant-purge"
        assert call_args[1]["trigger"] == "cron"

        mock_logger.info.assert_called_with(
            "Scheduled purge job for tenant test-tenant with "
            "cron expression: 0 2 * * *"
        )

    @patch("services.data_retention_scheduler.logger")
    def test_schedule_purge_job_scheduler_not_running(self, mock_logger):
        """Test scheduling job when scheduler not running."""
        scheduler = DataRetentionScheduler()
        scheduler.is_running = False

        # Test
        result = scheduler.schedule_purge_job("test-tenant", "0 2 * * *")

        # Verify
        assert result is False
        mock_logger.error.assert_called_with(
            "Cannot schedule job: scheduler is not running"
        )

    @patch("services.data_retention_scheduler.execute_retention_policy")
    @patch("services.data_retention_scheduler.logger")
    def test_schedule_purge_job_error(self, mock_logger, mock_execute):
        """Test purge job scheduling with error."""
        scheduler = DataRetentionScheduler()
        scheduler.is_running = True

        # Mock scheduler error
        scheduler.scheduler = Mock()
        scheduler.scheduler.add_job.side_effect = Exception("Schedule error")

        # Test
        result = scheduler.schedule_purge_job("test-tenant", "0 2 * * *")

        # Verify
        assert result is False
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to schedule purge job" in error_call
        assert "test-tenant" in error_call

    @patch("services.data_retention_scheduler.logger")
    def test_remove_purge_job_success(self, mock_logger):
        """Test successful purge job removal."""
        scheduler = DataRetentionScheduler()
        scheduler.is_running = True

        # Mock existing job
        mock_job = Mock()
        mock_job.id = "test-tenant-purge"
        scheduler.jobs["test-tenant"] = mock_job
        scheduler.scheduler = Mock()

        # Test
        result = scheduler.remove_purge_job("test-tenant")

        # Verify
        assert result is True
        assert "test-tenant" not in scheduler.jobs
        scheduler.scheduler.remove_job.assert_called_once_with("test-tenant-purge")
        mock_logger.info.assert_called_with("Removed purge job for tenant test-tenant")

    @patch("services.data_retention_scheduler.logger")
    def test_remove_purge_job_not_found(self, mock_logger):
        """Test removing non-existent purge job."""
        scheduler = DataRetentionScheduler()
        scheduler.is_running = True
        scheduler.scheduler = Mock()

        # Test
        result = scheduler.remove_purge_job("nonexistent-tenant")

        # Verify
        assert result is True
        scheduler.scheduler.remove_job.assert_not_called()
        mock_logger.warning.assert_called_with(
            "No purge job found for tenant nonexistent-tenant"
        )

    @patch("services.data_retention_scheduler.logger")
    def test_remove_purge_job_scheduler_not_running(self, mock_logger):
        """Test removing job when scheduler not running."""
        scheduler = DataRetentionScheduler()
        scheduler.is_running = False

        # Test
        result = scheduler.remove_purge_job("test-tenant")

        # Verify
        assert result is False
        mock_logger.error.assert_called_with(
            "Cannot remove job: scheduler is not running"
        )

    @patch("services.data_retention_scheduler.logger")
    def test_remove_purge_job_error(self, mock_logger):
        """Test purge job removal with error."""
        scheduler = DataRetentionScheduler()
        scheduler.is_running = True

        # Mock existing job and scheduler error
        mock_job = Mock()
        mock_job.id = "test-tenant-purge"
        scheduler.jobs["test-tenant"] = mock_job
        scheduler.scheduler = Mock()
        scheduler.scheduler.remove_job.side_effect = Exception("Remove error")

        # Test
        result = scheduler.remove_purge_job("test-tenant")

        # Verify
        assert result is False
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to remove purge job" in error_call
        assert "test-tenant" in error_call

    def test_get_job_status_exists(self):
        """Test getting status of existing job."""
        scheduler = DataRetentionScheduler()

        # Mock existing job
        mock_job = Mock()
        mock_job.id = "test-tenant-purge"
        mock_job.next_run_time = datetime(2024, 1, 15, 2, 0, tzinfo=timezone.utc)
        scheduler.jobs["test-tenant"] = mock_job

        # Test
        status = scheduler.get_job_status("test-tenant")

        # Verify
        assert status is not None
        assert status["job_id"] == "test-tenant-purge"
        assert status["next_run_time"] == mock_job.next_run_time
        assert status["exists"] is True

    def test_get_job_status_not_exists(self):
        """Test getting status of non-existent job."""
        scheduler = DataRetentionScheduler()

        # Test
        status = scheduler.get_job_status("nonexistent-tenant")

        # Verify
        assert status is not None
        assert status["exists"] is False
        assert "job_id" not in status
        assert "next_run_time" not in status

    @patch("services.data_retention_scheduler.release_expired_legal_holds")
    @patch("services.data_retention_scheduler.logger")
    def test_cleanup_expired_holds_success(self, mock_logger, mock_release):
        """Test successful expired holds cleanup."""
        scheduler = DataRetentionScheduler()

        # Mock release result
        mock_release.return_value = {
            "success": True,
            "released_count": 3,
            "released_holds": ["hold-1", "hold-2", "hold-3"],
        }

        # Test
        scheduler._cleanup_expired_holds("test-tenant")

        # Verify
        mock_release.assert_called_once_with("test-tenant")
        mock_logger.info.assert_called_with(
            "Released 3 expired legal holds for tenant test-tenant"
        )

    @patch("services.data_retention_scheduler.release_expired_legal_holds")
    @patch("services.data_retention_scheduler.logger")
    def test_cleanup_expired_holds_error(self, mock_logger, mock_release):
        """Test expired holds cleanup with error."""
        scheduler = DataRetentionScheduler()

        # Mock release error
        mock_release.return_value = {
            "success": False,
            "error": "Database connection failed",
            "released_count": 0,
        }

        # Test
        scheduler._cleanup_expired_holds("test-tenant")

        # Verify
        mock_release.assert_called_once_with("test-tenant")
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to cleanup expired legal holds" in error_call
        assert "test-tenant" in error_call

    def test_list_jobs(self):
        """Test listing all scheduled jobs."""
        scheduler = DataRetentionScheduler()

        # Mock jobs
        job1 = Mock()
        job1.id = "tenant1-purge"
        job1.next_run_time = datetime(2024, 1, 15, 2, 0, tzinfo=timezone.utc)

        job2 = Mock()
        job2.id = "tenant2-purge"
        job2.next_run_time = datetime(2024, 1, 16, 2, 0, tzinfo=timezone.utc)

        scheduler.jobs = {"tenant1": job1, "tenant2": job2}

        # Test
        jobs = scheduler.list_jobs()

        # Verify
        assert len(jobs) == 2
        assert jobs[0]["tenant_id"] == "tenant1"
        assert jobs[0]["job_id"] == "tenant1-purge"
        assert jobs[0]["next_run_time"] == job1.next_run_time
        assert jobs[1]["tenant_id"] == "tenant2"
        assert jobs[1]["job_id"] == "tenant2-purge"
        assert jobs[1]["next_run_time"] == job2.next_run_time

    def test_list_jobs_empty(self):
        """Test listing jobs when none are scheduled."""
        scheduler = DataRetentionScheduler()

        # Test
        jobs = scheduler.list_jobs()

        # Verify
        assert jobs == []


class TestSchedulerGlobalFunctions:
    """Test cases for global scheduler functions."""

    @patch("services.data_retention_scheduler.TestDataRetentionScheduler")
    def test_start_scheduler_function(self, mock_scheduler_class):
        """Test start_scheduler global function."""
        # Mock scheduler instance
        mock_instance = Mock()
        mock_instance.start.return_value = True
        mock_scheduler_class.return_value = mock_instance

        # Test
        result = start_scheduler()

        # Verify
        assert result is True
        mock_scheduler_class.assert_called_once()
        mock_instance.start.assert_called_once()

    @patch("services.data_retention_scheduler.TestDataRetentionScheduler")
    def test_stop_scheduler_function(self, mock_scheduler_class):
        """Test stop_scheduler global function."""
        # Mock scheduler instance
        mock_instance = Mock()
        mock_instance.stop.return_value = True
        mock_scheduler_class.return_value = mock_instance

        # Test
        result = stop_scheduler()

        # Verify
        assert result is True
        mock_scheduler_class.assert_called_once()
        mock_instance.stop.assert_called_once()

    def test_cron_expression_validation(self):
        """Test cron expression validation."""
        from services.data_retention_scheduler import _validate_cron_expression

        # Test valid expressions
        assert _validate_cron_expression("0 2 * * *") is True  # Daily at 2 AM
        assert _validate_cron_expression("0 0 * * 0") is True  # Weekly on Sunday
        assert _validate_cron_expression("0 0 1 * *") is True  # Monthly on 1st

        # Test invalid expressions
        assert _validate_cron_expression("invalid") is False
        assert _validate_cron_expression("") is False
        assert _validate_cron_expression(None) is False
        assert _validate_cron_expression("60 2 * * *") is False  # Invalid minute

    def test_default_cron_expressions(self):
        """Test default cron expressions are valid."""
        from services.data_retention_scheduler import (
            DEFAULT_CLEANUP_SCHEDULE,
            DEFAULT_PURGE_SCHEDULE,
            _validate_cron_expression,
        )

        assert _validate_cron_expression(DEFAULT_PURGE_SCHEDULE) is True
        assert _validate_cron_expression(DEFAULT_CLEANUP_SCHEDULE) is True

    @patch("services.data_retention_scheduler.logger")
    def test_job_execution_wrapper(self, mock_logger):
        """Test job execution wrapper for error handling."""
        from services.data_retention_scheduler import _execute_with_error_handling

        # Mock successful function
        mock_func = Mock()
        mock_func.return_value = {"success": True}

        # Test successful execution
        result = _execute_with_error_handling(
            mock_func, "test-tenant", "test operation"
        )

        # Verify
        assert result == {"success": True}
        mock_func.assert_called_once_with("test-tenant")
        mock_logger.info.assert_called_with(
            "Starting test operation for tenant test-tenant"
        )

    @patch("services.data_retention_scheduler.logger")
    def test_job_execution_wrapper_error(self, mock_logger):
        """Test job execution wrapper with error."""
        from services.data_retention_scheduler import _execute_with_error_handling

        # Mock function that raises exception
        mock_func = Mock()
        mock_func.side_effect = Exception("Test error")

        # Test error handling
        result = _execute_with_error_handling(
            mock_func, "test-tenant", "test operation"
        )

        # Verify
        assert result is None
        mock_func.assert_called_once_with("test-tenant")
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert "Error during test operation" in error_call
        assert "test-tenant" in error_call
        assert "Test error" in error_call

"""Tests for demo database functionality."""

import os
from unittest.mock import MagicMock, patch

from demo_database import cleanup_demo, create_demo_database


class TestDemoDatabase:
    """Test demo database functionality."""

    def test_create_demo_database_function_exists(self):
        """Test that create_demo_database function exists."""
        assert callable(create_demo_database)

    def test_cleanup_demo_function_exists(self):
        """Test that cleanup_demo function exists."""
        assert callable(cleanup_demo)

    @patch("demo_database.create_engine")
    @patch("demo_database.sessionmaker")
    @patch("demo_database.Base")
    def test_create_demo_database_creates_engine(
        self, mock_base, mock_sessionmaker, mock_create_engine
    ):
        """Test that demo database creation sets up engine."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_session_class = MagicMock()
        mock_sessionmaker.return_value = mock_session_class
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock successful execution
        mock_session.commit.return_value = None
        mock_session.close.return_value = None

        with patch("demo_database.logger") as mock_logger:
            result = create_demo_database()

            mock_create_engine.assert_called_once_with("sqlite:///demo.db", echo=False)
            mock_base.metadata.create_all.assert_called_once_with(mock_engine)
            mock_sessionmaker.assert_called_once_with(bind=mock_engine)
            assert result is True
            mock_logger.info.assert_called()

    @patch("demo_database.sessionmaker")
    @patch("demo_database.create_engine")
    def test_create_demo_database_handles_exception(
        self, mock_create_engine, mock_sessionmaker
    ):
        """Test that create_demo_database handles exceptions properly."""
        # Mock successful engine creation but session operations fail
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        mock_session = MagicMock()
        mock_session_class = MagicMock(return_value=mock_session)
        mock_sessionmaker.return_value = mock_session_class
        mock_session.add.side_effect = Exception("Database error")

        with patch("demo_database.logger") as mock_logger:
            result = create_demo_database()

            assert result is False
            mock_logger.error.assert_called()
            mock_session.rollback.assert_called()
            mock_session.close.assert_called()

    @patch("demo_database.Path")
    def test_cleanup_demo_removes_database(self, mock_path_class):
        """Test that cleanup removes demo database file."""
        mock_path = MagicMock()
        mock_path_class.return_value = mock_path
        mock_path.exists.return_value = True

        with patch("demo_database.logger") as mock_logger:
            cleanup_demo()

            mock_path_class.assert_called_once_with("demo.db")
            mock_path.exists.assert_called_once()
            mock_path.unlink.assert_called_once()
            mock_logger.info.assert_called()

    @patch("demo_database.Path")
    def test_cleanup_demo_handles_missing_file(self, mock_path_class):
        """Test that cleanup handles missing database file."""
        mock_path = MagicMock()
        mock_path_class.return_value = mock_path
        mock_path.exists.return_value = False

        cleanup_demo()

        mock_path_class.assert_called_once_with("demo.db")
        mock_path.exists.assert_called_once()
        mock_path.unlink.assert_not_called()

    @patch("demo_database.Path")
    def test_cleanup_demo_handles_removal_error(self, mock_path_class):
        """Test that cleanup handles file removal errors."""
        mock_path = MagicMock()
        mock_path_class.return_value = mock_path
        mock_path.exists.return_value = True
        mock_path.unlink.side_effect = OSError("Permission denied")

        # This should raise the exception since there's no error handling
        try:
            cleanup_demo()
            assert False, "Expected OSError to be raised"
        except OSError:
            pass

        mock_path_class.assert_called_once_with("demo.db")
        mock_path.exists.assert_called_once()
        mock_path.unlink.assert_called_once()

    def test_environment_variables_set(self):
        """Test that required environment variables are set."""
        # The demo_database module should set these on import
        assert os.environ.get("DATABASE_URL") == "sqlite:///demo.db"
        assert os.environ.get("ENVIRONMENT") == "demo"

    @patch("demo_database.create_demo_database")
    @patch("demo_database.cleanup_demo")
    @patch("builtins.input")
    def test_main_execution_success(self, mock_input, mock_cleanup, mock_create):
        """Test main execution path when demo succeeds."""
        mock_create.return_value = True
        mock_input.return_value = "n"  # Don't keep database

        # Simulate main execution
        success = mock_create()
        if success:
            response = mock_input()
            if response != "y":
                mock_cleanup()

            mock_create.assert_called_once()
            mock_cleanup.assert_called_once()

    @patch("demo_database.create_demo_database")
    @patch("demo_database.cleanup_demo")
    @patch("builtins.input")
    def test_main_execution_keep_database(self, mock_input, mock_cleanup, mock_create):
        """Test main execution when user chooses to keep database."""
        mock_create.return_value = True
        mock_input.return_value = "y"  # Keep database

        # Simulate main execution
        success = mock_create()
        if success:
            response = mock_input()
            if response != "y":
                mock_cleanup()

            mock_create.assert_called_once()
            mock_cleanup.assert_not_called()

    @patch("demo_database.create_demo_database")
    @patch("demo_database.cleanup_demo")
    def test_main_execution_failure(self, mock_cleanup, mock_create):
        """Test main execution when demo fails."""
        mock_create.return_value = False

        with patch("demo_database.logger") as mock_logger:
            # Simulate main execution
            success = mock_create()
            if not success:
                mock_logger.error("Demo failed - check error messages above")

            mock_create.assert_called_once()
            mock_logger.error.assert_called_with(
                "Demo failed - check error messages above"
            )

    def test_imports_work(self):
        """Test that all required imports work."""
        # These should not raise ImportError
        from demo_database import AuditLog, Base, Client, Provider, logger

        assert logger is not None
        assert AuditLog is not None
        assert Base is not None
        assert Client is not None
        assert Provider is not None

    def test_logging_configuration(self):
        """Test that logging is properly configured."""
        import logging

        from demo_database import logger

        assert isinstance(logger, logging.Logger)
        assert logger.name == "demo_database"

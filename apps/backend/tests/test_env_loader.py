"""Tests for core/env_loader.py module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from core.env_loader import (
    _load_env_file,
    get_environment_info,
    load_environment_config,
    validate_required_env_vars,
)


class TestLoadEnvironmentConfig:
    """Test cases for load_environment_config function."""

    def test_load_environment_config_test_env(self):
        """Test loading test environment configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary .env.test file
            env_test_file = Path(temp_dir) / ".env.test"
            env_test_file.write_text("TEST_VAR=test_value\n")

            with patch("core.env_loader.Path") as mock_path:
                # Mock the project root path
                mock_path.return_value.parent.parent.parent.parent = Path(temp_dir)
                mock_path.__file__ = "core/env_loader.py"

                # Clear any existing TEST_VAR
                if "TEST_VAR" in os.environ:
                    del os.environ["TEST_VAR"]

                load_environment_config("test")

                assert os.environ.get("TEST_VAR") == "test_value"

                # Clean up
                if "TEST_VAR" in os.environ:
                    del os.environ["TEST_VAR"]

    def test_load_environment_config_staging_env(self):
        """Test loading staging environment configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary .env.staging file
            env_staging_file = Path(temp_dir) / ".env.staging"
            env_staging_file.write_text("STAGING_VAR=staging_value\n")

            with patch("core.env_loader.Path") as mock_path:
                # Mock the project root path
                mock_path.return_value.parent.parent.parent.parent = Path(temp_dir)
                mock_path.__file__ = "core/env_loader.py"

                # Clear any existing STAGING_VAR
                if "STAGING_VAR" in os.environ:
                    del os.environ["STAGING_VAR"]

                load_environment_config("staging")

                assert os.environ.get("STAGING_VAR") == "staging_value"

                # Clean up
                if "STAGING_VAR" in os.environ:
                    del os.environ["STAGING_VAR"]

    def test_load_environment_config_production_env(self):
        """Test loading production environment configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary .env.production file
            env_prod_file = Path(temp_dir) / ".env.production"
            env_prod_file.write_text("PROD_VAR=prod_value\n")

            with patch("core.env_loader.Path") as mock_path:
                # Mock the project root path
                mock_path.return_value.parent.parent.parent.parent = Path(temp_dir)
                mock_path.__file__ = "core/env_loader.py"

                # Clear any existing PROD_VAR
                if "PROD_VAR" in os.environ:
                    del os.environ["PROD_VAR"]

                load_environment_config("production")

                assert os.environ.get("PROD_VAR") == "prod_value"

                # Clean up
                if "PROD_VAR" in os.environ:
                    del os.environ["PROD_VAR"]

    def test_load_environment_config_fallback_to_default(self):
        """Test fallback to default .env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary .env file
            env_file = Path(temp_dir) / ".env"
            env_file.write_text("DEFAULT_VAR=default_value\n")

            with patch("core.env_loader.Path") as mock_path:
                # Mock the project root path
                mock_path.return_value.parent.parent.parent.parent = Path(temp_dir)
                mock_path.__file__ = "core/env_loader.py"

                # Clear any existing DEFAULT_VAR
                if "DEFAULT_VAR" in os.environ:
                    del os.environ["DEFAULT_VAR"]

                load_environment_config("development")

                assert os.environ.get("DEFAULT_VAR") == "default_value"

                # Clean up
                if "DEFAULT_VAR" in os.environ:
                    del os.environ["DEFAULT_VAR"]

    def test_load_environment_config_no_env_specified(self):
        """Test loading config when no environment is specified."""
        with patch.dict(os.environ, {"ENVIRONMENT": "test"}, clear=False):
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create a temporary .env.test file
                env_test_file = Path(temp_dir) / ".env.test"
                env_test_file.write_text("AUTO_VAR=auto_value\n")

                with patch("core.env_loader.Path") as mock_path:
                    # Mock the project root path
                    mock_path.return_value.parent.parent.parent.parent = Path(temp_dir)
                    mock_path.__file__ = "core/env_loader.py"

                    # Clear any existing AUTO_VAR
                    if "AUTO_VAR" in os.environ:
                        del os.environ["AUTO_VAR"]

                    load_environment_config()

                    assert os.environ.get("AUTO_VAR") == "auto_value"

                    # Clean up
                    if "AUTO_VAR" in os.environ:
                        del os.environ["AUTO_VAR"]

    def test_load_environment_config_no_file_found(self):
        """Test behavior when no .env file is found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("core.env_loader.Path") as mock_path:
                # Mock the project root path to empty directory
                mock_path.return_value.parent.parent.parent.parent = Path(temp_dir)
                mock_path.__file__ = "core/env_loader.py"

                # Should not raise an exception
                load_environment_config("nonexistent")


class TestLoadEnvFile:
    """Test cases for _load_env_file function."""

    def test_load_env_file_basic(self):
        """Test basic .env file loading."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("KEY1=value1\n")
            f.write("KEY2=value2\n")
            f.flush()

            # Clear any existing keys
            for key in ["KEY1", "KEY2"]:
                if key in os.environ:
                    del os.environ[key]

            _load_env_file(Path(f.name))

            assert os.environ.get("KEY1") == "value1"
            assert os.environ.get("KEY2") == "value2"

            # Clean up
            for key in ["KEY1", "KEY2"]:
                if key in os.environ:
                    del os.environ[key]
            os.unlink(f.name)

    def test_load_env_file_with_quotes(self):
        """Test loading .env file with quoted values."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write('QUOTED_DOUBLE="double quoted value"\n')
            f.write("QUOTED_SINGLE='single quoted value'\n")
            f.flush()

            # Clear any existing keys
            for key in ["QUOTED_DOUBLE", "QUOTED_SINGLE"]:
                if key in os.environ:
                    del os.environ[key]

            _load_env_file(Path(f.name))

            assert os.environ.get("QUOTED_DOUBLE") == "double quoted value"
            assert os.environ.get("QUOTED_SINGLE") == "single quoted value"

            # Clean up
            for key in ["QUOTED_DOUBLE", "QUOTED_SINGLE"]:
                if key in os.environ:
                    del os.environ[key]
            os.unlink(f.name)

    def test_load_env_file_skip_comments_and_empty_lines(self):
        """Test that comments and empty lines are skipped."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("# This is a comment\n")
            f.write("\n")
            f.write("VALID_KEY=valid_value\n")
            f.write("# Another comment\n")
            f.flush()

            # Clear any existing key
            if "VALID_KEY" in os.environ:
                del os.environ["VALID_KEY"]

            _load_env_file(Path(f.name))

            assert os.environ.get("VALID_KEY") == "valid_value"

            # Clean up
            if "VALID_KEY" in os.environ:
                del os.environ["VALID_KEY"]
            os.unlink(f.name)

    def test_load_env_file_preserves_existing_env_vars(self):
        """Test that existing environment variables are not overwritten."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("EXISTING_VAR=new_value\n")
            f.flush()

            # Set existing environment variable
            os.environ["EXISTING_VAR"] = "original_value"

            _load_env_file(Path(f.name))

            # Should preserve original value
            assert os.environ.get("EXISTING_VAR") == "original_value"

            # Clean up
            del os.environ["EXISTING_VAR"]
            os.unlink(f.name)

    def test_load_env_file_invalid_format(self):
        """Test handling of invalid line format."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("VALID_KEY=valid_value\n")
            f.write("INVALID_LINE_NO_EQUALS\n")
            f.write("ANOTHER_VALID=another_value\n")
            f.flush()

            # Clear any existing keys
            for key in ["VALID_KEY", "ANOTHER_VALID"]:
                if key in os.environ:
                    del os.environ[key]

            # Should not raise exception, just log warning
            _load_env_file(Path(f.name))

            # Valid keys should still be loaded
            assert os.environ.get("VALID_KEY") == "valid_value"
            assert os.environ.get("ANOTHER_VALID") == "another_value"

            # Clean up
            for key in ["VALID_KEY", "ANOTHER_VALID"]:
                if key in os.environ:
                    del os.environ[key]
            os.unlink(f.name)

    def test_load_env_file_file_not_found(self):
        """Test handling of non-existent file."""
        with pytest.raises(FileNotFoundError):
            _load_env_file(Path("/nonexistent/file.env"))


class TestGetEnvironmentInfo:
    """Test cases for get_environment_info function."""

    def test_get_environment_info_defaults(self):
        """Test get_environment_info with default values."""
        # Clear relevant environment variables
        env_vars_to_clear = [
            "ENVIRONMENT",
            "DEBUG",
            "LOG_LEVEL",
            "DATABASE_URL",
            "REDIS_URL",
            "SECRET_KEY",
            "JWT_SECRET_KEY",
        ]
        original_values = {}
        for var in env_vars_to_clear:
            if var in os.environ:
                original_values[var] = os.environ[var]
                del os.environ[var]

        try:
            info = get_environment_info()

            assert info["environment"] == "development"
            assert info["debug"] is False
            assert info["log_level"] == "INFO"
            assert info["database_url_set"] is False
            assert info["redis_url_set"] is False
            assert info["secret_key_set"] is False
            assert info["jwt_secret_key_set"] is False
        finally:
            # Restore original values
            for var, value in original_values.items():
                os.environ[var] = value

    def test_get_environment_info_with_values(self):
        """Test get_environment_info with set values."""
        test_env_vars = {
            "ENVIRONMENT": "production",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "DATABASE_URL": "postgresql://localhost/test",
            "REDIS_URL": "redis://localhost:6379",
            "SECRET_KEY": "test-secret",
            "JWT_SECRET_KEY": "test-jwt-secret",
        }

        with patch.dict(os.environ, test_env_vars, clear=False):
            info = get_environment_info()

            assert info["environment"] == "production"
            assert info["debug"] is True
            assert info["log_level"] == "DEBUG"
            assert info["database_url_set"] is True
            assert info["redis_url_set"] is True
            assert info["secret_key_set"] is True
            assert info["jwt_secret_key_set"] is True

    def test_get_environment_info_debug_false_variations(self):
        """Test debug flag with various false values."""
        false_values = ["false", "False", "FALSE", "0", "no", "No"]

        for false_val in false_values:
            with patch.dict(os.environ, {"DEBUG": false_val}, clear=False):
                info = get_environment_info()
                assert info["debug"] is False


class TestValidateRequiredEnvVars:
    """Test cases for validate_required_env_vars function."""

    def test_validate_required_env_vars_all_present(self):
        """Test validation when all required vars are present."""
        required_vars = {
            "SECRET_KEY": "test-secret",
            "JWT_SECRET_KEY": "test-jwt-secret",
            "DATABASE_URL": "postgresql://localhost/test",
            "REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, required_vars, clear=False):
            missing = validate_required_env_vars()
            assert missing == []

    def test_validate_required_env_vars_some_missing(self):
        """Test validation when some required vars are missing."""
        # Clear all required vars
        required_vars = ["SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL", "REDIS_URL"]
        original_values = {}
        for var in required_vars:
            if var in os.environ:
                original_values[var] = os.environ[var]
                del os.environ[var]

        try:
            # Set only some vars
            with patch.dict(
                os.environ, {"SECRET_KEY": "test", "DATABASE_URL": "test"}, clear=False
            ):
                missing = validate_required_env_vars()
                assert set(missing) == {"JWT_SECRET_KEY", "REDIS_URL"}
        finally:
            # Restore original values
            for var, value in original_values.items():
                os.environ[var] = value

    def test_validate_required_env_vars_all_missing(self):
        """Test validation when all required vars are missing."""
        # Clear all required vars
        required_vars = ["SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL", "REDIS_URL"]
        original_values = {}
        for var in required_vars:
            if var in os.environ:
                original_values[var] = os.environ[var]
                del os.environ[var]

        try:
            missing = validate_required_env_vars()
            assert set(missing) == set(required_vars)
        finally:
            # Restore original values
            for var, value in original_values.items():
                os.environ[var] = value

    def test_validate_required_env_vars_empty_values(self):
        """Test validation with empty string values."""
        empty_vars = {
            "SECRET_KEY": "",
            "JWT_SECRET_KEY": "",
            "DATABASE_URL": "",
            "REDIS_URL": "",
        }

        with patch.dict(os.environ, empty_vars, clear=False):
            missing = validate_required_env_vars()
            # Empty strings should be considered missing
            assert set(missing) == set(empty_vars.keys())

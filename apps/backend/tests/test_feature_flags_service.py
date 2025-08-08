"""Tests for the feature flags service."""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from config.feature_flags_config import FeatureFlagsConfig
from services.feature_flags_service import FeatureFlagsService


class TestFeatureFlagsService:
    """Test cases for FeatureFlagsService."""

    def setup_method(self):
        """Set up test fixtures."""
        # Store original environment variables
        self.original_env = {
            "FEATURE_FLAGS_PROVIDER": os.environ.get("FEATURE_FLAGS_PROVIDER"),
            "ENVIRONMENT": os.environ.get("ENVIRONMENT"),
            "FEATURE_FLAGS_FILE": os.environ.get("FEATURE_FLAGS_FILE"),
        }

        # Create a temporary file for local flags
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        self.temp_file_path = self.temp_file.name

        # Write test flags to the temporary file
        test_flags = {
            "development": {
                "video_calls_enabled": True,
                "edi_integration_enabled": False,
                "payments_enabled": True,
                "advanced_reporting_enabled": False,
            }
        }
        json.dump(test_flags, self.temp_file)
        self.temp_file.close()

        # Create test config by patching environment variables
        os.environ["FEATURE_FLAGS_PROVIDER"] = "local"
        os.environ["ENVIRONMENT"] = "development"
        os.environ["FEATURE_FLAGS_FILE"] = self.temp_file_path

        self.config = FeatureFlagsConfig()

        self.service = FeatureFlagsService(self.config)

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_file_path):
            os.unlink(self.temp_file_path)

        # Restore original environment variables
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_is_enabled_existing_flag_true(self):
        """Test evaluating an existing flag that is True."""
        result = self.service.is_enabled(
            "video_calls_enabled", user_id="user123", default=False
        )
        assert result is True

    def test_is_enabled_existing_flag_false(self):
        """Test evaluating an existing flag that is False."""
        result = self.service.is_enabled(
            "edi_integration_enabled", user_id="user123", default=True
        )
        assert result is False

    def test_is_enabled_nonexistent_flag_returns_default(self):
        """Test evaluating a non-existent flag returns default value."""
        result = self.service.is_enabled(
            "nonexistent_flag", user_id="user123", default=True
        )
        assert result is True

    def test_get_all_flags(self):
        """Test getting all flags for the current environment."""
        flags = self.service.get_all_flags()

        # Should contain all flags from test data
        assert "video_calls_enabled" in flags
        assert "edi_integration_enabled" in flags
        assert "payments_enabled" in flags
        assert "advanced_reporting_enabled" in flags
        assert isinstance(flags["video_calls_enabled"], bool)
        assert isinstance(flags["advanced_reporting_enabled"], bool)

    def test_get_flag_info(self):
        """Test getting flag information."""
        info = self.service.get_flag_info("video_calls_enabled")
        assert info["name"] == "video_calls_enabled"
        assert "default_value" in info
        assert "environment" in info

    def test_get_flag_info_nonexistent_flag(self):
        """Test getting info for non-existent flag returns None."""
        info = self.service.get_flag_info("nonexistent_flag")
        assert info["name"] == "nonexistent_flag"
        assert info["default_value"] is None

    def test_is_enabled_logs_evaluation(self):
        """Test that flag evaluation is logged."""
        with patch.object(self.service, "logger") as mock_logger:
            self.service.is_enabled(
                "video_calls_enabled", user_id="user123", default=False
            )
            mock_logger.info.assert_called()

    def test_clear_cache(self):
        """Test clearing the cache."""
        # First, populate the cache
        self.service.is_enabled("video_calls_enabled", user_id="user123", default=False)

        # Verify cache has entries
        assert len(self.service._cache) > 0

        # Clear cache
        self.service.clear_cache()

        # Verify cache is empty
        assert len(self.service._cache) == 0

    @patch.dict(
        "os.environ",
        {
            "FEATURE_FLAGS_PROVIDER": "local",
            "ENVIRONMENT": "development",
            "FEATURE_FLAGS_FILE": "/nonexistent/file.json",
        },
    )
    def test_load_local_flags_file_not_found(self):
        """Test loading local flags when file doesn't exist."""

        config = FeatureFlagsConfig()
        service = FeatureFlagsService(config)

        # Should fall back to default flags
        flags = service.get_all_flags()
        # Should have some default flags from the config
        assert isinstance(flags, dict)

    def test_load_local_flags_invalid_json(self):
        """Test loading local flags with invalid JSON."""
        # Create a file with invalid JSON
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        temp_file.write("invalid json content")
        temp_file.close()

        try:
            with patch.dict(
                "os.environ",
                {
                    "FEATURE_FLAGS_PROVIDER": "local",
                    "ENVIRONMENT": "development",
                    "FEATURE_FLAGS_FILE": temp_file.name,
                },
            ):
                config = FeatureFlagsConfig()
                service = FeatureFlagsService(config)

                # Should fall back to default flags
                flags = service.get_all_flags()
                assert isinstance(flags, dict)
        finally:
            os.unlink(temp_file.name)

    def test_context_scrubbing(self):
        """Test that PHI is scrubbed from context in logs."""
        with patch.object(self.service, "logger") as mock_logger:
            self.service.is_enabled(
                "video_calls_enabled",
                user_id="user123",
                default=False,
                ssn="123-45-6789",
                email="test@example.com",
            )

            # Check that logger was called with scrubbed context
            mock_logger.info.assert_called()
            call_args = str(mock_logger.info.call_args)
            assert "123-45-6789" not in call_args
            assert "test@example.com" not in call_args

    @patch("services.feature_flags_service.FLAG_EVALUATIONS")
    def test_metrics_recorded(self, mock_counter):
        """Test that Prometheus metrics are recorded."""
        self.service.is_enabled("video_calls_enabled", user_id="user123", default=False)

        # Verify metrics were recorded
        mock_counter.labels.assert_called_with(
            flag_name="video_calls_enabled", environment="development", result="True"
        )
        mock_counter.labels.return_value.inc.assert_called_once()


class TestFeatureFlagsConfig:
    """Test cases for FeatureFlagsConfig."""

    def test_config_initialization_with_defaults(self):
        """Test config initialization with default values."""
        with patch.dict(
            os.environ,
            {
                "FEATURE_FLAGS_PROVIDER": "local",
                "ENVIRONMENT": "development",
                "FEATURE_FLAGS_FILE": "/path/to/flags.json",
            },
        ):
            config = FeatureFlagsConfig()
            assert config.provider == "local"
            assert config.environment == "development"
            assert config.local_flags_file == "/path/to/flags.json"

    def test_config_initialization_with_custom_values(self):
        """Test config initialization with custom values."""
        with patch.dict(
            os.environ,
            {
                "FEATURE_FLAGS_PROVIDER": "launchdarkly",
                "ENVIRONMENT": "staging",
                "LAUNCHDARKLY_SDK_KEY": "test-key",
            },
        ):
            config = FeatureFlagsConfig()
            assert config.provider == "launchdarkly"
            assert config.environment == "staging"
            assert config.launchdarkly_sdk_key == "test-key"

    def test_validate_config_valid_local_provider(self):
        """Test validation passes for valid local provider config."""
        with patch.dict(
            os.environ,
            {"FEATURE_FLAGS_PROVIDER": "local", "ENVIRONMENT": "development"},
        ):
            config = FeatureFlagsConfig()
            # Should not raise an exception
            config._validate_configuration()

    def test_validate_config_valid_launchdarkly_provider(self):
        """Test validation passes for valid LaunchDarkly config."""
        with patch.dict(
            os.environ,
            {
                "FEATURE_FLAGS_PROVIDER": "launchdarkly",
                "ENVIRONMENT": "production",
                "LAUNCHDARKLY_SDK_KEY": "test-key",
            },
        ):
            config = FeatureFlagsConfig()
            # Should not raise an exception
            config._validate_configuration()

    def test_validate_config_invalid_environment(self):
        """Test validation fails for invalid environment."""
        with patch.dict(
            os.environ,
            {"ENVIRONMENT": "invalid_env", "FEATURE_FLAGS_PROVIDER": "local"},
        ):
            with pytest.raises(ValueError, match="Invalid environment"):
                FeatureFlagsConfig()

    def test_validate_config_missing_launchdarkly_key(self):
        """Test validation fails when LaunchDarkly key is missing."""
        with patch.dict(
            os.environ,
            {"ENVIRONMENT": "production", "FEATURE_FLAGS_PROVIDER": "launchdarkly"},
            clear=True,
        ):
            with pytest.raises(ValueError, match="LaunchDarkly SDK key is required"):
                FeatureFlagsConfig()

    def test_get_flag_context_basic(self):
        """Test getting basic context."""
        with patch.dict(
            os.environ,
            {"ENVIRONMENT": "development", "FEATURE_FLAGS_PROVIDER": "local"},
        ):
            config = FeatureFlagsConfig()
            context = config.get_flag_context(
                user_id="user123", ip_address="192.168.1.1"
            )

            assert "user_id" in context
            assert "ip_address" in context
            assert "environment" in context
            assert context["environment"] == "development"

    def test_get_flag_context_with_custom_attributes(self):
        """Test getting context with custom attributes."""
        with patch.dict(
            os.environ,
            {"ENVIRONMENT": "development", "FEATURE_FLAGS_PROVIDER": "local"},
        ):
            config = FeatureFlagsConfig()
            context = config.get_flag_context(
                user_id="user123", custom_attr1="value1", custom_attr2="value2"
            )

            assert context["custom_attr1"] == "value1"
            assert context["custom_attr2"] == "value2"

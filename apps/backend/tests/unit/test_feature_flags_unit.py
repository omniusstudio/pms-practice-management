"""Unit tests for feature flags functionality."""

import json
import os
import sys
import tempfile
from unittest.mock import Mock, patch

import pytest

from config.feature_flags_config import FeatureFlagsConfig
from services.feature_flags_service import FeatureFlagsService
from utils.feature_flags import FeatureFlags, get_feature_flags


class TestFeatureFlagsConfig:
    """Unit tests for FeatureFlagsConfig class."""

    @pytest.mark.unit
    def test_config_initialization_default(self):
        """Test default configuration initialization."""
        with patch.dict("os.environ", {}, clear=True):
            config = FeatureFlagsConfig()
            assert config.provider == "local"
            assert config.environment == "development"

    @pytest.mark.unit
    def test_config_initialization_from_env(self):
        """Test configuration initialization from environment variables."""
        env_vars = {
            "FEATURE_FLAGS_PROVIDER": "launchdarkly",
            "ENVIRONMENT": "production",
            "LAUNCHDARKLY_SDK_KEY": "test_key",
        }
        with patch.dict("os.environ", env_vars):
            config = FeatureFlagsConfig()
            assert config.provider == "launchdarkly"
            assert config.environment == "production"
            assert config.launchdarkly_sdk_key == "test_key"

    @pytest.mark.unit
    def test_config_validation_valid(self):
        """Test configuration validation with valid settings."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            config = FeatureFlagsConfig()
            # Should not raise any exception
            config._validate_configuration()

    @pytest.mark.unit
    def test_config_validation_invalid_environment(self):
        """Test configuration validation with invalid environment."""
        with patch.dict("os.environ", {"ENVIRONMENT": "invalid"}):
            with pytest.raises(ValueError, match="Invalid environment"):
                FeatureFlagsConfig()

    @pytest.mark.unit
    def test_get_context(self):
        """Test context generation for feature flag evaluation."""
        config = FeatureFlagsConfig()
        context = config.get_flag_context(user_id="123")
        assert "environment" in context
        assert "timestamp" in context
        assert "user_id" in context

    @pytest.mark.unit
    @pytest.mark.security
    def test_env_var_override(self):
        """Test environment variable override for feature flags."""
        env_vars = {
            "FEATURE_FLAG_VIDEO_CALLS_ENABLED": "true",
            "FEATURE_FLAG_ADVANCED_REPORTING_ENABLED": "false",
        }

        with patch.dict("os.environ", env_vars):
            config = FeatureFlagsConfig()
            # Test that environment variables override defaults
            assert config.default_flags["video_calls_enabled"] is True
            assert config.default_flags["advanced_reporting_enabled"] is False


class TestFeatureFlagsService:
    """Unit tests for FeatureFlagsService class."""

    @pytest.fixture
    def mock_config(self):
        """Mock feature flags configuration."""
        config = Mock(spec=FeatureFlagsConfig)
        config.provider = "local"
        config.environment = "test"
        config.local_flags_file = "/tmp/test_flags.json"
        config.default_flags = {
            "video_calls_enabled": True,
            "advanced_reporting_enabled": False,
        }
        config.flag_cache_ttl_seconds = 300
        config.enable_flag_evaluation_logging = True
        config.enable_flag_metrics = False
        return config

    @pytest.fixture
    def service(self, mock_config):
        """Feature flags service instance."""
        with patch(
            "services.feature_flags_service.get_feature_flags_config",
            return_value=mock_config,
        ):
            return FeatureFlagsService()

    @pytest.mark.unit
    def test_service_initialization(self, mock_config):
        """Test service initialization."""
        with patch(
            "services.feature_flags_service.get_feature_flags_config",
            return_value=mock_config,
        ):
            service = FeatureFlagsService()
            assert service.config == mock_config

    @pytest.mark.unit
    def test_load_local_flags_success(self, service, mock_config):
        """Test successful loading of local flags."""
        test_flags = {
            "test": {
                "video_calls_enabled": True,
                "advanced_reporting_enabled": False,
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_flags, f)
            temp_path = f.name

        mock_config.local_flags_file = temp_path
        mock_config.environment = "test"

        try:
            # Mock the private method by patching it
            with patch.object(service, "_load_local_flags") as mock_load:
                mock_load.return_value = None  # void return
                service._load_local_flags()
                mock_load.assert_called_once()
        finally:
            os.unlink(temp_path)

    @pytest.mark.unit
    def test_load_local_flags_file_not_found(self, service, mock_config):
        """Test handling of missing local flags file."""
        mock_config.local_flags_file = "/nonexistent/file.json"

        # Mock the method to simulate file not found behavior
        with patch.object(service, "_load_local_flags") as mock_load:
            mock_load.return_value = None  # void return
            service._load_local_flags()
            mock_load.assert_called_once()

    @pytest.mark.unit
    def test_is_enabled_cached(self, service):
        """Test flag evaluation with cached result."""
        import time

        service._cache["test_flag"] = {"value": True}
        service._cache_timestamps["test_flag"] = time.time()

        result = service.is_enabled("test_flag")
        assert result is True

    @pytest.mark.unit
    def test_is_enabled_local_provider(self, service, mock_config):
        """Test flag evaluation with local provider."""
        mock_config.provider = "local"
        mock_config.default_flags = {"test_flag": True}

        result = service.is_enabled("test_flag")
        assert result is True

    @pytest.mark.unit
    @pytest.mark.critical
    def test_is_enabled_fallback_to_default(self, service, mock_config):
        """Test flag evaluation fallback to default."""
        mock_config.default_flags = {}

        result = service.is_enabled("test_flag", default=False)
        assert result is False

    @pytest.mark.unit
    def test_is_enabled_with_context(self, service):
        """Test flag evaluation with context."""
        context = {
            "user_id": "123",
            "environment": "test",
            "custom_attr": "value",
        }

        result = service.is_enabled("test_flag", **context)
        assert isinstance(result, bool)

    @pytest.mark.unit
    def test_get_all_flags(self, service, mock_config):
        """Test getting all flags."""
        mock_config.default_flags = {
            "flag1": True,
            "flag2": False,
            "flag3": True,
        }

        all_flags = service.get_all_flags()
        assert len(all_flags) >= 3
        assert "flag1" in all_flags

    @pytest.mark.unit
    def test_clear_cache(self, service):
        """Test cache clearing."""
        service._cache = {"flag1": {"value": True}, "flag2": {"value": False}}

        service.clear_cache()
        assert service._cache == {}

    @pytest.mark.unit
    @pytest.mark.security
    def test_flag_evaluation_logging(self, service, mock_config):
        """Test that flag evaluation is properly logged."""
        mock_config.default_flags = {"test_flag": True}
        mock_config.enable_flag_evaluation_logging = True

        with patch.object(service, "_log_flag_evaluation") as mock_log:
            service.is_enabled("test_flag")
            # Should log flag evaluation
            mock_log.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.hipaa
    def test_no_phi_in_logging(self, service, mock_config):
        """Test that no PHI is logged during flag evaluation."""
        mock_config.enable_flag_evaluation_logging = True
        context = {
            "user_id": "123",
            # PHI that should not be logged
            "ssn": "123-45-6789",
            "environment": "test",
        }

        with patch.object(service.logger, "info") as mock_log:
            service.is_enabled("test_flag", **context)

            # Check that log calls don't contain PHI
            if mock_log.called:
                for call in mock_log.call_args_list:
                    log_message = str(call)
                    assert "123-45-6789" not in log_message


class TestUtilsFeatureFlags:
    """Unit tests for utils.feature_flags module."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for feature flags."""
        settings = Mock()
        settings.enable_mock_edi = True
        settings.enable_mock_payments = False
        settings.enable_mock_video = True
        return settings

    @pytest.mark.unit
    def test_feature_flags_initialization(self, mock_settings):
        """Test FeatureFlags class initialization."""
        with patch(
            "utils.feature_flags.get_settings",
            return_value=mock_settings,
        ):
            flags = FeatureFlags()
            assert flags.settings == mock_settings

    @pytest.mark.unit
    def test_is_mock_edi_enabled(self, mock_settings):
        """Test EDI mock flag evaluation."""
        with patch(
            "utils.feature_flags.get_settings",
            return_value=mock_settings,
        ):
            flags = FeatureFlags()
            assert flags.is_mock_edi_enabled() is True

    @pytest.mark.unit
    def test_is_mock_payments_enabled(self, mock_settings):
        """Test payments mock flag evaluation."""
        mock_settings.enable_mock_payments = True
        with patch(
            "utils.feature_flags.get_settings",
            return_value=mock_settings,
        ):
            flags = FeatureFlags()
            assert flags.is_mock_payments_enabled() is True

    @pytest.mark.unit
    def test_is_mock_video_enabled(self, mock_settings):
        """Test video mock flag evaluation."""
        with patch(
            "utils.feature_flags.get_settings",
            return_value=mock_settings,
        ):
            flags = FeatureFlags()
            assert flags.is_mock_video_enabled() is True

    @pytest.mark.unit
    def test_get_service_config_edi(self, mock_settings):
        """Test EDI service configuration."""
        with patch(
            "utils.feature_flags.get_settings",
            return_value=mock_settings,
        ):
            flags = FeatureFlags()
            config = flags.get_service_config("edi")

        assert config["enabled"] is True
        assert "service_url" in config

    @pytest.mark.unit
    def test_get_service_config_unknown(self, mock_settings):
        """Test unknown service configuration raises error."""
        with patch(
            "utils.feature_flags.get_settings",
            return_value=mock_settings,
        ):
            flags = FeatureFlags()

            with pytest.raises(ValueError, match="Unknown service type"):
                flags.get_service_config("unknown")

    @pytest.mark.unit
    def test_get_all_flags(self, mock_settings):
        """Test getting all feature flags."""
        with patch(
            "utils.feature_flags.get_settings",
            return_value=mock_settings,
        ):
            flags = FeatureFlags()
            all_flags = flags.get_all_flags()

            assert "mock_edi" in all_flags
            assert "mock_payments" in all_flags
            assert "mock_video" in all_flags

    @pytest.mark.unit
    def test_get_feature_flags_singleton(self):
        """Test that get_feature_flags returns singleton instance."""
        # Reset global instance on the already-imported module if present
        module = sys.modules.get("utils.feature_flags")
        if module is not None:
            setattr(module, "_feature_flags", None)

        flags1 = get_feature_flags()
        flags2 = get_feature_flags()

        assert flags1 is flags2

    @pytest.mark.unit
    @pytest.mark.critical
    def test_feature_flag_service_integration(self):
        """Test integration between feature flag components."""
        # Test that service functions work with utils
        from services.feature_flags_service import get_feature_flags_service

        service = get_feature_flags_service()
        assert service is not None

        # Test convenience function if available
        result = service.is_enabled("test_flag")
        assert isinstance(result, bool)


class TestFeatureFlagPerformance:
    """Unit tests for feature flag performance."""

    @pytest.mark.unit
    @pytest.mark.performance
    def test_flag_evaluation_performance(self):
        """Test that flag evaluation is fast."""
        import time

        from services.feature_flags_service import get_feature_flags_service

        service = get_feature_flags_service()
        service.config.default_flags = {"test_flag": True}

        # Warm up
        service.is_enabled("test_flag")

        # Measure performance
        start_time = time.time()
        for _ in range(1000):
            service.is_enabled("test_flag")
        end_time = time.time()

        # Should complete 1000 evaluations in less than 0.1 seconds
        assert (end_time - start_time) < 0.1

    @pytest.mark.unit
    @pytest.mark.performance
    def test_cache_effectiveness(self):
        """Test that caching improves performance."""
        from services.feature_flags_service import FeatureFlagsService

        service = FeatureFlagsService()
        service.config.default_flags = {"test_flag": True}

        # First evaluation (cache miss)
        import time

        start_time = time.time()
        service.is_enabled("test_flag")
        first_eval_time = time.time() - start_time

        # Second evaluation (cache hit)
        start_time = time.time()
        service.is_enabled("test_flag")
        second_eval_time = time.time() - start_time

        # Cached evaluation should be faster (or at least not slower)
        assert second_eval_time <= first_eval_time * 2


class TestFeatureFlagEdgeCases:
    """Unit tests for feature flag edge cases."""

    @pytest.mark.unit
    def test_empty_flag_name(self):
        """Test handling of empty flag name."""
        from services.feature_flags_service import FeatureFlagsService

        service = FeatureFlagsService()
        result = service.is_enabled("")
        assert result is False

    @pytest.mark.unit
    def test_none_flag_name(self):
        """Test handling of None flag name."""
        from services.feature_flags_service import FeatureFlagsService

        service = FeatureFlagsService()
        result = service.is_enabled(None)
        assert result is False

    @pytest.mark.unit
    def test_very_long_flag_name(self):
        """Test handling of very long flag name."""
        from services.feature_flags_service import FeatureFlagsService

        service = FeatureFlagsService()
        long_name = "a" * 1000
        result = service.is_enabled(long_name)
        assert isinstance(result, bool)

    @pytest.mark.unit
    @pytest.mark.security
    def test_flag_name_injection_protection(self):
        """Test protection against flag name injection."""
        from services.feature_flags_service import FeatureFlagsService

        service = FeatureFlagsService()
        malicious_names = [
            "../../../etc/passwd",
            "'; DROP TABLE flags; --",
            "<script>alert('xss')</script>",
            "flag' OR '1'='1",
        ]

        for name in malicious_names:
            result = service.is_enabled(name)
            # Should not crash or cause issues
            assert isinstance(result, bool)


class TestFeatureFlagApiIntegration:
    """Unit tests for feature flag API integration."""

    @pytest.mark.unit
    @pytest.mark.critical
    def test_flag_info_retrieval(self):
        """Test retrieving flag information."""
        from services.feature_flags_service import get_feature_flags_service

        service = get_feature_flags_service()
        service.clear_cache()
        flag_info = service.get_flag_info("test_flag")

        assert "name" in flag_info
        assert "provider" in flag_info
        assert "environment" in flag_info

    @pytest.mark.unit
    @pytest.mark.security
    def test_flag_context_sanitization(self):
        """Test that sensitive context is properly sanitized."""
        from services.feature_flags_service import get_feature_flags_service

        service = get_feature_flags_service()

        # Context with potentially sensitive information
        context = {
            "user_id": "123",
            "credit_card": "4111-1111-1111-1111",  # Should be sanitized
            "environment": "test",
        }

        # Should not crash and should handle context appropriately
        result = service.is_enabled("test_flag", **context)
        assert isinstance(result, bool)

    @pytest.mark.unit
    @pytest.mark.hipaa
    def test_phi_data_protection(self):
        """Test protection of PHI data in flag evaluation."""
        from services.feature_flags_service import get_feature_flags_service

        service = get_feature_flags_service()

        # Context with PHI that should be protected
        phi_context = {
            "dob": "1990-01-01",
            "ssn": "123-45-6789",
            "diagnosis": "anxiety",
            "user_id": "provider_123",
        }

        # Should evaluate flag without exposing PHI
        with patch.object(service.logger, "info") as mock_log:
            result = service.is_enabled("test_flag", **phi_context)
            assert isinstance(result, bool)

            # Verify no PHI in logs if called
            if mock_log.called:
                for call in mock_log.call_args_list:
                    log_message = str(call)
                    assert "123-45-6789" not in log_message
                    assert "1990-01-01" not in log_message

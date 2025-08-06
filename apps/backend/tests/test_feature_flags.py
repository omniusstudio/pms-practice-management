"""Tests for Feature Flags utility."""

from unittest.mock import MagicMock, patch

import pytest

from utils.feature_flags import FeatureFlags, get_feature_flags


class TestFeatureFlags:
    """Test cases for FeatureFlags class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.enable_mock_edi = True
        settings.enable_mock_payments = False
        settings.enable_mock_video = True
        settings.edi_service_url = "https://edi.example.com"
        settings.stripe_api_key = "sk_test_123"
        settings.stripe_webhook_secret = "whsec_123"
        settings.video_service_url = "https://video.example.com"
        settings.video_api_key = "video_key_123"
        return settings

    @pytest.fixture
    def feature_flags(self, mock_settings):
        """Create FeatureFlags instance with mock settings."""
        with patch("utils.feature_flags.get_settings", return_value=mock_settings):
            return FeatureFlags()

    def test_initialization(self, feature_flags, mock_settings):
        """Test FeatureFlags initialization."""
        assert feature_flags.settings == mock_settings

    def test_is_mock_edi_enabled_true(self, feature_flags):
        """Test EDI mock flag when enabled."""
        assert feature_flags.is_mock_edi_enabled() is True

    def test_is_mock_edi_enabled_false(self, mock_settings):
        """Test EDI mock flag when disabled."""
        mock_settings.enable_mock_edi = False
        with patch("utils.feature_flags.get_settings", return_value=mock_settings):
            flags = FeatureFlags()
            assert flags.is_mock_edi_enabled() is False

    def test_is_mock_payments_enabled_false(self, feature_flags):
        """Test payments mock flag when disabled."""
        assert feature_flags.is_mock_payments_enabled() is False

    def test_is_mock_payments_enabled_true(self, mock_settings):
        """Test payments mock flag when enabled."""
        mock_settings.enable_mock_payments = True
        with patch("utils.feature_flags.get_settings", return_value=mock_settings):
            flags = FeatureFlags()
            assert flags.is_mock_payments_enabled() is True

    def test_is_mock_video_enabled_true(self, feature_flags):
        """Test video mock flag when enabled."""
        assert feature_flags.is_mock_video_enabled() is True

    def test_is_mock_video_enabled_false(self, mock_settings):
        """Test video mock flag when disabled."""
        mock_settings.enable_mock_video = False
        with patch("utils.feature_flags.get_settings", return_value=mock_settings):
            flags = FeatureFlags()
            assert flags.is_mock_video_enabled() is False

    def test_get_service_config_edi(self, feature_flags):
        """Test EDI service configuration."""
        config = feature_flags.get_service_config("edi")

        expected = {
            "enabled": True,
            "service_url": "https://edi.example.com",
            "mock_endpoint": "/mock/edi",
        }

        assert config == expected

    def test_get_service_config_payments(self, feature_flags):
        """Test payments service configuration."""
        config = feature_flags.get_service_config("payments")

        expected = {
            "enabled": False,
            "api_key": "sk_test_123",
            "webhook_secret": "whsec_123",
            "mock_endpoint": "/mock/payments",
        }

        assert config == expected

    def test_get_service_config_video(self, feature_flags):
        """Test video service configuration."""
        config = feature_flags.get_service_config("video")

        expected = {
            "enabled": True,
            "service_url": "https://video.example.com",
            "api_key": "video_key_123",
            "mock_endpoint": "/mock/video",
        }

        assert config == expected

    def test_get_service_config_unknown_service(self, feature_flags):
        """Test service configuration with unknown service type."""
        with pytest.raises(ValueError, match="Unknown service type: unknown"):
            feature_flags.get_service_config("unknown")

    def test_get_all_flags(self, feature_flags):
        """Test getting all feature flags."""
        flags = feature_flags.get_all_flags()

        expected = {
            "mock_edi": True,
            "mock_payments": False,
            "mock_video": True,
        }

        assert flags == expected


class TestGlobalFeatureFlags:
    """Test cases for global feature flags functions."""

    def test_get_feature_flags_singleton(self):
        """Test that get_feature_flags returns singleton instance."""
        # Clear any existing global instance
        import utils.feature_flags

        utils.feature_flags._feature_flags = None

        flags1 = get_feature_flags()
        flags2 = get_feature_flags()

        assert flags1 is flags2
        assert isinstance(flags1, FeatureFlags)

    def test_get_feature_flags_creates_instance(self):
        """Test that get_feature_flags creates instance when none exists."""
        # Clear any existing global instance
        import utils.feature_flags

        utils.feature_flags._feature_flags = None

        flags = get_feature_flags()

        assert isinstance(flags, FeatureFlags)
        assert utils.feature_flags._feature_flags is flags

    def test_get_feature_flags_reuses_existing(self):
        """Test that get_feature_flags reuses existing instance."""
        # Set up existing instance
        import utils.feature_flags

        existing_flags = FeatureFlags()
        utils.feature_flags._feature_flags = existing_flags

        flags = get_feature_flags()

        assert flags is existing_flags

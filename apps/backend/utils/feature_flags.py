"""Feature flag utilities for toggling between mock and real services."""

from typing import Any, Dict, Optional

from core.config import get_settings


class FeatureFlags:
    """Centralized feature flag management."""

    def __init__(self):
        """Initialize with current settings."""
        self.settings = get_settings()

    def is_mock_edi_enabled(self) -> bool:
        """Check if mock EDI service is enabled."""
        return self.settings.enable_mock_edi

    def is_mock_payments_enabled(self) -> bool:
        """Check if mock payment service is enabled."""
        return self.settings.enable_mock_payments

    def is_mock_video_enabled(self) -> bool:
        """Check if mock video service is enabled."""
        return self.settings.enable_mock_video

    def get_service_config(self, service_type: str) -> Dict[str, Any]:
        """Get configuration for a specific service type.

        Args:
            service_type: One of 'edi', 'payments', 'video'

        Returns:
            Dictionary containing service configuration
        """
        if service_type == "edi":
            return {
                "enabled": self.is_mock_edi_enabled(),
                "service_url": self.settings.edi_service_url,
                "mock_endpoint": "/mock/edi",
            }
        elif service_type == "payments":
            return {
                "enabled": self.is_mock_payments_enabled(),
                "api_key": self.settings.stripe_api_key,
                "webhook_secret": self.settings.stripe_webhook_secret,
                "mock_endpoint": "/mock/payments",
            }
        elif service_type == "video":
            return {
                "enabled": self.is_mock_video_enabled(),
                "service_url": self.settings.video_service_url,
                "api_key": self.settings.video_api_key,
                "mock_endpoint": "/mock/video",
            }
        else:
            raise ValueError(f"Unknown service type: {service_type}")

    def get_all_flags(self) -> Dict[str, bool]:
        """Get all feature flags as a dictionary."""
        return {
            "mock_edi": self.is_mock_edi_enabled(),
            "mock_payments": self.is_mock_payments_enabled(),
            "mock_video": self.is_mock_video_enabled(),
        }


# Global feature flags instance
_feature_flags: Optional[FeatureFlags] = None


def get_feature_flags() -> FeatureFlags:
    """Get the global feature flags instance."""
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = FeatureFlags()
    return _feature_flags

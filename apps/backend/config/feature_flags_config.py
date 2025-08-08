"""Feature flags configuration for the PMS backend application."""

import os
from enum import Enum
from typing import Any, Dict, Optional


class FeatureFlagEnvironment(str, Enum):
    """Supported environments for feature flags."""

    TEST = "test"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    DEMO = "demo"


class FeatureFlagsConfig:
    """Feature flags configuration settings."""

    def __init__(self):
        """Initialize feature flags configuration from environment."""
        # Environment configuration
        self.environment = os.getenv("ENVIRONMENT", "development")

        # Feature flag provider configuration
        # Supported providers: local, launchdarkly, etc.
        self.provider = os.getenv("FEATURE_FLAGS_PROVIDER", "local")

        # LaunchDarkly configuration (if using external provider)
        self.launchdarkly_sdk_key = os.getenv("LAUNCHDARKLY_SDK_KEY", "")

        # Local feature flags configuration
        self.local_flags_file = os.getenv(
            "FEATURE_FLAGS_FILE", "/app/config/feature_flags.json"
        )

        # Default feature flags (fallback values)
        self.default_flags = {
            # Kill-switch flags for risky features
            "video_calls_enabled": self._get_default_flag_value(
                "video_calls_enabled", False
            ),
            "edi_integration_enabled": self._get_default_flag_value(
                "edi_integration_enabled", False
            ),
            "payments_enabled": self._get_default_flag_value("payments_enabled", False),
            # Feature flags for new functionality
            "advanced_reporting_enabled": self._get_default_flag_value(
                "advanced_reporting_enabled", True
            ),
            "audit_trail_enhanced": self._get_default_flag_value(
                "audit_trail_enhanced", True
            ),
            "multi_practice_support": self._get_default_flag_value(
                "multi_practice_support", False
            ),
            # Performance and optimization flags
            "database_query_optimization": self._get_default_flag_value(
                "database_query_optimization", True
            ),
            "caching_enabled": self._get_default_flag_value("caching_enabled", True),
            # Security flags
            "enhanced_encryption": self._get_default_flag_value(
                "enhanced_encryption", True
            ),
            "two_factor_auth_required": self._get_default_flag_value(
                "two_factor_auth_required", False
            ),
        }

        # Logging configuration
        self.enable_flag_evaluation_logging = (
            os.getenv("ENABLE_FLAG_EVALUATION_LOGGING", "true").lower() == "true"
        )

        # Metrics configuration
        self.enable_flag_metrics = (
            os.getenv("ENABLE_FLAG_METRICS", "true").lower() == "true"
        )

        # Cache configuration
        self.flag_cache_ttl_seconds = int(
            os.getenv("FLAG_CACHE_TTL_SECONDS", "300")  # 5 minutes
        )

        # Validate configuration
        self._validate_configuration()

    def _get_default_flag_value(self, flag_name: str, default: bool) -> bool:
        """Get default flag value from environment or use provided default."""
        env_var = f"FEATURE_FLAG_{flag_name.upper()}"
        env_value = os.getenv(env_var)

        if env_value is not None:
            return env_value.lower() in ("true", "1", "yes", "on")

        return default

    def _validate_configuration(self) -> None:
        """Validate feature flags configuration."""
        if self.provider == "launchdarkly" and not self.launchdarkly_sdk_key:
            raise ValueError(
                "LaunchDarkly SDK key is required when using " "LaunchDarkly provider"
            )

        valid_envs = [env.value for env in FeatureFlagEnvironment]
        if self.environment not in valid_envs:
            raise ValueError(
                f"Invalid environment: {self.environment}. "
                f"Must be one of: {valid_envs}"
            )

    def get_flag_context(
        self, user_id: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """Get context for feature flag evaluation."""
        context = {
            "environment": self.environment,
            "timestamp": kwargs.get("timestamp"),
        }

        if user_id:
            context["user_id"] = user_id

        # Add any additional context
        context.update(kwargs)

        return context


# Global configuration instance
feature_flags_config = None


def get_feature_flags_config() -> FeatureFlagsConfig:
    """Get the global feature flags configuration instance."""
    global feature_flags_config
    if feature_flags_config is None:
        feature_flags_config = FeatureFlagsConfig()
    return feature_flags_config

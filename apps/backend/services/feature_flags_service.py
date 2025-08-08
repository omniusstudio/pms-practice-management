"""Feature flags service for the PMS backend application."""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from prometheus_client import Counter, Histogram

from config.feature_flags_config import FeatureFlagsConfig, get_feature_flags_config

# Prometheus metrics for feature flag evaluations
FLAG_EVALUATIONS = Counter(
    "feature_flag_evaluations_total",
    "Total number of feature flag evaluations",
    ["flag_name", "environment", "result"],
)

FLAG_EVALUATION_DURATION = Histogram(
    "feature_flag_evaluation_duration_seconds",
    "Time spent evaluating feature flags",
    ["flag_name", "environment"],
)

FLAG_CACHE_HITS = Counter(
    "feature_flag_cache_hits_total",
    "Total number of feature flag cache hits",
    ["flag_name"],
)

FLAG_CACHE_MISSES = Counter(
    "feature_flag_cache_misses_total",
    "Total number of feature flag cache misses",
    ["flag_name"],
)


class FeatureFlagsService:
    """Service for managing and evaluating feature flags."""

    def __init__(self, config: Optional[FeatureFlagsConfig] = None):
        """Initialize the feature flags service."""
        self.config = config or get_feature_flags_config()
        self.logger = structlog.get_logger(__name__)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, float] = {}

        # Initialize flags from configuration
        self._initialize_flags()

    def _initialize_flags(self) -> None:
        """Initialize feature flags from configuration sources."""
        try:
            if self.config.provider == "local":
                self._load_local_flags()
            elif self.config.provider == "launchdarkly":
                self._initialize_launchdarkly()
            else:
                self.logger.warning(
                    "Unknown feature flag provider, using defaults",
                    provider=self.config.provider,
                )

            self.logger.info(
                "Feature flags service initialized",
                provider=self.config.provider,
                environment=self.config.environment,
                flags_count=len(self.config.default_flags),
            )
        except Exception as e:
            self.logger.error(
                "Failed to initialize feature flags service",
                error=str(e),
                provider=self.config.provider,
            )
            # Fall back to default flags

    def _load_local_flags(self) -> None:
        """Load feature flags from local JSON file."""
        try:
            flags_file = Path(self.config.local_flags_file)
            if flags_file.exists():
                with open(flags_file, "r") as f:
                    local_flags = json.load(f)

                # Merge with default flags
                env_flags = local_flags.get(self.config.environment, {})
                self.config.default_flags.update(env_flags)

                self.logger.info(
                    "Loaded local feature flags",
                    file_path=str(flags_file),
                    environment=self.config.environment,
                    flags_loaded=len(env_flags),
                )
            else:
                self.logger.info(
                    "Local flags file not found, using defaults",
                    file_path=str(flags_file),
                )
        except Exception as e:
            self.logger.error(
                "Failed to load local feature flags",
                error=str(e),
                file_path=self.config.local_flags_file,
            )

    def _initialize_launchdarkly(self) -> None:
        """Initialize LaunchDarkly SDK (placeholder for future implementation)."""
        # This would initialize LaunchDarkly SDK in a real implementation
        self.logger.info(
            "LaunchDarkly provider configured",
            sdk_key_configured=bool(self.config.launchdarkly_sdk_key),
        )

    def is_enabled(
        self,
        flag_name: str,
        user_id: Optional[str] = None,
        default: bool = False,
        **context,
    ) -> bool:
        """Check if a feature flag is enabled.

        Args:
            flag_name: Name of the feature flag
            user_id: Optional user ID for user-specific flags
            default: Default value if flag is not found
            **context: Additional context for flag evaluation

        Returns:
            Boolean indicating if the flag is enabled
        """
        start_time = time.time()

        try:
            # Check cache first
            cached_value = self._get_cached_flag(flag_name, user_id)
            if cached_value is not None:
                if self.config.enable_flag_metrics:
                    FLAG_CACHE_HITS.labels(flag_name=flag_name).inc()
                return cached_value

            if self.config.enable_flag_metrics:
                FLAG_CACHE_MISSES.labels(flag_name=flag_name).inc()

            # Evaluate flag
            result = self._evaluate_flag(flag_name, user_id, default, **context)

            # Cache the result
            self._cache_flag_result(flag_name, user_id, result)

            # Log evaluation if enabled
            if self.config.enable_flag_evaluation_logging:
                self._log_flag_evaluation(flag_name, result, user_id, context)

            # Record metrics
            if self.config.enable_flag_metrics:
                FLAG_EVALUATIONS.labels(
                    flag_name=flag_name,
                    environment=self.config.environment,
                    result=str(result),
                ).inc()

                FLAG_EVALUATION_DURATION.labels(
                    flag_name=flag_name, environment=self.config.environment
                ).observe(time.time() - start_time)

            return result

        except Exception as e:
            self.logger.error(
                "Error evaluating feature flag",
                flag_name=flag_name,
                user_id=user_id,
                error=str(e),
            )
            return default

    def _evaluate_flag(
        self, flag_name: str, user_id: Optional[str], default: bool, **context
    ) -> bool:
        """Evaluate a feature flag based on the configured provider."""
        if self.config.provider == "local":
            return self._evaluate_local_flag(flag_name, default)
        elif self.config.provider == "launchdarkly":
            return self._evaluate_launchdarkly_flag(
                flag_name, user_id, default, **context
            )
        else:
            return default

    def _evaluate_local_flag(self, flag_name: str, default: bool) -> bool:
        """Evaluate a local feature flag."""
        return self.config.default_flags.get(flag_name, default)

    def _evaluate_launchdarkly_flag(
        self, flag_name: str, user_id: Optional[str], default: bool, **context
    ) -> bool:
        """Evaluate a LaunchDarkly feature flag (placeholder)."""
        # This would use LaunchDarkly SDK in a real implementation
        self.logger.debug(
            "LaunchDarkly flag evaluation (placeholder)",
            flag_name=flag_name,
            user_id=user_id,
        )
        return self.config.default_flags.get(flag_name, default)

    def _get_cached_flag(
        self, flag_name: str, user_id: Optional[str]
    ) -> Optional[bool]:
        """Get cached flag value if still valid."""
        cache_key = self._get_cache_key(flag_name, user_id)

        if cache_key not in self._cache:
            return None

        # Check if cache is still valid
        cache_time = self._cache_timestamps.get(cache_key, 0)
        if time.time() - cache_time > self.config.flag_cache_ttl_seconds:
            # Cache expired
            self._cache.pop(cache_key, None)
            self._cache_timestamps.pop(cache_key, None)
            return None

        return self._cache[cache_key].get("value")

    def _cache_flag_result(
        self, flag_name: str, user_id: Optional[str], result: bool
    ) -> None:
        """Cache flag evaluation result."""
        cache_key = self._get_cache_key(flag_name, user_id)
        self._cache[cache_key] = {"value": result}
        self._cache_timestamps[cache_key] = time.time()

    def _get_cache_key(self, flag_name: str, user_id: Optional[str]) -> str:
        """Generate cache key for flag and user combination."""
        if user_id:
            return f"{flag_name}:{user_id}"
        return flag_name

    def _log_flag_evaluation(
        self,
        flag_name: str,
        result: bool,
        user_id: Optional[str],
        context: Dict[str, Any],
    ) -> None:
        """Log feature flag evaluation (without PHI)."""
        # Scrub any potential PHI from context
        safe_context = self._scrub_phi_from_context(context)

        self.logger.info(
            "Feature flag evaluated",
            flag_name=flag_name,
            result=result,
            user_id_hash=self._hash_user_id(user_id) if user_id else None,
            environment=self.config.environment,
            context=safe_context,
        )

    def _scrub_phi_from_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Remove potential PHI from context before logging."""
        # List of keys that might contain PHI
        phi_keys = {
            "email",
            "phone",
            "ssn",
            "patient_id",
            "medical_record_number",
            "first_name",
            "last_name",
            "full_name",
            "address",
            "dob",
            "date_of_birth",
            "diagnosis",
            "treatment",
        }

        safe_context = {}
        for key, value in context.items():
            if key.lower() in phi_keys:
                safe_context[key] = "[SCRUBBED]"
            else:
                safe_context[key] = value

        return safe_context

    def _hash_user_id(self, user_id: str) -> str:
        """Hash user ID for logging (to avoid logging actual user IDs)."""
        import hashlib

        return hashlib.sha256(user_id.encode()).hexdigest()[:8]

    def get_all_flags(
        self, user_id: Optional[str] = None, **context
    ) -> Dict[str, bool]:
        """Get all feature flags for a user/context."""
        flags = {}
        for flag_name in self.config.default_flags.keys():
            flags[flag_name] = self.is_enabled(flag_name, user_id, **context)
        return flags

    def clear_cache(self) -> None:
        """Clear the feature flags cache."""
        self._cache.clear()
        self._cache_timestamps.clear()
        self.logger.info("Feature flags cache cleared")

    def get_flag_info(self, flag_name: str) -> Dict[str, Any]:
        """Get information about a specific flag."""
        return {
            "name": flag_name,
            "default_value": self.config.default_flags.get(flag_name),
            "provider": self.config.provider,
            "environment": self.config.environment,
            "cached": flag_name in [key.split(":")[0] for key in self._cache.keys()],
        }


# Global service instance
_feature_flags_service: Optional[FeatureFlagsService] = None


def get_feature_flags_service() -> FeatureFlagsService:
    """Get the global feature flags service instance."""
    global _feature_flags_service
    if _feature_flags_service is None:
        _feature_flags_service = FeatureFlagsService()
    return _feature_flags_service


# Convenience functions for common usage patterns
def is_enabled(
    flag_name: str, user_id: Optional[str] = None, default: bool = False, **context
) -> bool:
    """Check if a feature flag is enabled (convenience function)."""
    return get_feature_flags_service().is_enabled(
        flag_name, user_id, default, **context
    )


def is_video_calls_enabled(user_id: Optional[str] = None) -> bool:
    """Check if video calls feature is enabled (kill-switch)."""
    return is_enabled("video_calls_enabled", user_id, default=False)


def is_edi_integration_enabled(user_id: Optional[str] = None) -> bool:
    """Check if EDI integration feature is enabled (kill-switch)."""
    return is_enabled("edi_integration_enabled", user_id, default=False)


def is_payments_enabled(user_id: Optional[str] = None) -> bool:
    """Check if payments feature is enabled (kill-switch)."""
    return is_enabled("payments_enabled", user_id, default=False)


def is_appointments_enabled(user_id: Optional[str] = None) -> bool:
    """Check if appointments feature is enabled."""
    return is_enabled("appointments_enabled", user_id, default=True)


def is_telehealth_appointments_enabled(user_id: Optional[str] = None) -> bool:
    """Check if telehealth appointments feature is enabled."""
    return is_enabled("telehealth_appointments_enabled", user_id, default=False)


def is_patient_management_enabled(user_id: Optional[str] = None) -> bool:
    """Check if patient management feature is enabled."""
    return is_enabled("patient_management_enabled", user_id, default=True)


def is_provider_management_enabled(user_id: Optional[str] = None) -> bool:
    """Check if provider management feature is enabled."""
    return is_enabled("provider_management_enabled", user_id, default=True)


def is_clinical_notes_enabled(user_id: Optional[str] = None) -> bool:
    """Check if clinical notes feature is enabled."""
    return is_enabled("clinical_notes_enabled", user_id, default=True)


def is_note_signing_enabled(user_id: Optional[str] = None) -> bool:
    """Check if note signing feature is enabled."""
    return is_enabled("note_signing_enabled", user_id, default=True)


def is_financial_ledger_enabled(user_id: Optional[str] = None) -> bool:
    """Check if financial ledger feature is enabled."""
    return is_enabled("financial_ledger_enabled", user_id, default=True)

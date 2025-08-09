#!/usr/bin/env python3
"""QA-specific seed data configuration for fast, HIPAA-compliant test data.

This module provides optimized configurations for QA environments that can:
- Seed fresh staging environments in under 5 minutes
- Generate comprehensive anonymized datasets
- Ensure zero PHI inclusion
- Support automated testing workflows
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class QAEnvironment(Enum):
    """QA environment types with different data requirements."""

    MINIMAL = "minimal"  # Smoke tests, basic functionality
    STANDARD = "standard"  # Full feature testing
    LOAD_TEST = "load_test"  # Performance and load testing
    INTEGRATION = "integration"  # Third-party integration testing


@dataclass
class QADataProfile:
    """Data profile configuration for QA environments."""

    name: str
    description: str
    target_seed_time_seconds: int
    record_counts: Dict[str, int]
    tenant_count: int
    enable_relationships: bool
    include_historical_data: bool
    validation_level: str  # 'basic', 'standard', 'comprehensive'


class QASeedConfig:
    """QA seed data configuration manager."""

    def __init__(self, environment: Optional[str] = None):
        """Initialize QA seed configuration.

        Args:
            environment: QA environment type (minimal, standard, load_test,
                        integration)
        """
        env_name = environment or os.getenv("QA_ENVIRONMENT", "standard")
        self.environment = QAEnvironment(env_name)
        self.profiles = self._initialize_profiles()
        self.current_profile = self.profiles[self.environment]

        # HIPAA compliance settings
        self.hipaa_safe_domains = [
            "example.com",
            "example.local",
            "test.local",
            "qa.local",
            "staging.local",
        ]

        self.safe_phone_prefixes = ["555", "800", "888", "877", "866"]

        # Performance optimization settings
        self.batch_size = int(os.getenv("QA_SEED_BATCH_SIZE", "100"))
        self.parallel_workers = int(os.getenv("QA_SEED_WORKERS", "4"))
        bulk_insert_env = os.getenv("QA_USE_BULK_INSERT", "true")
        self.use_bulk_insert = bulk_insert_env.lower() == "true"

        # Validation settings
        validation_env = os.getenv("QA_ENABLE_VALIDATION", "true")
        self.enable_data_validation = validation_env.lower() == "true"
        sample_size_env = os.getenv("QA_VALIDATION_SAMPLE_SIZE", "10")
        self.validation_sample_size = int(sample_size_env)

    def _initialize_profiles(self) -> Dict[QAEnvironment, QADataProfile]:
        """Initialize QA data profiles for different environments."""
        return {
            QAEnvironment.MINIMAL: QADataProfile(
                name="Minimal QA Dataset",
                description=(
                    "Minimal dataset for smoke tests and basic " "functionality"
                ),
                target_seed_time_seconds=60,  # 1 minute
                record_counts={
                    "practice_profiles": 1,
                    "locations": 2,
                    "Client": 5,
                    "Provider": 2,
                    "appointments": 10,
                    "notes": 15,
                    "ledger_entries": 20,
                    "auth_tokens": 5,
                    "encryption_keys": 3,
                    "fhir_mappings": 10,
                },
                tenant_count=1,
                enable_relationships=True,
                include_historical_data=False,
                validation_level="basic",
            ),
            QAEnvironment.STANDARD: QADataProfile(
                name="Standard QA Dataset",
                description="Comprehensive dataset for full feature testing",
                target_seed_time_seconds=180,  # 3 minutes
                record_counts={
                    "practice_profiles": 3,
                    "locations": 8,
                    "Client": 100,
                    "Provider": 20,
                    "appointments": 200,
                    "notes": 300,
                    "ledger_entries": 400,
                    "auth_tokens": 30,
                    "encryption_keys": 15,
                    "fhir_mappings": 200,
                },
                tenant_count=3,
                enable_relationships=True,
                include_historical_data=True,
                validation_level="standard",
            ),
            QAEnvironment.LOAD_TEST: QADataProfile(
                name="Load Test Dataset",
                description="Large dataset for performance and load testing",
                target_seed_time_seconds=300,  # 5 minutes
                record_counts={
                    "practice_profiles": 10,
                    "locations": 25,
                    "Client": 1000,
                    "Provider": 100,
                    "Appointment": 5000,
                    "appointments": 5000,
                    "notes": 3000,
                    "ledger_entries": 4000,
                    "auth_tokens": 200,
                    "encryption_keys": 50,
                    "fhir_mappings": 1500,
                },
                tenant_count=10,
                enable_relationships=True,
                include_historical_data=True,
                validation_level="comprehensive",
            ),
            QAEnvironment.INTEGRATION: QADataProfile(
                name="Integration Test Dataset",
                description=(
                    "Specialized dataset for third-party " "integration testing"
                ),
                target_seed_time_seconds=240,  # 4 minutes
                record_counts={
                    "practice_profiles": 5,
                    "locations": 12,
                    "Client": 100,
                    "Provider": 20,
                    "appointments": 200,
                    "notes": 300,
                    "ledger_entries": 400,
                    "auth_tokens": 30,
                    "encryption_keys": 15,
                    # More FHIR mappings for integration testing
                    "fhir_mappings": 500,
                },
                tenant_count=5,
                enable_relationships=True,
                include_historical_data=True,
                validation_level="comprehensive",
            ),
        }

    def get_tenant_ids(self) -> List[str]:
        """Generate tenant IDs for the current profile."""
        tenant_count = self.current_profile.tenant_count
        return [f"qa_tenant_{i:03d}" for i in range(1, tenant_count + 1)]

    def get_record_counts(self) -> Dict[str, int]:
        """Get record counts for the current profile."""
        return self.current_profile.record_counts.copy()

    def get_performance_settings(self) -> Dict[str, Any]:
        """Get performance optimization settings."""
        return {
            "batch_size": self.batch_size,
            "parallel_workers": self.parallel_workers,
            "use_bulk_insert": self.use_bulk_insert,
            "target_time_seconds": (self.current_profile.target_seed_time_seconds),
        }

    def get_validation_settings(self) -> Dict[str, Any]:
        """Get data validation settings."""
        # Environment-specific sample sizes
        environment_sample_sizes = {
            QAEnvironment.MINIMAL: 25,
            QAEnvironment.STANDARD: 50,
            QAEnvironment.LOAD_TEST: 150,
            QAEnvironment.INTEGRATION: 75,
        }

        # Use environment-specific size or fallback to configured size
        sample_size = environment_sample_sizes.get(
            self.environment, self.validation_sample_size
        )

        return {
            "enabled": self.enable_data_validation,
            "level": self.current_profile.validation_level,
            "sample_size": sample_size,
            "strict_mode": self.current_profile.validation_level == "strict",
        }

    def get_hipaa_compliance_settings(self) -> Dict[str, Any]:
        """Get HIPAA compliance settings."""
        return {
            "safe_domains": self.hipaa_safe_domains,
            "safe_phone_prefixes": self.safe_phone_prefixes,
            "prohibited_fields": [
                "ssn",
                "social_security",
                "real_name",
                "actual_email",
                "real_phone",
                "actual_address",
                "medical_record_number",
            ],
        }

    def should_include_historical_data(self) -> bool:
        """Check if historical data should be included."""
        return self.current_profile.include_historical_data

    def get_summary(self) -> Dict[str, Any]:
        """Get configuration summary for logging."""
        return {
            "environment": self.environment.value,
            "profile_name": self.current_profile.name,
            "target_seed_time": self.current_profile.target_seed_time_seconds,
            "total_records": sum(self.current_profile.record_counts.values()),
            "tenant_count": self.current_profile.tenant_count,
            "validation_level": self.current_profile.validation_level,
        }


# Global configuration instance
_qa_config = None


def get_qa_seed_config(environment: Optional[str] = None) -> QASeedConfig:
    """Get the global QA seed configuration instance."""
    global _qa_config
    if _qa_config is None or environment:
        _qa_config = QASeedConfig(environment)
    return _qa_config


# Convenience functions
def get_current_environment() -> QAEnvironment:
    """Get the current QA environment."""
    return get_qa_seed_config().environment


def get_target_seed_time() -> int:
    """Get target seed time in seconds for current environment."""
    return get_qa_seed_config().current_profile.target_seed_time_seconds


def is_fast_mode() -> bool:
    """Check if we're in fast seeding mode (minimal or under 3 min)."""
    return get_target_seed_time() <= 180

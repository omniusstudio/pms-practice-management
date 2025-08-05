"""Centralized PHI scrubbing configuration for HIPAA."""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PHICategory(Enum):
    """Categories of PHI for different scrubbing levels."""

    IDENTIFIERS = "identifiers"  # SSN, MRN, etc.
    CONTACT = "contact"  # Email, phone, address
    DEMOGRAPHIC = "demographic"  # Names, DOB
    FINANCIAL = "financial"  # Insurance, payment info
    MEDICAL = "medical"  # Diagnoses, treatments
    CUSTOM = "custom"  # Organization-specific patterns


@dataclass
class PHIPattern:
    """PHI pattern configuration."""

    name: str
    pattern: str
    replacement: str
    category: PHICategory
    enabled: bool = True
    environment_specific: bool = False
    description: str = ""


class PHIConfig:
    """Centralized PHI scrubbing configuration manager."""

    def __init__(self, environment: Optional[str] = None):
        """Initialize PHI configuration.

        Args:
            environment: Deployment environment (dev, staging, production)
        """
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self._patterns = self._load_patterns()

    def _load_patterns(self) -> Dict[str, PHIPattern]:
        """Load PHI patterns based on environment.

        Returns:
            Dictionary of PHI patterns keyed by name
        """
        # Base patterns that apply to all environments
        base_patterns = {
            "ssn_dashed": PHIPattern(
                name="ssn_dashed",
                pattern=r"\d{3}-\d{2}-\d{4}",
                replacement="[SSN-REDACTED]",
                category=PHICategory.IDENTIFIERS,
                description="Social Security Number with dashes",
            ),
            "ssn_plain": PHIPattern(
                name="ssn_plain",
                pattern=r"\b\d{9}\b",
                replacement="[SSN-REDACTED]",
                category=PHICategory.IDENTIFIERS,
                description="Social Security Number without formatting",
            ),
            "email": PHIPattern(
                name="email",
                pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                replacement="[EMAIL-REDACTED]",
                category=PHICategory.CONTACT,
                description="Email addresses",
            ),
            "phone_formatted": PHIPattern(
                name="phone_formatted",
                pattern=r"\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b",
                replacement="[PHONE-REDACTED]",
                category=PHICategory.CONTACT,
                description="Phone numbers with formatting",
            ),
            "credit_card": PHIPattern(
                name="credit_card",
                pattern=r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
                replacement="[CARD-REDACTED]",
                category=PHICategory.FINANCIAL,
                description="Credit card numbers",
            ),
            "mrn_formatted": PHIPattern(
                name="mrn_formatted",
                pattern=r"\bMRN[-:\s]*\d+\b",
                replacement="[MRN-REDACTED]",
                category=PHICategory.IDENTIFIERS,
                description="Medical Record Number with MRN prefix",
            ),
            "mr_formatted": PHIPattern(
                name="mr_formatted",
                pattern=r"\bMR[-:\s]*\d+\b",
                replacement="[MRN-REDACTED]",
                category=PHICategory.IDENTIFIERS,
                description="Medical Record Number with MR prefix",
            ),
            "dob_slashed": PHIPattern(
                name="dob_slashed",
                pattern=r"\b\d{1,2}/\d{1,2}/\d{4}\b",
                replacement="[DOB-REDACTED]",
                category=PHICategory.DEMOGRAPHIC,
                description="Date of birth in MM/DD/YYYY format",
            ),
            "dob_iso": PHIPattern(
                name="dob_iso",
                pattern=r"\b\d{4}-\d{2}-\d{2}\b",
                replacement="[DOB-REDACTED]",
                category=PHICategory.DEMOGRAPHIC,
                description="Date of birth in ISO format",
            ),
            "insurance_number": PHIPattern(
                name="insurance_number",
                pattern=r"\bINS[-:\s]*[A-Z0-9]+\b",
                replacement="[INSURANCE-REDACTED]",
                category=PHICategory.FINANCIAL,
                description="Insurance numbers",
            ),
        }

        # Add environment-specific patterns
        env_patterns = self._get_environment_patterns()
        base_patterns.update(env_patterns)

        return base_patterns

    def _get_environment_patterns(self) -> Dict[str, PHIPattern]:
        """Get environment-specific PHI patterns.

        Returns:
            Dictionary of environment-specific patterns
        """
        if self.environment == "development":
            return {
                "test_patient": PHIPattern(
                    name="test_patient",
                    pattern=r"\bTest Patient\b",
                    replacement="[TEST-PATIENT]",
                    category=PHICategory.DEMOGRAPHIC,
                    environment_specific=True,
                    description="Test patient names in development",
                ),
                "demo_email": PHIPattern(
                    name="demo_email",
                    pattern=r"\bdemo@example\.com\b",
                    replacement="[DEMO-EMAIL]",
                    category=PHICategory.CONTACT,
                    environment_specific=True,
                    description="Demo email addresses",
                ),
            }
        elif self.environment == "production":
            return {
                "strict_name": PHIPattern(
                    name="strict_name",
                    pattern=r"\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b",
                    replacement="[NAME-REDACTED]",
                    category=PHICategory.DEMOGRAPHIC,
                    environment_specific=True,
                    description="Strict name pattern for production",
                ),
                "patient_context": PHIPattern(
                    name="patient_context",
                    pattern=r"\bpatient[-_\s]+name[-:\s]*[A-Za-z\s]+\b",
                    replacement="[PATIENT-NAME-REDACTED]",
                    category=PHICategory.DEMOGRAPHIC,
                    environment_specific=True,
                    description="Patient names in context",
                ),
            }
        elif self.environment == "staging":
            return {
                "staging_data": PHIPattern(
                    name="staging_data",
                    pattern=r"\bSTAGING[-_\s]+\w+\b",
                    replacement="[STAGING-DATA]",
                    category=PHICategory.CUSTOM,
                    environment_specific=True,
                    description="Staging-specific data patterns",
                ),
            }

        return {}

    def get_active_patterns(
        self, category: Optional[PHICategory] = None
    ) -> List[Tuple[str, str]]:
        """Get active PHI patterns for scrubbing.

        Args:
            category: Optional category filter

        Returns:
            List of (pattern, replacement) tuples
        """
        patterns = []
        for pattern_config in self._patterns.values():
            if not pattern_config.enabled:
                continue
            if category and pattern_config.category != category:
                continue
            patterns.append((pattern_config.pattern, pattern_config.replacement))
        return patterns

    def get_pattern(self, name: str) -> Optional[PHIPattern]:
        """Get a specific PHI pattern by name.

        Args:
            name: Pattern name

        Returns:
            PHI pattern or None if not found
        """
        return self._patterns.get(name)

    def enable_pattern(self, name: str) -> bool:
        """Enable a PHI pattern.

        Args:
            name: Pattern name

        Returns:
            True if pattern was found and enabled
        """
        pattern = self._patterns.get(name)
        if pattern:
            pattern.enabled = True
            return True
        return False

    def disable_pattern(self, name: str) -> bool:
        """Disable a PHI pattern.

        Args:
            name: Pattern name

        Returns:
            True if pattern was found and disabled
        """
        pattern = self._patterns.get(name)
        if pattern:
            pattern.enabled = False
            return True
        return False

    def add_custom_pattern(
        self,
        name: str,
        pattern: str,
        replacement: str,
        category: PHICategory = PHICategory.CUSTOM,
        description: str = "",
    ) -> None:
        """Add a custom PHI pattern.

        Args:
            name: Pattern name
            pattern: Regular expression pattern
            replacement: Replacement text
            category: PHI category
            description: Pattern description
        """
        self._patterns[name] = PHIPattern(
            name=name,
            pattern=pattern,
            replacement=replacement,
            category=category,
            description=description,
        )

    def get_patterns_by_category(self, category: PHICategory) -> Dict[str, PHIPattern]:
        """Get all patterns for a specific category.

        Args:
            category: PHI category

        Returns:
            Dictionary of patterns in the category
        """
        return {
            name: pattern
            for name, pattern in self._patterns.items()
            if pattern.category == category and pattern.enabled
        }

    def validate_patterns(self) -> List[str]:
        """Validate all PHI patterns for regex correctness.

        Returns:
            List of validation error messages
        """
        import re

        errors = []

        for name, pattern_config in self._patterns.items():
            try:
                re.compile(pattern_config.pattern)
            except re.error as e:
                errors.append(f"Pattern '{name}': {e}")

        return errors

    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of the current PHI configuration.

        Returns:
            Configuration summary dictionary
        """
        summary: Dict[str, Any] = {
            "environment": self.environment,
            "total_patterns": len(self._patterns),
            "enabled_patterns": sum(1 for p in self._patterns.values() if p.enabled),
            "categories": {},
            "environment_specific": sum(
                1 for p in self._patterns.values() if p.environment_specific
            ),
        }

        # Count patterns by category
        for category in PHICategory:
            category_patterns = self.get_patterns_by_category(category)
            summary["categories"][category.value] = len(category_patterns)

        return summary


# Global PHI configuration instance
_phi_config: Optional[PHIConfig] = None


def get_phi_config() -> PHIConfig:
    """Get the global PHI configuration instance.

    Returns:
        PHI configuration instance
    """
    global _phi_config
    if _phi_config is None:
        _phi_config = PHIConfig()
    return _phi_config


def initialize_phi_config(environment: Optional[str] = None) -> PHIConfig:
    """Initialize the global PHI configuration.

    Args:
        environment: Deployment environment

    Returns:
        Initialized PHI configuration
    """
    global _phi_config
    _phi_config = PHIConfig(environment)
    return _phi_config

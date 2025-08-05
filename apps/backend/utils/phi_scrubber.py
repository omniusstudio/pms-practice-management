"""PHI scrubbing utilities for HIPAA compliance."""

import re
from typing import Any, Dict, List, Union

from config.phi_config import get_phi_config

# Legacy patterns for backward compatibility
PHI_PATTERNS = [
    # Social Security Numbers
    (r"\d{3}-\d{2}-\d{4}", "[SSN-REDACTED]"),
    (r"\b\d{9}\b", "[SSN-REDACTED]"),
    # Email addresses
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL-REDACTED]"),
    # Phone numbers
    (r"\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b", "[PHONE-REDACTED]"),
    # Credit card numbers
    (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[CARD-REDACTED]"),
    # Medical Record Numbers
    (r"\bMRN[-:\s]*\d+\b", "[MRN-REDACTED]"),
    (r"\bMR[-:\s]*\d+\b", "[MRN-REDACTED]"),
    # Dates of birth
    (r"\b\d{1,2}/\d{1,2}/\d{4}\b", "[DOB-REDACTED]"),
    (r"\b\d{4}-\d{2}-\d{2}\b", "[DOB-REDACTED]"),
    # Insurance numbers
    (r"\bINS[-:\s]*[A-Z0-9]+\b", "[INSURANCE-REDACTED]"),
    # Names and patient information
    (r"\bpatient[-_\s]+name[-:\s]*[A-Za-z\s]+\b", "[PATIENT-NAME-REDACTED]"),
    (r"\bfirst[-_\s]+name[-:\s]*[A-Za-z]+\b", "[FIRST-NAME-REDACTED]"),
    (r"\blast[-_\s]+name[-:\s]*[A-Za-z]+\b", "[LAST-NAME-REDACTED]"),
    # General name patterns
    (r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", "[NAME-REDACTED]"),
    (r"\bPatient\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b", "Patient [NAME-REDACTED]"),
    (r"\bDr\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b", "Dr. [NAME-REDACTED]"),
    (r"\bMr\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b", "Mr. [NAME-REDACTED]"),
    (r"\bMs\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b", "Ms. [NAME-REDACTED]"),
    (r"\bMrs\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b", "Mrs. [NAME-REDACTED]"),
]

# Sensitive field names that should be scrubbed
SENSITIVE_FIELDS = {
    "ssn",
    "social_security_number",
    "social_security",
    "email",
    "email_address",
    "user_email",
    "phone",
    "phone_number",
    "telephone",
    "first_name",
    "last_name",
    "full_name",
    "name",
    "patient_name",
    "date_of_birth",
    "dob",
    "birth_date",
    "address",
    "street_address",
    "home_address",
    "medical_record_number",
    "mrn",
    "patient_id",
    "insurance_number",
    "policy_number",
    "diagnosis",
    "medical_condition",
    "treatment",
    "prescription",
    "medication",
    "password",
    "token",
    "secret",
    "key",
}


def scrub_phi_from_string(text: str, use_centralized_config: bool = True) -> str:
    """Scrub PHI patterns from a string.

    Args:
        text: Input string that may contain PHI
        use_centralized_config: Whether to use centralized PHI config

    Returns:
        String with PHI patterns replaced with redacted placeholders
    """
    if not isinstance(text, str):
        return text

    scrubbed_text = text

    if use_centralized_config:
        # Use centralized configuration
        phi_config = get_phi_config()
        patterns = phi_config.get_active_patterns()

        for pattern, replacement in patterns:
            scrubbed_text = re.sub(
                pattern, replacement, scrubbed_text, flags=re.IGNORECASE
            )
    else:
        # Use legacy patterns for backward compatibility
        for pattern, replacement in PHI_PATTERNS:
            scrubbed_text = re.sub(
                pattern, replacement, scrubbed_text, flags=re.IGNORECASE
            )

    return scrubbed_text


def scrub_phi_from_dict(
    data: Dict[str, Any], use_centralized_config: bool = True
) -> Dict[str, Any]:
    """Recursively scrub PHI from dictionary data.

    Args:
        data: Dictionary that may contain PHI
        use_centralized_config: Whether to use centralized PHI config

    Returns:
        Dictionary with PHI scrubbed from values
    """
    if not isinstance(data, dict):
        return data

    scrubbed_data: Dict[str, Any] = {}

    for key, value in data.items():
        # Check if key is sensitive
        if key.lower() in SENSITIVE_FIELDS:
            scrubbed_data[key] = "[REDACTED]"
        elif isinstance(value, str):
            scrubbed_data[key] = scrub_phi_from_string(value, use_centralized_config)
        elif isinstance(value, dict):
            scrubbed_data[key] = scrub_phi_from_dict(value, use_centralized_config)
        elif isinstance(value, list):
            scrubbed_data[key] = scrub_phi_from_list(value, use_centralized_config)
        else:
            scrubbed_data[key] = value

    return scrubbed_data


def scrub_phi_from_list(
    data: List[Any], use_centralized_config: bool = True
) -> List[Any]:
    """Recursively scrub PHI from list data.

    Args:
        data: List that may contain PHI
        use_centralized_config: Whether to use centralized PHI config

    Returns:
        List with PHI scrubbed from items
    """
    if not isinstance(data, list):
        return data

    scrubbed_list: List[Any] = []

    for item in data:
        if isinstance(item, str):
            scrubbed_list.append(scrub_phi_from_string(item, use_centralized_config))
        elif isinstance(item, dict):
            scrubbed_list.append(scrub_phi_from_dict(item, use_centralized_config))
        elif isinstance(item, list):
            scrubbed_list.append(scrub_phi_from_list(item, use_centralized_config))
        else:
            scrubbed_list.append(item)

    return scrubbed_list


def scrub_phi(
    data: Union[str, Dict[str, Any], List[Any], Any],
    use_centralized_config: bool = True,
) -> Any:
    """Main PHI scrubbing function that handles various data types.

    Args:
        data: Data that may contain PHI (string, dict, list, or other)
        use_centralized_config: Whether to use centralized PHI config

    Returns:
        Data with PHI scrubbed based on type
    """
    if isinstance(data, str):
        return scrub_phi_from_string(data, use_centralized_config)
    elif isinstance(data, dict):
        return scrub_phi_from_dict(data, use_centralized_config)
    elif isinstance(data, list):
        return scrub_phi_from_list(data, use_centralized_config)
    else:
        return data

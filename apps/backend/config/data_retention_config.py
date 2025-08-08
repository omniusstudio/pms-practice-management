"""Data retention configuration and default policies."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from models.data_retention_policy import DataType, PolicyStatus, RetentionPeriodUnit


class DataRetentionConfig:
    """Configuration for data retention policies and settings."""

    # Default retention policies (HIPAA compliant)
    DEFAULT_POLICIES = [
        {
            "policy_name": "HIPAA Appointments Retention",
            "description": (
                "HIPAA-compliant retention for appointment records. "
                "Retains for 7 years as required for healthcare records."
            ),
            "data_type": DataType.APPOINTMENTS,
            "retention_period": 7,
            "retention_unit": RetentionPeriodUnit.YEARS,
            "status": PolicyStatus.DRAFT,  # Start as draft for safety
            "legal_hold_exempt": False,
            "compliance_notes": (
                "HIPAA requires healthcare records to be retained "
                "for a minimum of 6 years. Extended to 7 years "
                "for additional compliance margin."
            ),
            "batch_size": 500,
            "dry_run_only": True,  # Start with dry runs
        },
        {
            "policy_name": "HIPAA Clinical Notes Retention",
            "description": (
                "HIPAA-compliant retention for clinical notes and "
                "patient documentation. Retains for 7 years."
            ),
            "data_type": DataType.NOTES,
            "retention_period": 7,
            "retention_unit": RetentionPeriodUnit.YEARS,
            "status": PolicyStatus.DRAFT,
            "legal_hold_exempt": False,
            "compliance_notes": (
                "Clinical notes are critical healthcare records "
                "requiring long-term retention per HIPAA guidelines."
            ),
            "batch_size": 200,  # Smaller batches for sensitive data
            "dry_run_only": True,
        },
        {
            "policy_name": "Audit Logs Retention",
            "description": (
                "Retention policy for audit logs. Retains for 7 years "
                "to meet HIPAA audit trail requirements."
            ),
            "data_type": DataType.AUDIT_LOGS,
            "retention_period": 7,
            "retention_unit": RetentionPeriodUnit.YEARS,
            "status": PolicyStatus.DRAFT,
            "legal_hold_exempt": True,  # Audit logs may be exempt
            "compliance_notes": (
                "HIPAA requires audit logs to be retained for "
                "6 years minimum. Extended for compliance safety."
            ),
            "batch_size": 1000,
            "dry_run_only": True,
        },
        {
            "policy_name": "Authentication Tokens Cleanup",
            "description": (
                "Cleanup of expired authentication tokens. "
                "Retains for 90 days for security analysis."
            ),
            "data_type": DataType.AUTH_TOKENS,
            "retention_period": 90,
            "retention_unit": RetentionPeriodUnit.DAYS,
            "status": PolicyStatus.DRAFT,
            "legal_hold_exempt": True,
            "compliance_notes": (
                "Auth tokens are not PHI but retained briefly "
                "for security incident analysis."
            ),
            "batch_size": 2000,
            "dry_run_only": True,
        },
        {
            "policy_name": "FHIR Mappings Cleanup",
            "description": (
                "Cleanup of old FHIR mapping records. "
                "Retains for 2 years for integration history."
            ),
            "data_type": DataType.FHIR_MAPPINGS,
            "retention_period": 2,
            "retention_unit": RetentionPeriodUnit.YEARS,
            "status": PolicyStatus.DRAFT,
            "legal_hold_exempt": True,
            "compliance_notes": (
                "FHIR mappings support interoperability. "
                "Retained for troubleshooting and audit purposes."
            ),
            "batch_size": 1000,
            "dry_run_only": True,
        },
        {
            "policy_name": "Financial Ledger Retention",
            "description": (
                "Retention policy for financial ledger entries. "
                "Retains for 7 years per financial regulations."
            ),
            "data_type": DataType.LEDGER_ENTRIES,
            "retention_period": 7,
            "retention_unit": RetentionPeriodUnit.YEARS,
            "status": PolicyStatus.DRAFT,
            "legal_hold_exempt": False,
            "compliance_notes": (
                "Financial records must be retained for tax "
                "and regulatory compliance. May contain PHI."
            ),
            "batch_size": 500,
            "dry_run_only": True,
        },
    ]

    # Scheduler configuration
    SCHEDULER_CONFIG = {
        "check_interval_minutes": 60,  # Check every hour
        "max_concurrent_jobs": 3,  # Limit concurrent purge jobs
        "execution_interval_hours": 24,  # Execute policies daily
    }

    # Legal hold configuration
    LEGAL_HOLD_CONFIG = {
        "auto_release_enabled": True,
        "notification_enabled": True,
        "default_hold_duration_days": 365,  # 1 year default
    }

    # Safety and compliance settings
    SAFETY_CONFIG = {
        "require_dry_run_first": True,
        "max_records_per_batch": 5000,
        "require_legal_hold_check": True,
        "audit_all_operations": True,
    }

    @classmethod
    def get_default_policies_for_tenant(cls, tenant_id: str) -> List[Dict[str, Any]]:
        """Get default retention policies for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of policy configurations
        """
        policies = []
        now = datetime.now(timezone.utc)

        for policy_config in cls.DEFAULT_POLICIES:
            # Add tenant_id and generated fields to each policy
            tenant_policy = policy_config.copy()
            tenant_policy["tenant_id"] = tenant_id
            tenant_policy["policy_id"] = str(uuid.uuid4())
            tenant_policy["created_at"] = now
            tenant_policy["updated_at"] = now
            policies.append(tenant_policy)

        return policies

    @classmethod
    def get_policy_by_data_type(
        cls, data_type: str, tenant_id: str = "test-tenant"
    ) -> Dict[str, Any]:
        """Get default policy configuration for a data type.

        Args:
            data_type: Type of data (string)
            tenant_id: Tenant identifier

        Returns:
            Policy configuration dictionary or None if not found
        """
        for policy in cls.DEFAULT_POLICIES:
            if policy["data_type"].value == data_type:
                result = policy.copy()
                result["tenant_id"] = tenant_id
                return result

        # Return None if not found
        return None

    @classmethod
    def validate_policy_config(cls, policy_config: Dict) -> Dict[str, Any]:
        """Validate a policy configuration.

        Args:
            policy_config: Policy configuration to validate

        Returns:
            Dictionary with 'valid' boolean and 'errors' list
        """
        errors = []

        required_fields = [
            "policy_name",
            "data_type",
            "retention_period",
            "retention_unit",
        ]

        for field in required_fields:
            if field not in policy_config:
                errors.append(f"Missing required field: {field}")

        # Validate retention period
        if "retention_period" in policy_config:
            period = policy_config["retention_period"]
            if not isinstance(period, int) or period <= 0:
                errors.append("retention_period must be a positive integer")

        # Validate batch size
        if "batch_size" in policy_config:
            batch_size = policy_config["batch_size"]
            if (
                not isinstance(batch_size, int)
                or batch_size <= 0
                or batch_size > cls.SAFETY_CONFIG["max_records_per_batch"]
            ):
                errors.append(
                    f"batch_size must be between 1 and "
                    f"{cls.SAFETY_CONFIG['max_records_per_batch']}"
                )

        return {"valid": len(errors) == 0, "errors": errors}

    @classmethod
    def get_hipaa_compliant_periods(cls) -> Dict[DataType, int]:
        """Get HIPAA-compliant minimum retention periods in years.

        Returns:
            Dictionary mapping data types to minimum years
        """
        return {
            DataType.APPOINTMENTS: 6,  # HIPAA minimum
            DataType.NOTES: 6,  # HIPAA minimum
            DataType.AUDIT_LOGS: 6,  # HIPAA minimum
            DataType.LEDGER_ENTRIES: 7,  # Financial regulations
            DataType.AUTH_TOKENS: 0,  # Not PHI, can be shorter
            DataType.FHIR_MAPPINGS: 1,  # Technical data
            DataType.ENCRYPTION_KEYS: 7,  # Security requirement
        }

"""Data retention policy model for HIPAA-compliant data management."""

from datetime import datetime, timedelta, timezone
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Index, Integer, String, Text

from .base import BaseModel


class RetentionPeriodUnit(str, Enum):
    """Units for retention periods."""

    DAYS = "days"
    MONTHS = "months"
    YEARS = "years"


class DataType(str, Enum):
    """Types of data that can have retention policies."""

    APPOINTMENTS = "appointments"
    NOTES = "notes"
    AUDIT_LOGS = "audit_logs"
    AUTH_TOKENS = "auth_tokens"
    ENCRYPTION_KEYS = "encryption_keys"
    FHIR_MAPPINGS = "fhir_mappings"
    LEDGER_ENTRIES = "ledger_entries"


class PolicyStatus(str, Enum):
    """Status of retention policies."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"


class DataRetentionPolicy(BaseModel):
    """Data retention policy for automated data lifecycle management.

    This model defines retention rules for different types of data,
    ensuring HIPAA compliance and legal requirements are met.
    """

    __tablename__ = "data_retention_policies"

    # Policy identification
    policy_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Data type and retention rules
    data_type: Column[DataType] = Column(SQLEnum(DataType), nullable=False)
    retention_period = Column(Integer, nullable=False)  # Number of units
    retention_unit: Column[RetentionPeriodUnit] = Column(
        SQLEnum(RetentionPeriodUnit), nullable=False, default=RetentionPeriodUnit.YEARS
    )

    # Policy status and scheduling
    status: Column[PolicyStatus] = Column(
        SQLEnum(PolicyStatus), nullable=False, default=PolicyStatus.DRAFT
    )

    # Execution tracking
    last_executed_at = Column(DateTime(timezone=True), nullable=True)
    next_execution_at = Column(DateTime(timezone=True), nullable=True)

    # Legal and compliance
    legal_hold_exempt = Column(Boolean, default=False, nullable=False)
    compliance_notes = Column(Text, nullable=True)

    # Execution settings
    batch_size = Column(Integer, default=1000, nullable=False)
    dry_run_only = Column(Boolean, default=True, nullable=False)

    def __init__(self, **kwargs):
        """Initialize with proper defaults for in-memory objects."""
        # Set defaults for fields that should have them
        if "retention_unit" not in kwargs:
            kwargs["retention_unit"] = RetentionPeriodUnit.YEARS
        if "status" not in kwargs:
            kwargs["status"] = PolicyStatus.DRAFT
        if "legal_hold_exempt" not in kwargs:
            kwargs["legal_hold_exempt"] = False
        if "batch_size" not in kwargs:
            kwargs["batch_size"] = 1000
        if "dry_run_only" not in kwargs:
            kwargs["dry_run_only"] = True

        super().__init__(**kwargs)

    # Indexes for performance
    __table_args__ = (
        Index("idx_retention_policy_data_type_status", "data_type", "status"),
        Index("idx_retention_policy_next_execution", "next_execution_at"),
        Index("idx_retention_policy_tenant_active", "tenant_id", "status"),
    )

    def calculate_retention_cutoff(self) -> datetime:
        """Calculate the cutoff date for data retention.

        Returns:
            datetime: Records older than this date should be purged
        """
        now = datetime.now(timezone.utc)

        if self.retention_unit == RetentionPeriodUnit.DAYS:
            return now - timedelta(days=self.retention_period)
        elif self.retention_unit == RetentionPeriodUnit.MONTHS:
            # Approximate months as 30 days
            return now - timedelta(days=self.retention_period * 30)
        elif self.retention_unit == RetentionPeriodUnit.YEARS:
            return now - timedelta(days=self.retention_period * 365)
        else:
            raise ValueError(f"Unknown retention unit: {self.retention_unit}")

    def should_execute_now(self) -> bool:
        """Check if the policy should be executed now.

        Returns:
            bool: True if policy should be executed
        """
        if self.status != PolicyStatus.ACTIVE:
            return False

        if self.next_execution_at is None:
            return True

        now = datetime.now(timezone.utc)
        return now >= self.next_execution_at

    def update_execution_schedule(self, execution_interval_hours: int = 24) -> None:
        """Update the next execution time.

        Args:
            execution_interval_hours: Hours until next execution
        """
        now = datetime.now(timezone.utc)
        self.last_executed_at = now
        self.next_execution_at = now + timedelta(hours=execution_interval_hours)

    def __repr__(self) -> str:
        """String representation without PHI."""
        return (
            f"<DataRetentionPolicy("
            f"id={self.id}, "
            f"name={self.policy_name}, "
            f"data_type={self.data_type.value}, "
            f"retention={self.retention_period} {self.retention_unit.value}"
            f")>"
        )

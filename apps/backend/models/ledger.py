"""Ledger model for billing and financial tracking."""

from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, Column, Date
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import relationship

from .base import BaseModel
from .types import UUID


class TransactionType(str, Enum):
    """Transaction type enumeration."""

    CHARGE = "charge"
    PAYMENT = "payment"
    ADJUSTMENT = "adjustment"
    REFUND = "refund"
    WRITE_OFF = "write_off"
    INSURANCE_PAYMENT = "insurance_payment"
    COPAY = "copay"
    DEDUCTIBLE = "deductible"


class PaymentMethod(str, Enum):
    """Payment method enumeration."""

    CASH = "cash"
    CHECK = "check"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    INSURANCE = "insurance"
    OTHER = "other"


class LedgerEntry(BaseModel):
    """Financial ledger entry for billing and payments."""

    __tablename__ = "ledger"

    # Foreign keys
    client_id: Column[UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Transaction details
    transaction_type: Column[TransactionType] = Column(
        SQLEnum(TransactionType), nullable=False
    )

    amount = Column(Numeric(precision=10, scale=2), nullable=False)

    description = Column(String(500), nullable=False)

    # Service and billing information
    service_date = Column(Date, nullable=True)
    billing_code = Column(String(20), nullable=True)  # CPT code
    diagnosis_code = Column(String(20), nullable=True)  # ICD-10 code

    # Payment information
    payment_method: Column[PaymentMethod] = Column(
        SQLEnum(PaymentMethod), nullable=True
    )

    reference_number = Column(String(100), nullable=True)
    check_number = Column(String(50), nullable=True)

    # Insurance information
    insurance_claim_number = Column(String(100), nullable=True)
    insurance_authorization = Column(String(100), nullable=True)

    # Status and reconciliation
    is_posted = Column(Boolean, default=True, nullable=False)
    is_reconciled = Column(Boolean, default=False, nullable=False)
    reconciliation_date = Column(Date, nullable=True)

    # Additional notes
    notes = Column(Text, nullable=True)

    # Relationships
    client = relationship("Client", back_populates="ledger_entries")

    # Indexes for performance
    __table_args__ = (
        Index("idx_ledger_client", "client_id"),
        Index("idx_ledger_transaction_type", "transaction_type"),
        Index("idx_ledger_service_date", "service_date"),
        Index("idx_ledger_amount", "amount"),
        Index("idx_ledger_posted", "is_posted"),
        Index("idx_ledger_reconciled", "is_reconciled"),
        Index("idx_ledger_client_date", "client_id", "service_date"),
        Index("idx_ledger_billing_code", "billing_code"),
    )

    def is_charge(self) -> bool:
        """Check if entry is a charge."""
        return self.transaction_type == TransactionType.CHARGE

    def is_payment(self) -> bool:
        """Check if entry is a payment."""
        return self.transaction_type in [
            TransactionType.PAYMENT,
            TransactionType.INSURANCE_PAYMENT,
            TransactionType.COPAY,
        ]

    @property
    def signed_amount(self) -> Decimal:
        """Get amount with appropriate sign (negative for payments)."""
        if self.is_payment or self.transaction_type == TransactionType.REFUND:
            return -abs(self.amount)
        return abs(self.amount)

    def can_be_reconciled(self) -> bool:
        """Check if entry can be reconciled."""
        return self.is_posted and not self.is_reconciled

    def reconcile(self) -> None:
        """Reconcile the entry (implementation in service layer)."""
        pass

    def to_dict(self) -> dict:
        """Convert to dictionary with computed fields."""
        data = super().to_dict()

        # Convert Decimal to string for JSON serialization
        if self.amount:
            data["amount"] = str(self.amount)
            data["signed_amount"] = str(self.signed_amount)

        # Add computed fields
        data["is_charge"] = self.is_charge()
        data["is_payment"] = self.is_payment()
        data["can_be_reconciled"] = self.can_be_reconciled()

        return data

    def __repr__(self) -> str:
        """String representation without PHI."""
        return (
            f"<LedgerEntry(id={self.id}, "
            f"type={self.transaction_type}, "
            f"amount={self.amount})>"
        )

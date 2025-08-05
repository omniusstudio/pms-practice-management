"""Ledger Entry factory for HIPAA-compliant test data generation."""

from datetime import date, timedelta
from decimal import Decimal

import factory
from faker import Faker

from models.ledger import LedgerEntry

from .base import BaseFactory
from .client import ClientFactory

fake = Faker()


class LedgerEntryFactory(BaseFactory):
    """Factory for generating HIPAA-compliant ledger entries."""

    class Meta:
        model = LedgerEntry

    # Relationships
    client = factory.SubFactory(ClientFactory)

    # Transaction details
    transaction_type = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "charge",
                "payment",
                "adjustment",
                "refund",
                "write_off",
                "insurance_payment",
            ]
        )
    )

    payment_method = factory.LazyAttribute(
        lambda obj: (
            fake.random_element(
                [
                    "cash",
                    "check",
                    "credit_card",
                    "debit_card",
                    "insurance",
                    "bank_transfer",
                    "other",
                ]
            )
            if obj.transaction_type in ["payment", "insurance_payment"]
            else None
        )
    )

    # Financial amounts
    amount = factory.LazyFunction(lambda: Decimal(str(fake.random_int(25, 500))))

    # Remove balance fields as they don't exist in the model

    # Service information
    service_date = factory.LazyFunction(
        lambda: fake.date_between(
            start_date=date.today() - timedelta(days=90), end_date=date.today()
        )
    )

    billing_code = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "90834",  # Psychotherapy, 45 minutes
                "90837",  # Psychotherapy, 60 minutes
                "90791",  # Psychiatric diagnostic evaluation
                "90834+90836",  # Psychotherapy with add-on
                "90847",  # Family psychotherapy
                "90853",  # Group psychotherapy
                "99213",  # Office visit, established patient
                "99214",  # Office visit, established patient, complex
                "96116",  # Neurobehavioral status exam
                "96118",  # Neuropsychological testing
            ]
        )
    )

    diagnosis_code = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "F32.9",  # Major depressive disorder, single episode
                "F41.1",  # Generalized anxiety disorder
                "F43.10",  # Post-traumatic stress disorder
                "F90.9",  # ADHD, unspecified
                "F84.0",  # Autistic disorder
                "F31.9",  # Bipolar disorder, unspecified
                "F40.10",  # Social phobia, unspecified
                "F42.9",  # Obsessive-compulsive disorder
                "F50.9",  # Eating disorder, unspecified
                "F60.3",  # Borderline personality disorder
            ]
        )
    )

    # Description and notes
    description = factory.LazyAttribute(
        lambda obj: (
            f"{obj.transaction_type.replace('_', ' ').title()} - "
            f"Service Code {obj.billing_code}"
        )
    )

    notes = factory.LazyFunction(
        lambda: fake.random_element(
            [
                None,
                "Insurance copay collected",
                "Patient self-pay",
                "Insurance claim pending",
                "Adjustment per contract",
                "Refund processed",
                "Write-off approved by supervisor",
            ]
        )
    )

    # Insurance information
    insurance_claim_number = factory.LazyFunction(
        lambda: fake.random_element(
            [None, f"CLM{fake.random_int(100000000, 999999999)}"]
        )
    )

    insurance_authorization = factory.LazyFunction(
        lambda: fake.random_element([None, f"AUTH{fake.random_int(100000, 999999)}"])
    )

    # Payment processing
    check_number = factory.LazyAttribute(
        lambda obj: (
            f"{fake.random_int(1000, 9999)}" if obj.payment_method == "check" else None
        )
    )

    reference_number = factory.LazyFunction(
        lambda: f"REF{fake.random_int(100000000, 999999999)}"
    )

    is_posted = factory.LazyFunction(lambda: fake.boolean(chance_of_getting_true=85))

    # Reconciliation
    is_reconciled = factory.LazyFunction(
        lambda: fake.boolean(chance_of_getting_true=70)
    )

    reconciliation_date = factory.LazyAttribute(
        lambda obj: (
            fake.date_between(start_date=obj.service_date, end_date=date.today())
            if obj.is_reconciled
            else None
        )
    )

    # Remove audit trail fields as they don't exist in the model

    @factory.post_generation
    def ensure_financial_logic(obj, create, extracted, **kwargs):
        """Ensure financial logic consistency."""
        if not create:
            return

        # Ensure reconciled entries have reconciliation dates
        if obj.is_reconciled and not obj.reconciliation_date:
            obj.reconciliation_date = obj.service_date

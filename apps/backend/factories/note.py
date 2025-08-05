"""Note factory for HIPAA-compliant test data generation."""

import factory
from faker import Faker

from models.note import Note

from .base import BaseFactory
from .client import ClientFactory
from .provider import ProviderFactory

fake = Faker()


class NoteFactory(BaseFactory):
    """Factory for generating HIPAA-compliant clinical notes."""

    class Meta:
        model = Note

    # Relationships
    client = factory.SubFactory(ClientFactory)
    provider = factory.SubFactory(ProviderFactory)
    appointment = None  # Optional appointment reference

    # Note classification
    note_type = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "progress_note",
                "intake_note",
                "assessment",
                "treatment_plan",
                "discharge_summary",
                "administrative",
                "billing",
                "other",
            ]
        )
    )

    title = factory.LazyAttribute(
        lambda obj: (
            f"{obj.note_type.replace('_', ' ').title()} - "
            f"{fake.date_object().strftime('%m/%d/%Y')}"
        )
    )

    # Clinical content (fictional)
    content = factory.LazyFunction(lambda: fake.text(max_nb_chars=1500))

    # Clinical fields
    diagnosis_codes = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "F41.1",  # Generalized anxiety disorder
                "F32.9",  # Major depressive disorder
                "F43.10",  # PTSD
                "F43.23",  # Adjustment disorder
                "F31.9",  # Bipolar disorder
                "F90.9",  # ADHD
            ]
        )
    )

    treatment_goals = factory.LazyFunction(lambda: fake.text(max_nb_chars=500))

    interventions = factory.LazyFunction(lambda: fake.text(max_nb_chars=500))

    client_response = factory.LazyFunction(lambda: fake.text(max_nb_chars=500))

    plan = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "Continue current medication regimen, follow up in 4 weeks.",
                "Increase therapy frequency to weekly sessions.",
                "Refer to psychiatrist for medication evaluation.",
                "Continue CBT techniques, practice mindfulness exercises.",
                "Schedule family therapy session next month.",
                "Monitor mood symptoms, adjust treatment as needed.",
            ]
        )
    )

    # Note status fields
    is_signed = factory.LazyFunction(lambda: fake.boolean(chance_of_getting_true=70))

    is_locked = factory.LazyFunction(lambda: fake.boolean(chance_of_getting_true=30))

    requires_review = factory.LazyFunction(
        lambda: fake.boolean(chance_of_getting_true=25)
    )

    # Billing information
    billable = factory.LazyFunction(lambda: fake.boolean(chance_of_getting_true=85))

    billing_code = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "90834",  # Psychotherapy, 45 minutes
                "90837",  # Psychotherapy, 60 minutes
                "90791",  # Psychiatric diagnostic evaluation
                "90847",  # Family psychotherapy
                "90853",  # Group psychotherapy
            ]
        )
    )

    # Post-generation removed to avoid session conflicts

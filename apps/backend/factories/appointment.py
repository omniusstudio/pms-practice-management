"""Appointment factory for HIPAA-compliant test data generation."""

from datetime import timedelta, timezone

import factory
from faker import Faker

from models.appointment import Appointment

from .base import BaseFactory
from .client import ClientFactory
from .provider import ProviderFactory

fake = Faker()


class AppointmentFactory(BaseFactory):
    """Factory for generating HIPAA-compliant appointment data."""

    class Meta:
        model = Appointment

    # Relationships
    client = factory.SubFactory(ClientFactory)
    provider = factory.SubFactory(ProviderFactory)

    # Appointment details
    appointment_type = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "initial_consultation",
                "follow_up",
                "therapy_session",
                "medication_management",
                "group_therapy",
                "family_therapy",
                "crisis_intervention",
                "assessment",
                "other",
            ]
        )
    )

    status = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "scheduled",
                "confirmed",
                "completed",
                "cancelled",
                "no_show",
                "rescheduled",
            ]
        )
    )

    # Scheduling information
    scheduled_start = factory.LazyFunction(
        lambda: fake.date_time_between(
            start_date="-30d", end_date="+60d", tzinfo=timezone.utc
        )
    )

    scheduled_end = factory.LazyAttribute(
        lambda obj: obj.scheduled_start
        + timedelta(minutes=fake.random_element([30, 45, 60, 90]))
    )

    actual_start = factory.LazyAttribute(
        lambda obj: (
            obj.scheduled_start + timedelta(minutes=fake.random_int(-10, 15))
            if obj.status in ["completed", "no_show"]
            else None
        )
    )

    actual_end = factory.LazyAttribute(
        lambda obj: (
            obj.actual_start
            + timedelta(minutes=fake.random_element([25, 30, 45, 60, 90]))
            if obj.actual_start and obj.status == "completed"
            else None
        )
    )

    duration_minutes = factory.LazyAttribute(
        lambda obj: ((obj.scheduled_end - obj.scheduled_start).total_seconds() / 60)
    )

    # Location and format
    location = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "Main Office - Room 101",
                "Main Office - Room 102",
                "Downtown Branch - Room A",
                "Telehealth",
                "Group Room",
                "Family Therapy Room",
            ]
        )
    )

    is_telehealth = factory.LazyAttribute(
        lambda obj: "Telehealth" in (obj.location or "")
    )

    # Clinical information
    reason_for_visit = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "Anxiety and stress management",
                "Depression symptoms",
                "Sleep difficulties",
                "Relationship issues",
                "Work-related stress",
                "Family conflicts",
                "Grief and loss",
                "Substance use concerns",
                "Panic attacks",
                "Mood swings",
                "Concentration problems",
                "Social anxiety",
                "Trauma processing",
                "Life transitions",
                "Self-esteem issues",
            ]
        )
    )

    appointment_notes = factory.LazyFunction(
        lambda: fake.random_element([None, fake.text(max_nb_chars=500)])
    )

    # Billing and insurance

    insurance_authorization = factory.LazyFunction(
        lambda: fake.random_element([None, f"AUTH{fake.random_int(100000, 999999)}"])
    )

    copay_amount = factory.LazyFunction(
        lambda: fake.random_element(
            ["0.00", "10.00", "15.00", "20.00", "25.00", "30.00", "40.00", "50.00"]
        )
    )

    # Administrative details
    cancellation_reason = factory.LazyAttribute(
        lambda obj: (
            fake.random_element(
                [
                    "Patient request",
                    "Provider illness",
                    "Emergency",
                    "Weather",
                    "Transportation issues",
                    "Insurance issues",
                ]
            )
            if obj.status == "cancelled"
            else None
        )
    )

    # Remove no_show_fee as it doesn't exist in the model

    # Reminders and notifications
    reminder_sent = factory.LazyFunction(
        lambda: fake.boolean(chance_of_getting_true=85)
    )

    confirmation_sent = factory.LazyFunction(
        lambda: fake.boolean(chance_of_getting_true=75)
    )

    # Follow-up information

    # Quality metrics

    @factory.post_generation
    def ensure_logical_times(obj, create, extracted, **kwargs):
        """Ensure appointment times are logically consistent."""
        if obj.scheduled_start and obj.scheduled_end:
            if obj.scheduled_end <= obj.scheduled_start:
                obj.scheduled_end = obj.scheduled_start + timedelta(minutes=60)

        if obj.actual_start and obj.actual_end:
            if obj.actual_end <= obj.actual_start:
                obj.actual_end = obj.actual_start + timedelta(minutes=45)

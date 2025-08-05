"""Client factory for HIPAA-compliant test data generation."""

from datetime import date, timedelta

import factory
from faker import Faker

from models.client import Client

from .base import BaseFactory

fake = Faker()


class ClientFactory(BaseFactory):
    """Factory for generating HIPAA-compliant client data."""

    class Meta:
        model = Client

    # Personal information (HIPAA-safe)
    first_name = factory.LazyFunction(BaseFactory.generate_safe_name)
    last_name = factory.LazyFunction(lambda: fake.last_name())

    date_of_birth = factory.LazyFunction(
        lambda: fake.date_of_birth(minimum_age=18, maximum_age=85)
    )

    gender = factory.LazyFunction(
        lambda: fake.random_element(
            ["Male", "Female", "Non-binary", "Prefer not to say"]
        )
    )

    # Contact information (HIPAA-safe)
    email = factory.LazyFunction(
        lambda: BaseFactory.generate_safe_email("client.local")
    )
    phone = factory.LazyFunction(BaseFactory.generate_safe_phone)

    # Address information (fictional)
    address_line1 = factory.LazyFunction(
        lambda: f"{fake.building_number()} {fake.street_name()}"
    )
    address_line2 = factory.LazyFunction(
        lambda: fake.random_element(
            [None, f"Apt {fake.random_int(1, 999)}", f"Unit {fake.random_int(1, 50)}"]
        )
    )
    city = factory.LazyFunction(fake.city)
    state = factory.LazyFunction(fake.state_abbr)
    zip_code = factory.LazyFunction(fake.zipcode)

    # Emergency contact (HIPAA-safe)
    emergency_contact_name = factory.LazyFunction(BaseFactory.generate_safe_name)
    emergency_contact_phone = factory.LazyFunction(BaseFactory.generate_safe_phone)
    emergency_contact_relationship = factory.LazyFunction(
        lambda: fake.random_element(
            ["Spouse", "Parent", "Sibling", "Child", "Friend", "Other"]
        )
    )

    # Insurance information (fictional)
    insurance_provider = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "Blue Cross Blue Shield",
                "Aetna",
                "Cigna",
                "UnitedHealth",
                "Humana",
                "Kaiser Permanente",
                "Self-Pay",
            ]
        )
    )
    insurance_id = factory.LazyFunction(
        lambda: f"{fake.random_int(100000000, 999999999)}"
    )

    # Clinical information (fictional)
    primary_diagnosis = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "F32.9 - Major depressive disorder, single episode",
                "F41.1 - Generalized anxiety disorder",
                "F43.10 - Post-traumatic stress disorder",
                "F90.9 - Attention-deficit hyperactivity disorder",
                "F84.0 - Autistic disorder",
                "F31.9 - Bipolar disorder, unspecified",
            ]
        )
    )

    medications = factory.LazyFunction(
        lambda: fake.random_element(
            [
                None,
                "Sertraline 50mg daily",
                "Fluoxetine 20mg daily",
                "Lorazepam 0.5mg as needed",
                "Methylphenidate 10mg twice daily",
            ]
        )
    )

    allergies = factory.LazyFunction(
        lambda: fake.random_element(
            [None, "NKDA", "Penicillin", "Sulfa drugs", "Latex"]
        )
    )

    # Preferences and settings
    preferred_language = factory.LazyFunction(
        lambda: fake.random_element(
            ["English", "Spanish", "French", "German", "Mandarin"]
        )
    )

    communication_preferences = factory.LazyFunction(
        lambda: fake.random_element(["Email", "Phone", "Text", "Portal", "Mail"])
    )

    # Clinical notes (fictional)
    intake_notes = factory.LazyFunction(lambda: fake.text(max_nb_chars=500))

    administrative_notes = factory.LazyFunction(
        lambda: fake.random_element([None, fake.text(max_nb_chars=200)])
    )

    # Status and preferences
    is_active = factory.LazyFunction(lambda: fake.boolean(chance_of_getting_true=90))

    @factory.post_generation
    def ensure_adult_age(obj, create, extracted, **kwargs):
        """Ensure client is at least 18 years old."""
        if obj.date_of_birth:
            today = date.today()
            age = (today - obj.date_of_birth).days // 365
            if age < 18:
                obj.date_of_birth = today - timedelta(days=18 * 365 + 30)

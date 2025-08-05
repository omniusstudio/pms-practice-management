"""Provider factory for HIPAA-compliant test data generation."""

import factory
from faker import Faker

from models.provider import Provider

from .base import BaseFactory

fake = Faker()


class ProviderFactory(BaseFactory):
    """Factory for generating HIPAA-compliant provider data."""

    class Meta:
        model = Provider

    # Personal information (HIPAA-safe)
    first_name = factory.LazyFunction(BaseFactory.generate_safe_name)
    last_name = factory.LazyFunction(lambda: fake.last_name())

    # Professional information
    title = factory.LazyFunction(
        lambda: fake.random_element(["Dr.", "Ms.", "Mr.", "Mrs."])
    )

    credentials = factory.LazyFunction(
        lambda: fake.random_element(
            ["MD", "PhD", "PsyD", "LCSW", "LPC", "LMFT", "LPCC"]
        )
    )

    specialty = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "General Psychiatry",
                "Child and Adolescent Psychiatry",
                "Clinical Psychology",
                "Marriage and Family Therapy",
                "Substance Abuse Counseling",
                "Trauma Therapy",
                "Cognitive Behavioral Therapy",
            ]
        )
    )

    # Contact information (HIPAA-safe)
    email = factory.LazyFunction(
        lambda: BaseFactory.generate_safe_email("provider.local")
    )
    phone = factory.LazyFunction(BaseFactory.generate_safe_phone)

    middle_name = factory.LazyFunction(
        lambda: fake.random_element([None, fake.first_name()])
    )

    # Professional credentials
    license_number = factory.LazyFunction(
        lambda: f"{fake.state_abbr()}{fake.random_int(100000, 999999)}"
    )

    license_state = factory.LazyFunction(fake.state_abbr)

    npi_number = factory.LazyFunction(
        lambda: f"{fake.random_int(1000000000, 9999999999)}"
    )

    tax_id = factory.LazyFunction(
        lambda: (f"{fake.random_int(10, 99)}-{fake.random_int(1000000, 9999999)}")
    )

    # Office address (fictional)
    office_address_line1 = factory.LazyFunction(
        lambda: f"{fake.building_number()} {fake.street_name()}"
    )

    office_address_line2 = factory.LazyFunction(
        lambda: fake.random_element(
            [
                None,
                f"Suite {fake.random_int(100, 999)}",
                f"Floor {fake.random_int(1, 10)}",
            ]
        )
    )

    office_city = factory.LazyFunction(fake.city)
    office_state = factory.LazyFunction(fake.state_abbr)
    office_zip_code = factory.LazyFunction(fake.zipcode)

    office_phone = factory.LazyFunction(BaseFactory.generate_safe_phone)

    default_appointment_duration = factory.LazyFunction(
        lambda: fake.random_element(["30", "45", "50", "60"])
    )

    # Availability and preferences
    accepts_new_patients = factory.LazyFunction(
        lambda: fake.boolean(chance_of_getting_true=75)
    )

    # Status and additional information
    is_active = factory.LazyFunction(lambda: fake.boolean(chance_of_getting_true=95))

    bio = factory.LazyFunction(lambda: fake.text(max_nb_chars=1000))

    administrative_notes = factory.LazyFunction(
        lambda: fake.random_element([None, fake.text(max_nb_chars=500)])
    )

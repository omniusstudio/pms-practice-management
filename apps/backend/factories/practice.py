"""Practice Profile and Location factories."""

import factory
from faker import Faker

from models.practice_profile import PracticeProfile

from .base import BaseFactory

fake = Faker()


class PracticeProfileFactory(BaseFactory):
    """Factory for generating HIPAA-compliant practice profiles."""

    class Meta:
        model = PracticeProfile

    name = factory.LazyFunction(
        lambda: fake.word().title()
        + " "
        + fake.random_element(
            [
                "Wellness Center",
                "Mental Health Group",
                "Counseling Associates",
                "Therapy Center",
                "Behavioral Health",
                "Psychology Practice",
            ]
        )
    )

    # Contact information (HIPAA-safe)
    email = factory.LazyFunction(
        lambda: BaseFactory.generate_safe_email("practice.local")
    )
    phone = factory.LazyFunction(BaseFactory.generate_safe_phone)
    fax = factory.LazyFunction(BaseFactory.generate_safe_phone)
    website = factory.LazyFunction(lambda: f"https://www.{fake.domain_name()}")

    # Address information (fictional)
    address_line1 = factory.LazyFunction(
        lambda: f"{fake.building_number()} {fake.street_name()}"
    )

    address_line2 = factory.LazyFunction(
        lambda: fake.random_element(
            [
                None,
                f"Suite {fake.random_int(100, 999)}",
                f"Floor {fake.random_int(1, 10)}",
            ]
        )
    )
    city = factory.LazyFunction(fake.city)
    state = factory.LazyFunction(fake.state_abbr)
    zip_code = factory.LazyFunction(fake.zipcode)
    country = "US"

    # Practice details
    npi_number = factory.LazyFunction(
        lambda: f"{fake.random_int(1000000000, 9999999999)}"
    )
    tax_id = factory.LazyFunction(
        lambda: (f"{fake.random_int(10, 99)}-{fake.random_int(1000000, 9999999)}")
    )

    # Operational settings
    timezone = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "America/New_York",
                "America/Chicago",
                "America/Denver",
                "America/Los_Angeles",
                "America/Phoenix",
            ]
        )
    )

    # Business information
    # Remove business_hours and emergency_contact as they don't exist
    # in the model

    # Status flags
    is_active = True
    accepts_new_patients = factory.LazyFunction(
        lambda: fake.boolean(chance_of_getting_true=80)
    )

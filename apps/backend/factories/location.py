"""Location factory for HIPAA-compliant test data generation."""

import factory
from faker import Faker

from models.location import Location

from .base import BaseFactory
from .practice import PracticeProfileFactory

fake = Faker()


class LocationFactory(BaseFactory):
    """Factory for generating HIPAA-compliant location data."""

    class Meta:
        model = Location

    # Link to practice profile
    practice_profile = factory.SubFactory(PracticeProfileFactory)

    # Inherit tenant_id from practice_profile
    tenant_id = factory.LazyAttribute(lambda obj: obj.practice_profile.tenant_id)

    name = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "Main Office",
                "Downtown Branch",
                "Eastside Location",
                "Westside Center",
                "North Campus",
                "South Branch",
                "Telehealth Services",
                "Mobile Unit",
            ]
        )
    )

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

    # Contact information (HIPAA-safe)
    phone = factory.LazyFunction(BaseFactory.generate_safe_phone)
    fax = factory.LazyFunction(
        lambda: fake.random_element([None, BaseFactory.generate_safe_phone()])
    )
    email = factory.LazyFunction(
        lambda: BaseFactory.generate_safe_email("location.local")
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

    # Location flags
    is_primary = factory.LazyFunction(lambda: fake.boolean(chance_of_getting_true=20))
    is_active = True
    accepts_appointments = factory.LazyFunction(
        lambda: fake.boolean(chance_of_getting_true=90)
    )

    # Accessibility features
    wheelchair_accessible = factory.LazyFunction(
        lambda: fake.boolean(chance_of_getting_true=75)
    )
    parking_available = factory.LazyFunction(
        lambda: fake.boolean(chance_of_getting_true=85)
    )

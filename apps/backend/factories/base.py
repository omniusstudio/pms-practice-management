"""Base factory class for HIPAA-compliant data generation."""

import uuid
from datetime import timezone

import factory
from faker import Faker

# Initialize Faker with a seed for reproducible test data
fake = Faker()
Faker.seed(42)


class BaseFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Base factory with HIPAA-compliant data generation.

    All factories inherit from this base to ensure:
    - Consistent data generation patterns
    - HIPAA compliance (no real PHI)
    - Proper tenant isolation
    - Reproducible test data
    """

    class Meta:
        abstract = True
        # Session will be set by tests or default to production session
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    # Base model fields
    id = factory.LazyFunction(lambda: uuid.uuid4())
    created_at = factory.LazyFunction(
        lambda: fake.date_time_between(
            start_date="-1y", end_date="now", tzinfo=timezone.utc
        )
    )
    updated_at = factory.LazyAttribute(lambda obj: obj.created_at)
    correlation_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    tenant_id = factory.Sequence(lambda n: f"tenant_{n:03d}")

    @classmethod
    def _check_for_phi(cls, data_dict):
        """Check for PHI fields in data dictionary.

        Args:
            data_dict: Dictionary of field names and values to check

        Raises:
            ValueError: If PHI field is detected
        """
        sensitive_fields = ["ssn", "social_security", "real_name", "actual_email"]
        for field in sensitive_fields:
            if field in data_dict:
                raise ValueError("HIPAA Violation")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override create to ensure HIPAA compliance."""
        # Check for PHI fields
        cls._check_for_phi(kwargs)

        return super()._create(model_class, *args, **kwargs)

    @staticmethod
    def generate_safe_email(domain="example.local"):
        """Generate HIPAA-safe email addresses."""
        email = fake.email()
        return email.replace(email.split("@")[1], domain)

    @staticmethod
    def generate_safe_phone():
        """Generate HIPAA-safe phone numbers."""
        # Use 555 prefix for clearly fake numbers
        return f"555-{fake.random_int(min=1000, max=9999)}"

    @staticmethod
    def generate_safe_name():
        """Generate HIPAA-safe names."""
        # Use clearly fictional names
        return fake.name()

    @staticmethod
    def generate_tenant_id(prefix="tenant"):
        """Generate consistent tenant IDs for isolation."""
        return f"{prefix}_{fake.random_int(min=100, max=999)}"

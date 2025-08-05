"""Encryption key factory for HIPAA-compliant test data generation."""

from datetime import timedelta, timezone
from uuid import uuid4

import factory
from faker import Faker

from models.encryption_key import EncryptionKey, KeyProvider, KeyStatus, KeyType

from .base import BaseFactory

fake = Faker()


class EncryptionKeyFactory(BaseFactory):
    """Factory for generating HIPAA-compliant encryption key data."""

    class Meta:
        model = EncryptionKey

    # Key identification
    key_name = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "master-key",
                "data-encryption-key",
                "backup-key",
                "archive-key",
                "temp-key",
            ]
        )
        + f"-{fake.random_int(min=100, max=999)}"
    )

    key_type = factory.LazyFunction(
        lambda: fake.random_element(
            [
                KeyType.PHI_DATA,
                KeyType.PII_DATA,
                KeyType.FINANCIAL,
                KeyType.CLINICAL,
                KeyType.BACKUP,
            ]
        )
    )

    kms_provider = factory.LazyFunction(
        lambda: fake.random_element(
            [
                KeyProvider.AWS_KMS,
                KeyProvider.AZURE_KV,
                KeyProvider.HASHICORP_VAULT,
                KeyProvider.LOCAL_HSM,
            ]
        )
    )

    # Key metadata
    kms_key_id = factory.LazyFunction(lambda: f"key-{fake.uuid4()}")

    kms_region = factory.LazyFunction(
        lambda: fake.random_element([None, "us-west-2", "us-east-1", "eu-west-1"])
    )

    kms_endpoint = factory.LazyFunction(
        lambda: fake.random_element(
            [None, "https://kms.us-west-2.amazonaws.com", "https://vault.example.com"]
        )
    )

    status = factory.LazyFunction(
        lambda: fake.random_element(
            [KeyStatus.ACTIVE, KeyStatus.PENDING, KeyStatus.INACTIVE]
        )
    )

    version = factory.LazyFunction(lambda: str(fake.random_int(min=1, max=5)))

    key_algorithm = factory.LazyFunction(
        lambda: fake.random_element(
            ["AES-256-GCM", "AES-256-CBC", "RSA-2048", "RSA-4096"]
        )
    )

    created_at = factory.LazyFunction(
        lambda: fake.date_time_between(
            start_date="-1y", end_date="-1d", tzinfo=timezone.utc
        )
    )

    activated_at = factory.LazyAttribute(
        lambda obj: (
            fake.date_time_between(
                start_date=obj.created_at, end_date="now", tzinfo=timezone.utc
            )
            if obj.status == KeyStatus.ACTIVE
            else None
        )
    )

    expires_at = factory.LazyAttribute(
        lambda obj: (
            obj.created_at + timedelta(days=365)
            if obj.key_type == KeyType.PHI_DATA
            else obj.created_at + timedelta(days=90)
        )
    )

    # Key relationships - set to None to avoid FK constraint violations
    parent_key_id = None

    last_used_at = factory.LazyFunction(
        lambda: fake.date_time_between(
            start_date="-30d", end_date="now", tzinfo=timezone.utc
        )
    )

    rotated_at = factory.LazyFunction(
        lambda: fake.random_element(
            [
                None,
                fake.date_time_between(
                    start_date="-90d", end_date="-1d", tzinfo=timezone.utc
                ),
            ]
        )
    )

    # Rollback support
    can_rollback = factory.LazyFunction(lambda: fake.boolean(chance_of_getting_true=80))

    rollback_expires_at = factory.LazyFunction(
        lambda: fake.random_element(
            [
                None,
                fake.date_time_between(
                    start_date="now", end_date="+30d", tzinfo=timezone.utc
                ),
            ]
        )
    )

    # Security and compliance
    key_purpose = factory.LazyFunction(
        lambda: fake.random_element(
            [
                None,
                "Database encryption",
                "File encryption",
                "Backup encryption",
                "Communication encryption",
            ]
        )
    )

    compliance_tags = factory.LazyFunction(
        lambda: fake.random_element(
            [None, ["HIPAA"], ["SOC2", "HIPAA"], ["PCI-DSS"], ["GDPR", "HIPAA"]]
        )
    )

    authorized_services = factory.LazyFunction(
        lambda: fake.random_element(
            [
                None,
                ["api-service", "backup-service"],
                ["web-app", "mobile-app"],
                ["reporting-service"],
            ]
        )
    )

    access_policy = factory.LazyFunction(
        lambda: fake.random_element([None, {"read": True, "write": False}])
    )

    # Token relationships - set to None to avoid FK constraint violations
    created_by_token_id = None
    rotated_by_token_id = None
    rotation_policy_id = None


class ActiveEncryptionKeyFactory(EncryptionKeyFactory):
    """Factory for active encryption keys."""

    status = KeyStatus.ACTIVE
    activated_at = factory.LazyFunction(
        lambda: fake.date_time_between(
            start_date="-30d", end_date="now", tzinfo=timezone.utc
        )
    )


class PHIKeyFactory(EncryptionKeyFactory):
    """Factory for PHI encryption keys."""

    key_type = KeyType.PHI_DATA
    key_name = factory.LazyFunction(
        lambda: f"phi-key-{fake.random_int(min=100, max=999)}"
    )
    status = KeyStatus.ACTIVE
    parent_key_id = None
    expires_at = factory.LazyAttribute(lambda obj: obj.created_at + timedelta(days=365))


class ClinicalKeyFactory(EncryptionKeyFactory):
    """Factory for clinical data encryption keys."""

    key_type = KeyType.CLINICAL
    key_name = factory.LazyFunction(
        lambda: f"clinical-key-{fake.random_int(min=100, max=999)}"
    )
    parent_key_id = factory.LazyFunction(lambda: uuid4())
    expires_at = factory.LazyAttribute(lambda obj: obj.created_at + timedelta(days=90))


class ExpiredKeyFactory(EncryptionKeyFactory):
    """Factory for expired encryption keys."""

    status = KeyStatus.EXPIRED
    created_at = factory.LazyFunction(
        lambda: fake.date_time_between(
            start_date="-2y", end_date="-1y", tzinfo=timezone.utc
        )
    )
    expires_at = factory.LazyAttribute(lambda obj: obj.created_at + timedelta(days=90))

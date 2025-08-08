"""Models package."""

# Import all models and make them available
# Import submodules to make them accessible via models.base, etc.
from . import (
    appointment,
    audit,
    auth_token,
    base,
    client,
    data_retention_policy,
    encryption_key,
    fhir_mapping,
    key_rotation_policy,
    ledger,
    legal_hold,
    location,
    note,
    practice_profile,
    provider,
    user,
)
from .appointment import Appointment
from .audit import AuditLog
from .auth_token import AuthToken, TokenStatus, TokenType
from .base import Base, BaseModel
from .client import Client
from .data_retention_policy import DataRetentionPolicy, DataType
from .data_retention_policy import PolicyStatus as RetentionPolicyStatus
from .data_retention_policy import RetentionPeriodUnit
from .encryption_key import EncryptionKey, KeyProvider, KeyStatus, KeyType
from .fhir_mapping import FHIRMapping, FHIRMappingStatus, FHIRResourceType
from .key_rotation_policy import KeyRotationPolicy
from .key_rotation_policy import PolicyStatus as KeyRotationPolicyStatus
from .key_rotation_policy import RotationTrigger
from .ledger import LedgerEntry
from .legal_hold import HoldReason, HoldStatus, LegalHold
from .location import Location
from .note import Note
from .practice_profile import PracticeProfile
from .provider import Provider
from .user import User

__all__ = [
    "Base",
    "BaseModel",
    "AuditLog",
    "AuthToken",
    "TokenStatus",
    "TokenType",
    "Client",
    "DataRetentionPolicy",
    "DataType",
    "RetentionPolicyStatus",
    "RetentionPeriodUnit",
    "EncryptionKey",
    "KeyType",
    "KeyStatus",
    "KeyProvider",
    "FHIRMapping",
    "FHIRResourceType",
    "FHIRMappingStatus",
    "KeyRotationPolicy",
    "RotationTrigger",
    "KeyRotationPolicyStatus",
    "LegalHold",
    "HoldStatus",
    "HoldReason",
    "Provider",
    "Appointment",
    "Note",
    "LedgerEntry",
    "PracticeProfile",
    "Location",
    "User",
    "base",
    "audit",
    "auth_token",
    "client",
    "data_retention_policy",
    "encryption_key",
    "fhir_mapping",
    "key_rotation_policy",
    "legal_hold",
    "provider",
    "appointment",
    "note",
    "ledger",
    "practice_profile",
    "location",
    "user",
]

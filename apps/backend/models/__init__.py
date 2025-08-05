"""Models package."""

# Import all models and make them available
# Import submodules to make them accessible via models.base, etc.
from . import (
    appointment,
    audit,
    auth_token,
    base,
    client,
    encryption_key,
    fhir_mapping,
    key_rotation_policy,
    ledger,
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
from .encryption_key import EncryptionKey, KeyProvider, KeyStatus, KeyType
from .fhir_mapping import FHIRMapping, FHIRMappingStatus, FHIRResourceType
from .key_rotation_policy import KeyRotationPolicy, PolicyStatus, RotationTrigger
from .ledger import LedgerEntry
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
    "EncryptionKey",
    "KeyType",
    "KeyStatus",
    "KeyProvider",
    "FHIRMapping",
    "FHIRResourceType",
    "FHIRMappingStatus",
    "KeyRotationPolicy",
    "RotationTrigger",
    "PolicyStatus",
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
    "encryption_key",
    "fhir_mapping",
    "key_rotation_policy",
    "provider",
    "appointment",
    "note",
    "ledger",
    "practice_profile",
    "location",
    "user",
]

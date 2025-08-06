"""Database service layer for CRUD operations."""

from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import SessionLocal
from models.appointment import Appointment, AppointmentStatus
from models.client import Client
from models.ledger import LedgerEntry
from models.note import Note
from models.provider import Provider

# Type alias for audit logger
AuditLogger = Callable[..., Any]


@contextmanager
def get_sync_session() -> Any:
    """Get a synchronous database session."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class DatabaseService:
    """Service layer for database operations with HIPAA compliance."""

    def __init__(
        self,
        session: Optional[AsyncSession] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        self.session = session
        self.audit_logger = audit_logger

    def _ensure_session(self) -> AsyncSession:
        if self.session is None:
            raise ValueError("Database session is required")
        return self.session

    def _log_action(
        self, action: str, resource_type: str, resource_id: str, **kwargs: Any
    ) -> None:
        if self.audit_logger:
            self.audit_logger(action, resource_type, resource_id, **kwargs)

    # Client operations
    async def create_client(self, client_data: Dict[str, Any]) -> Client:
        """Create a new client with audit logging."""
        session = self._ensure_session()
        client = Client(**client_data)
        session.add(client)
        await session.commit()

        self._log_action(
            action="CREATE",
            resource_type="Client",
            resource_id=str(client.id),
            new_values=client_data,
        )

        return client

    async def get_client(self, client_id: UUID) -> Optional[Client]:
        """Get client by ID."""
        result = await self.session.execute(
            select(Client).where(Client.id == client_id)
        )
        return result.scalar_one_or_none()

    async def list_clients(
        self, active_only: bool = True, limit: int = 100, offset: int = 0
    ) -> List[Client]:
        """List clients with pagination."""
        session = self._ensure_session()
        query = select(Client)

        if active_only:
            query = query.where(Client.is_active)

        query = query.limit(limit).offset(offset)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def update_client(
        self, client_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[Client]:
        """Update client with audit logging."""
        client = await self.get_client(client_id)
        if not client:
            return None

        session = self._ensure_session()
        old_values = {}
        for key, value in update_data.items():
            if hasattr(client, key):
                old_values[key] = getattr(client, key)
                setattr(client, key, value)

        await session.commit()

        self._log_action(
            action="UPDATE",
            resource_type="Client",
            resource_id=str(client.id),
            old_values=old_values,
            new_values=update_data,
        )

        return client

    # Provider operations
    async def create_provider(self, provider_data: Dict[str, Any]) -> Provider:
        """Create a new provider."""
        session = self._ensure_session()
        provider = Provider(**provider_data)
        session.add(provider)
        await session.commit()

        self._log_action(
            action="CREATE",
            resource_type="Provider",
            resource_id=str(provider.id),
            new_values=provider_data,
        )

        return provider

    async def get_provider(self, provider_id: UUID) -> Optional[Provider]:
        """Get provider by ID."""
        result = await self.session.execute(
            select(Provider).where(Provider.id == provider_id)
        )
        return result.scalar_one_or_none()

    async def list_providers(
        self, active_only: bool = True, specialty: Optional[str] = None
    ) -> List[Provider]:
        """List providers with optional filtering."""
        session = self._ensure_session()
        query = select(Provider)

        conditions = []
        if active_only:
            conditions.append(Provider.is_active)
        if specialty:
            conditions.append(Provider.specialty.ilike(f"%{specialty}%"))

        if conditions:
            query = query.where(and_(*conditions))

        result = await session.execute(query)
        return list(result.scalars().all())

    async def update_provider(
        self, provider_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[Provider]:
        """Update provider with audit logging."""
        provider = await self.get_provider(provider_id)
        if not provider:
            return None

        session = self._ensure_session()
        old_values = {}
        for key, value in update_data.items():
            if hasattr(provider, key):
                old_values[key] = getattr(provider, key)
                setattr(provider, key, value)

        await session.commit()

        self._log_action(
            action="UPDATE",
            resource_type="Provider",
            resource_id=str(provider.id),
            old_values=old_values,
            new_values=update_data,
        )

        return provider

    async def delete_provider(self, provider_id: UUID) -> bool:
        """Soft delete provider."""
        result = await self.update_provider(
            provider_id, {"is_active": False}
        )
        return result is not None

    # Appointment operations
    async def create_appointment(
        self, appointment_data: Dict[str, Any]
    ) -> Appointment:
        """Create a new appointment."""
        session = self._ensure_session()
        appointment = Appointment(**appointment_data)
        session.add(appointment)
        await session.commit()

        self._log_action(
            action="CREATE",
            resource_type="Appointment",
            resource_id=str(appointment.id),
            new_values=appointment_data,
        )

        return appointment

    async def get_appointment(
        self, appointment_id: UUID
    ) -> Optional[Appointment]:
        """Get appointment by ID with related data."""
        result = await self.session.execute(
            select(Appointment)
            .options(
                selectinload(Appointment.client),
                selectinload(Appointment.provider),
            )
            .where(Appointment.id == appointment_id)
        )
        return result.scalar_one_or_none()

    async def list_appointments_for_client(
        self, client_id: UUID, status: Optional[AppointmentStatus] = None
    ) -> List[Appointment]:
        """List appointments for a specific client."""
        session = self._ensure_session()
        query = select(Appointment).where(Appointment.client_id == client_id)

        if status:
            query = query.where(Appointment.status == status)

        query = query.order_by(Appointment.scheduled_start.desc())
        result = await session.execute(query)
        return list(result.scalars().all())

    async def update_appointment(
        self, appointment_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[Appointment]:
        """Update appointment with audit logging."""
        appointment = await self.get_appointment(appointment_id)
        if not appointment:
            return None

        session = self._ensure_session()
        old_values = {}
        for key, value in update_data.items():
            if hasattr(appointment, key):
                old_values[key] = getattr(appointment, key)
                setattr(appointment, key, value)

        await session.commit()

        self._log_action(
            action="UPDATE",
            resource_type="Appointment",
            resource_id=str(appointment.id),
            old_values=old_values,
            new_values=update_data,
        )

        return appointment

    async def delete_appointment(self, appointment_id: UUID) -> bool:
        """Delete appointment."""
        appointment = await self.get_appointment(appointment_id)
        if not appointment:
            return False

        session = self._ensure_session()
        await session.delete(appointment)
        await session.commit()

        self._log_action(
            action="DELETE",
            resource_type="Appointment",
            resource_id=str(appointment.id),
        )

        return True

    # Note operations
    async def create_note(self, note_data: Dict[str, Any]) -> Note:
        """Create a clinical note."""
        session = self._ensure_session()
        note = Note(**note_data)
        session.add(note)
        await session.commit()

        self._log_action(
            action="CREATE",
            resource_type="Note",
            resource_id=str(note.id),
            new_values=note_data,
        )

        return note

    async def get_notes_for_client(
        self, client_id: UUID, signed_only: bool = False
    ) -> List[Note]:
        """Get notes for a specific client."""
        session = self._ensure_session()
        query = select(Note).where(Note.client_id == client_id)

        if signed_only:
            query = query.where(Note.is_signed)

        query = query.order_by(Note.created_at.desc())
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_note(self, note_id: UUID) -> Optional[Note]:
        """Get note by ID."""
        result = await self.session.execute(
            select(Note).where(Note.id == note_id)
        )
        return result.scalar_one_or_none()

    async def update_note(
        self, note_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[Note]:
        """Update note with audit logging."""
        note = await self.get_note(note_id)
        if not note:
            return None

        session = self._ensure_session()
        old_values = {}
        for key, value in update_data.items():
            if hasattr(note, key):
                old_values[key] = getattr(note, key)
                setattr(note, key, value)

        await session.commit()

        self._log_action(
            action="UPDATE",
            resource_type="Note",
            resource_id=str(note.id),
            old_values=old_values,
            new_values=update_data,
        )

        return note

    async def delete_note(self, note_id: UUID) -> bool:
        """Delete note."""
        note = await self.get_note(note_id)
        if not note:
            return False

        session = self._ensure_session()
        await session.delete(note)
        await session.commit()

        self._log_action(
            action="DELETE",
            resource_type="Note",
            resource_id=str(note.id),
        )

        return True

    # Ledger operations
    async def create_ledger_entry(
        self, entry_data: Dict[str, Any]
    ) -> LedgerEntry:
        """Create a ledger entry for billing."""
        session = self._ensure_session()
        entry = LedgerEntry(**entry_data)
        session.add(entry)
        await session.commit()

        self._log_action(
            action="CREATE",
            resource_type="LedgerEntry",
            resource_id=str(entry.id),
            new_values=entry_data,
        )

        return entry

    async def get_ledger_entry(self, entry_id: UUID) -> Optional[LedgerEntry]:
        """Get ledger entry by ID."""
        result = await self.session.execute(
            select(LedgerEntry).where(LedgerEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def update_ledger_entry(
        self, entry_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[LedgerEntry]:
        """Update ledger entry with audit logging."""
        entry = await self.get_ledger_entry(entry_id)
        if not entry:
            return None

        session = self._ensure_session()
        old_values = {}
        for key, value in update_data.items():
            if hasattr(entry, key):
                old_values[key] = getattr(entry, key)
                setattr(entry, key, value)

        await session.commit()

        self._log_action(
            action="UPDATE",
            resource_type="LedgerEntry",
            resource_id=str(entry.id),
            old_values=old_values,
            new_values=update_data,
        )

        return entry

    async def delete_ledger_entry(self, entry_id: UUID) -> bool:
        """Delete ledger entry."""
        entry = await self.get_ledger_entry(entry_id)
        if not entry:
            return False

        session = self._ensure_session()
        await session.delete(entry)
        await session.commit()

        self._log_action(
            action="DELETE",
            resource_type="LedgerEntry",
            resource_id=str(entry.id),
        )

        return True

    async def get_client_balance(self, client_id: UUID) -> Dict[str, Any]:
        """Calculate client's account balance."""
        session = self._ensure_session()
        result = await session.execute(
            select(LedgerEntry).where(LedgerEntry.client_id == client_id)
        )
        entries = result.scalars().all()

        total_charges = sum(entry.amount for entry in entries if entry.is_charge())
        total_payments = sum(entry.amount for entry in entries if entry.is_payment())

        balance = total_charges - total_payments

        return {
            "client_id": str(client_id),
            "total_charges": str(total_charges),
            "total_payments": str(total_payments),
            "balance": str(balance),
            "entry_count": len(entries),
        }

    # Health check
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check."""
        try:
            session = self._ensure_session()
            # Test basic connectivity
            result = await session.execute(select(1))
            result.scalar()

            # Count records in main tables
            client_count = await session.execute(select(Client).where(Client.is_active))
            provider_count = await session.execute(
                select(Provider).where(Provider.is_active)
            )

            return {
                "status": "healthy",
                "active_clients": len(client_count.scalars().all()),
                "active_providers": len(provider_count.scalars().all()),
                "timestamp": "2025-01-01T00:00:00Z",
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "2025-01-01T00:00:00Z",
            }

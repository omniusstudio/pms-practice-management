"""Optimized database service with improved query patterns."""

from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database import SessionLocal
from models.appointment import Appointment, AppointmentStatus
from models.client import Client
from models.ledger import LedgerEntry, TransactionType
from models.note import Note
from models.provider import Provider

# Response models available for future use

# Type alias for audit logger
AuditLogger = Callable[..., Any]


class OptimizedDatabaseService:
    """Optimized database service with N+1 query prevention."""

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

    # Optimized Client operations
    async def get_client_with_relationships(
        self,
        client_id: UUID,
        include_appointments: bool = False,
        include_notes: bool = False,
        include_ledger: bool = False,
    ) -> Optional[Client]:
        """Get client with eagerly loaded relationships to prevent N+1."""
        session = self._ensure_session()

        query = select(Client).where(Client.id == client_id)

        # Eagerly load relationships based on requirements
        if include_appointments:
            query = query.options(selectinload(Client.appointments))
        if include_notes:
            query = query.options(selectinload(Client.notes))
        if include_ledger:
            query = query.options(selectinload(Client.ledger_entries))

        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def list_clients_optimized(
        self,
        page: int = 1,
        per_page: int = 50,
        active_only: bool = True,
        search_term: Optional[str] = None,
        include_stats: bool = False,
    ) -> Tuple[List[Client], int]:
        """Optimized client listing with search and optional statistics."""
        session = self._ensure_session()

        # Base query with conditions
        conditions = []
        if active_only:
            conditions.append(Client.is_active)

        if search_term:
            search_pattern = f"%{search_term}%"
            conditions.append(
                or_(
                    Client.first_name.ilike(search_pattern),
                    Client.last_name.ilike(search_pattern),
                    Client.email.ilike(search_pattern),
                )
            )

        # Count query for pagination
        count_query = select(func.count(Client.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))

        count_result = await session.execute(count_query)
        total_count = count_result.scalar()

        # Main query with pagination
        query = select(Client)
        if conditions:
            query = query.where(and_(*conditions))

        # Add statistics if requested (using subqueries to avoid N+1)
        if include_stats:
            query = query.options(
                selectinload(Client.appointments).selectinload(Appointment.provider),
                selectinload(Client.ledger_entries),
            )

        query = (
            query.order_by(Client.last_name, Client.first_name)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )

        result = await session.execute(query)
        clients = list(result.scalars().all())

        return clients, total_count

    # Optimized Appointment operations
    async def get_appointments_with_details(
        self,
        client_id: Optional[UUID] = None,
        provider_id: Optional[UUID] = None,
        status: Optional[AppointmentStatus] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> Tuple[List[Appointment], int]:
        """Get appointments with client and provider details."""
        session = self._ensure_session()

        # Build conditions
        conditions = []
        if client_id:
            conditions.append(Appointment.client_id == client_id)
        if provider_id:
            conditions.append(Appointment.provider_id == provider_id)
        if status:
            conditions.append(Appointment.status == status)
        if date_from:
            conditions.append(Appointment.scheduled_start >= date_from)
        if date_to:
            conditions.append(Appointment.scheduled_start <= date_to)

        # Count query
        count_query = select(func.count(Appointment.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))

        count_result = await session.execute(count_query)
        total_count = count_result.scalar()

        # Main query with eager loading
        query = select(Appointment).options(
            joinedload(Appointment.client),
            joinedload(Appointment.provider),
            selectinload(Appointment.notes),
        )

        if conditions:
            query = query.where(and_(*conditions))

        query = (
            query.order_by(Appointment.scheduled_start.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )

        result = await session.execute(query)
        appointments = list(result.scalars().all())

        return appointments, total_count

    async def get_provider_schedule_optimized(
        self, provider_id: UUID, date_from: str, date_to: str
    ) -> List[Appointment]:
        """Get provider schedule with minimal data for calendar view."""
        session = self._ensure_session()

        # Only select necessary fields for calendar view
        query = (
            select(Appointment)
            .options(
                joinedload(Appointment.client).load_only(
                    Client.first_name, Client.last_name
                )
            )
            .where(
                and_(
                    Appointment.provider_id == provider_id,
                    Appointment.scheduled_start >= date_from,
                    Appointment.scheduled_start <= date_to,
                    Appointment.status.in_(
                        [
                            AppointmentStatus.SCHEDULED,
                            AppointmentStatus.CONFIRMED,
                            AppointmentStatus.IN_PROGRESS,
                        ]
                    ),
                )
            )
            .order_by(Appointment.scheduled_start)
        )

        result = await session.execute(query)
        return list(result.scalars().all())

    # Optimized Financial operations
    async def get_client_financial_summary(self, client_id: UUID) -> Dict[str, Any]:
        """Get client financial summary using aggregation queries."""
        session = self._ensure_session()

        # Single query with aggregations
        query = select(
            func.sum(
                func.case(
                    (
                        LedgerEntry.transaction_type == TransactionType.CHARGE,
                        LedgerEntry.amount,
                    ),
                    0,
                )
            ).label("total_charges"),
            func.sum(
                func.case(
                    (
                        LedgerEntry.transaction_type == TransactionType.PAYMENT,
                        LedgerEntry.amount,
                    ),
                    0,
                )
            ).label("total_payments"),
            func.count(LedgerEntry.id).label("entry_count"),
            func.max(LedgerEntry.service_date).label("last_service_date"),
        ).where(and_(LedgerEntry.client_id == client_id, LedgerEntry.is_posted))

        result = await session.execute(query)
        row = result.first()

        total_charges = row.total_charges or 0
        total_payments = row.total_payments or 0
        balance = total_charges - total_payments

        return {
            "client_id": str(client_id),
            "total_charges": float(total_charges),
            "total_payments": float(total_payments),
            "balance": float(balance),
            "entry_count": row.entry_count or 0,
            "last_service_date": (
                row.last_service_date.isoformat() if row.last_service_date else None
            ),
        }

    async def get_financial_dashboard_data(
        self, date_from: str, date_to: str
    ) -> Dict[str, Any]:
        """Get financial dashboard data with optimized aggregations."""
        session = self._ensure_session()

        # Revenue by day
        revenue_query = (
            select(
                func.date(LedgerEntry.service_date).label("date"),
                func.sum(LedgerEntry.amount).label("revenue"),
            )
            .where(
                and_(
                    LedgerEntry.transaction_type == TransactionType.CHARGE,
                    LedgerEntry.service_date >= date_from,
                    LedgerEntry.service_date <= date_to,
                    LedgerEntry.is_posted,
                )
            )
            .group_by(func.date(LedgerEntry.service_date))
            .order_by(func.date(LedgerEntry.service_date))
        )

        revenue_result = await session.execute(revenue_query)
        daily_revenue = [
            {"date": row.date.isoformat(), "revenue": float(row.revenue)}
            for row in revenue_result
        ]

        # Outstanding balances
        balance_query = (
            select(
                Client.id,
                Client.first_name,
                Client.last_name,
                func.sum(
                    func.case(
                        (
                            LedgerEntry.transaction_type == TransactionType.CHARGE,
                            LedgerEntry.amount,
                        ),
                        -LedgerEntry.amount,
                    )
                ).label("balance"),
            )
            .join(LedgerEntry, Client.id == LedgerEntry.client_id)
            .where(LedgerEntry.is_posted)
            .group_by(Client.id, Client.first_name, Client.last_name)
            .having(
                func.sum(
                    func.case(
                        (
                            LedgerEntry.transaction_type == TransactionType.CHARGE,
                            LedgerEntry.amount,
                        ),
                        -LedgerEntry.amount,
                    )
                )
                > 0
            )
            .order_by(
                func.sum(
                    func.case(
                        (
                            LedgerEntry.transaction_type == TransactionType.CHARGE,
                            LedgerEntry.amount,
                        ),
                        -LedgerEntry.amount,
                    )
                ).desc()
            )
            .limit(10)
        )

        balance_result = await session.execute(balance_query)
        outstanding_balances = [
            {
                "client_id": str(row.id),
                "client_name": f"{row.first_name} {row.last_name}",
                "balance": float(row.balance),
            }
            for row in balance_result
        ]

        return {
            "daily_revenue": daily_revenue,
            "outstanding_balances": outstanding_balances,
        }

    # Database health and performance monitoring
    async def get_database_performance_stats(self) -> Dict[str, Any]:
        """Get database performance statistics."""
        session = self._ensure_session()

        # Table sizes and counts
        stats_queries = {
            "clients": select(func.count(Client.id)),
            "providers": select(func.count(Provider.id)),
            "appointments": select(func.count(Appointment.id)),
            "notes": select(func.count(Note.id)),
            "ledger_entries": select(func.count(LedgerEntry.id)),
        }

        stats: Dict[str, Any] = {}
        for table_name, query in stats_queries.items():
            result = await session.execute(query)
            stats[f"{table_name}_count"] = result.scalar()

        # Recent activity (last 24 hours)
        from datetime import datetime, timedelta

        yesterday = datetime.utcnow() - timedelta(days=1)

        recent_activity_query = (
            select(
                func.count(Appointment.id).label("recent_appointments"),
                func.count(Note.id).label("recent_notes"),
            )
            .select_from(Appointment.__table__.outerjoin(Note.__table__))
            .where(
                or_(Appointment.created_at >= yesterday, Note.created_at >= yesterday)
            )
        )

        activity_result = await session.execute(recent_activity_query)
        activity_row = activity_result.first()

        if activity_row:
            stats.update(
                {
                    "recent_appointments": activity_row.recent_appointments or 0,
                    "recent_notes": activity_row.recent_notes or 0,
                }
            )
        else:
            stats.update({"recent_appointments": 0, "recent_notes": 0})

        stats["timestamp"] = datetime.utcnow().isoformat()

        return stats


@contextmanager
def get_optimized_sync_session() -> Any:
    """Get an optimized synchronous database session."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

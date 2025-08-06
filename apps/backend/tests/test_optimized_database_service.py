"""Tests for OptimizedDatabaseService."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from models.appointment import Appointment, AppointmentStatus
from models.client import Client
from models.ledger import TransactionType
from services.optimized_database_service import (
    OptimizedDatabaseService,
    get_optimized_sync_session,
)


class TestOptimizedDatabaseService:
    """Test cases for OptimizedDatabaseService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def mock_audit_logger(self):
        """Create a mock audit logger."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_session, mock_audit_logger):
        """Create OptimizedDatabaseService instance."""
        return OptimizedDatabaseService(
            session=mock_session, audit_logger=mock_audit_logger
        )

    @pytest.fixture
    def service_no_session(self):
        """Create OptimizedDatabaseService without session."""
        return OptimizedDatabaseService()

    def test_init_with_session_and_logger(self, mock_session, mock_audit_logger):
        """Test initialization with session and audit logger."""
        service = OptimizedDatabaseService(
            session=mock_session, audit_logger=mock_audit_logger
        )
        assert service.session == mock_session
        assert service.audit_logger == mock_audit_logger

    def test_init_without_session(self):
        """Test initialization without session."""
        service = OptimizedDatabaseService()
        assert service.session is None
        assert service.audit_logger is None

    def test_ensure_session_with_session(self, service, mock_session):
        """Test _ensure_session when session exists."""
        result = service._ensure_session()
        assert result == mock_session

    def test_ensure_session_without_session(self, service_no_session):
        """Test _ensure_session when session is None."""
        with pytest.raises(ValueError, match="Database session is required"):
            service_no_session._ensure_session()

    def test_log_action_with_logger(self, service, mock_audit_logger):
        """Test _log_action when audit logger exists."""
        service._log_action("create", "client", "123", extra_data="test")
        mock_audit_logger.assert_called_once_with(
            "create", "client", "123", extra_data="test"
        )

    def test_log_action_without_logger(self, mock_session):
        """Test _log_action when audit logger is None."""
        service = OptimizedDatabaseService(session=mock_session)
        # Should not raise an exception
        service._log_action("create", "client", "123")

    @pytest.mark.asyncio
    async def test_get_client_with_relationships_basic(self, service, mock_session):
        """Test get_client_with_relationships with basic options."""
        client_id = uuid4()
        mock_client = MagicMock(spec=Client)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_client
        mock_session.execute.return_value = mock_result

        result = await service.get_client_with_relationships(client_id)

        assert result == mock_client
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_client_with_relationships_all_includes(
        self, service, mock_session
    ):
        """Test get_client_with_relationships with all includes."""
        client_id = uuid4()
        mock_client = MagicMock(spec=Client)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_client
        mock_session.execute.return_value = mock_result

        result = await service.get_client_with_relationships(
            client_id,
            include_appointments=True,
            include_notes=True,
            include_ledger=True,
        )

        assert result == mock_client
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_clients_optimized_basic(self, service, mock_session):
        """Test list_clients_optimized with basic parameters."""
        mock_clients = [MagicMock(spec=Client) for _ in range(3)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_clients

        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 10
        mock_session.execute.side_effect = [mock_count_result, mock_result]

        clients, total = await service.list_clients_optimized()

        assert len(clients) == 3
        assert total == 10
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_list_clients_optimized_with_search(self, service, mock_session):
        """Test list_clients_optimized with search term."""
        mock_clients = [MagicMock(spec=Client)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_clients
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_session.execute.side_effect = [mock_count_result, mock_result]

        clients, total = await service.list_clients_optimized(
            search_term="john", include_stats=True
        )

        assert len(clients) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_appointments_with_details(self, service, mock_session):
        """Test get_appointments_with_details."""
        mock_appointments = [MagicMock(spec=Appointment) for _ in range(2)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_appointments
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 5
        mock_session.execute.side_effect = [mock_count_result, mock_result]

        appointments, total = await service.get_appointments_with_details(
            client_id=uuid4(),
            provider_id=uuid4(),
            status=AppointmentStatus.SCHEDULED,
            date_from="2024-01-01",
            date_to="2024-12-31",
        )

        assert len(appointments) == 2
        assert total == 5

    @pytest.mark.asyncio
    async def test_get_provider_schedule_optimized(self, service, mock_session):
        """Test get_provider_schedule_optimized."""
        provider_id = uuid4()
        mock_appointments = [MagicMock(spec=Appointment) for _ in range(3)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_appointments
        mock_session.execute.return_value = mock_result

        result = await service.get_provider_schedule_optimized(
            provider_id, "2024-01-01", "2024-01-31"
        )

        assert result == mock_appointments
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_client_financial_summary(self, service, mock_session):
        """Test get_client_financial_summary."""
        client_id = uuid4()

        # Mock the ledger entries query
        mock_ledger_result = MagicMock()
        mock_ledger_result.scalars.return_value.all.return_value = [
            MagicMock(
                transaction_type=TransactionType.CHARGE, amount=Decimal("100.00")
            ),
            MagicMock(
                transaction_type=TransactionType.PAYMENT, amount=Decimal("50.00")
            ),
        ]

        # Mock the appointments query
        mock_appt_result = MagicMock()
        mock_appt_result.scalars.return_value.all.return_value = [
            MagicMock(status=AppointmentStatus.COMPLETED),
            MagicMock(status=AppointmentStatus.SCHEDULED),
        ]

        mock_session.execute.side_effect = [mock_ledger_result, mock_appt_result]

        result = await service.get_client_financial_summary(client_id)

        assert "total_charges" in result
        assert "total_payments" in result
        assert "balance" in result
        assert "client_id" in result
        assert "entry_count" in result
        assert "last_service_date" in result

    @pytest.mark.asyncio
    async def test_get_financial_dashboard_data(self, service, mock_session):
        """Test get_financial_dashboard_data."""
        # Mock revenue query
        mock_revenue_result = MagicMock()
        mock_revenue_result.scalars.return_value.all.return_value = [
            MagicMock(amount=Decimal("1000.00")),
            MagicMock(amount=Decimal("500.00")),
        ]

        # Mock appointments query
        mock_appt_result = MagicMock()
        mock_appt_result.scalars.return_value.all.return_value = [
            MagicMock(status=AppointmentStatus.COMPLETED),
            MagicMock(status=AppointmentStatus.SCHEDULED),
        ]

        # Mock outstanding balances query
        mock_balance_result = MagicMock()
        mock_balance_result.scalars.return_value.all.return_value = [
            MagicMock(balance=Decimal("200.00")),
            MagicMock(balance=Decimal("300.00")),
        ]

        mock_session.execute.side_effect = [
            mock_revenue_result,
            mock_appt_result,
            mock_balance_result,
        ]

        result = await service.get_financial_dashboard_data("2024-01-01", "2024-12-31")

        assert "daily_revenue" in result
        assert "outstanding_balances" in result
        assert isinstance(result["daily_revenue"], list)
        assert isinstance(result["outstanding_balances"], list)

    @pytest.mark.asyncio
    async def test_get_database_performance_stats(self, service, mock_session):
        """Test get_database_performance_stats."""
        # Mock scalar queries for table counts
        mock_scalar_result = MagicMock()
        mock_scalar_result.scalar.return_value = 100

        # Mock activity query result
        mock_activity_result = MagicMock()
        mock_activity_row = MagicMock()
        mock_activity_row.recent_appointments = 5
        mock_activity_row.recent_notes = 3
        mock_activity_result.first.return_value = mock_activity_row

        # Set up side_effect for multiple execute calls
        mock_session.execute.side_effect = [
            mock_scalar_result,  # clients count
            mock_scalar_result,  # providers count
            mock_scalar_result,  # appointments count
            mock_scalar_result,  # notes count
            mock_scalar_result,  # ledger_entries count
            mock_activity_result,  # activity query
        ]

        result = await service.get_database_performance_stats()

        assert "clients_count" in result
        assert "providers_count" in result
        assert "appointments_count" in result
        assert "notes_count" in result
        assert "ledger_entries_count" in result
        assert "recent_appointments" in result
        assert "recent_notes" in result
        assert "timestamp" in result


def test_get_optimized_sync_session():
    """Test get_optimized_sync_session context manager."""
    with patch(
        "services.optimized_database_service.SessionLocal"
    ) as mock_session_local:
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        with get_optimized_sync_session() as session:
            assert session == mock_session

        mock_session.close.assert_called_once()


def test_get_optimized_sync_session_with_exception():
    """Test get_optimized_sync_session handles exceptions properly."""
    with patch(
        "services.optimized_database_service.SessionLocal"
    ) as mock_session_local:
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        try:
            with get_optimized_sync_session() as session:
                assert session == mock_session
                raise ValueError("Test exception")
        except ValueError:
            pass

        mock_session.close.assert_called_once()

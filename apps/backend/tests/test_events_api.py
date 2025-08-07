"""Tests for events API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.events import (
    ETLStatusResponse,
    EventBusStatusResponse,
    PublishEventRequest,
    PublishEventResponse,
    get_etl_service,
    get_event_bus_service,
    get_event_types,
    publish_event,
    router,
)
from schemas.events import EventSeverity, EventType

try:
    from main import app
except ImportError:
    from fastapi import FastAPI

    app = FastAPI()


class TestEventsAPI:
    """Test cases for events API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus service."""
        mock_bus = AsyncMock()
        mock_bus.publish_event.return_value = str(uuid4())
        mock_bus._redis = MagicMock()  # Simulate connected state
        mock_bus.environment = "test"
        mock_bus._subscribers = ["subscriber1", "subscriber2"]
        mock_bus.get_stream_info.return_value = {
            "length": 100,
            "first_entry_id": "1234567890-0",
            "last_entry_id": "1234567891-0",
        }
        return mock_bus

    @pytest.fixture
    def mock_etl_service(self):
        """Mock ETL service."""
        mock_etl = MagicMock()
        mock_etl.get_metrics.return_value = {
            "running": True,
            "events_processed": 1000,
            "batches_processed": 50,
            "errors_count": 2,
            "buffer_size": 25,
            "environment": "test",
            "s3_bucket": "test-bucket",
        }
        return mock_etl

    @pytest.fixture
    def sample_crud_event_request(self):
        """Sample CRUD event request data."""
        return {
            "event_type": EventType.USER_UPDATED,
            "resource_type": "patient",
            "resource_id": "patient-123",
            "severity": EventSeverity.MEDIUM,
            "metadata": {"source": "api"},
            "user_id": "user-456",
            "operation": "UPDATE",
            "changes": {"name": "John Doe"},
        }

    @pytest.fixture
    def sample_auth_event_request(self):
        """Sample auth event request data."""
        return {
            "event_type": EventType.USER_CREATED,
            "resource_type": "user",
            "resource_id": "user-123",
            "severity": EventSeverity.LOW,
            "metadata": {"source": "auth"},
            "user_id": "user-123",
            "auth_type": "LOGIN",
            "success": True,
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
        }

    @pytest.fixture
    def sample_system_event_request(self):
        """Sample system event request data."""
        return {
            "event_type": EventType.SYSTEM_ERROR,
            "resource_type": "system",
            "resource_id": "component-123",
            "severity": EventSeverity.HIGH,
            "metadata": {"source": "system"},
            "user_id": None,
            "component": "database",
            "error_code": "DB_CONNECTION_FAILED",
            "stack_trace": "Traceback...",
        }

    @pytest.fixture
    def sample_business_event_request(self):
        """Sample business event request data."""
        return {
            "event_type": EventType.APPOINTMENT_SCHEDULED,
            "resource_type": "appointment",
            "resource_id": "appt-123",
            "severity": EventSeverity.LOW,
            "metadata": {"source": "scheduler"},
            "user_id": "user-456",
            "business_process": "appointment_booking",
            "outcome": "SUCCESS",
            "duration_ms": 1500,
        }

    @pytest.mark.asyncio
    async def test_publish_crud_event_success(
        self, sample_crud_event_request, mock_event_bus
    ):
        """Test successful CRUD event publishing."""
        request = PublishEventRequest(**sample_crud_event_request)
        correlation_id = "test-correlation-id"

        with patch("api.events.logger") as mock_logger:
            response = await publish_event(
                request=request,
                correlation_id=correlation_id,
                event_bus=mock_event_bus,
            )

        assert isinstance(response, PublishEventResponse)
        assert response.correlation_id == correlation_id
        assert response.status == "published"

        # Verify event bus was called
        mock_event_bus.publish_event.assert_called_once()
        published_event = mock_event_bus.publish_event.call_args[0][0]
        assert published_event.event_type == EventType.USER_UPDATED
        assert published_event.operation == "UPDATE"
        assert published_event.changes == {"name": "John Doe"}

        # Verify logging
        mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_auth_event_success(
        self, sample_auth_event_request, mock_event_bus
    ):
        """Test successful auth event publishing."""
        request = PublishEventRequest(**sample_auth_event_request)
        correlation_id = "test-correlation-id"

        response = await publish_event(
            request=request,
            correlation_id=correlation_id,
            event_bus=mock_event_bus,
        )

        assert isinstance(response, PublishEventResponse)

        # Verify event bus was called with auth event
        published_event = mock_event_bus.publish_event.call_args[0][0]
        assert published_event.auth_type == "LOGIN"
        assert published_event.success is True
        assert published_event.ip_address == "192.168.1.1"
        assert published_event.user_agent == "Mozilla/5.0"

    @pytest.mark.asyncio
    async def test_publish_system_event_success(
        self, sample_system_event_request, mock_event_bus
    ):
        """Test successful system event publishing."""
        request = PublishEventRequest(**sample_system_event_request)
        correlation_id = "test-correlation-id"

        response = await publish_event(
            request=request,
            correlation_id=correlation_id,
            event_bus=mock_event_bus,
        )

        assert isinstance(response, PublishEventResponse)

        # Verify event bus was called with system event
        published_event = mock_event_bus.publish_event.call_args[0][0]
        assert published_event.component == "database"
        assert published_event.error_code == "DB_CONNECTION_FAILED"
        assert published_event.stack_trace == "Traceback..."

    @pytest.mark.asyncio
    async def test_publish_business_event_success(
        self, sample_business_event_request, mock_event_bus
    ):
        """Test successful business event publishing."""
        request = PublishEventRequest(**sample_business_event_request)
        correlation_id = "test-correlation-id"

        response = await publish_event(
            request=request,
            correlation_id=correlation_id,
            event_bus=mock_event_bus,
        )

        assert isinstance(response, PublishEventResponse)

        # Verify event bus was called with business event
        published_event = mock_event_bus.publish_event.call_args[0][0]
        assert published_event.business_process == "appointment_booking"
        assert published_event.outcome == "SUCCESS"
        assert published_event.duration_ms == 1500

    @pytest.mark.asyncio
    async def test_publish_base_event_success(self, mock_event_bus):
        """Test successful base event publishing."""
        request_data = {
            "event_type": EventType.SYSTEM_ERROR,
            "resource_type": "system",
            "resource_id": "system-1",
            "severity": EventSeverity.LOW,
            "metadata": {"source": "system"},
            "user_id": None,
        }
        request = PublishEventRequest(**request_data)
        correlation_id = "test-correlation-id"

        response = await publish_event(
            request=request,
            correlation_id=correlation_id,
            event_bus=mock_event_bus,
        )

        assert isinstance(response, PublishEventResponse)

        # Verify event bus was called with base event
        published_event = mock_event_bus.publish_event.call_args[0][0]
        assert published_event.event_type == EventType.SYSTEM_ERROR

    @pytest.mark.asyncio
    async def test_publish_event_failure(
        self, sample_crud_event_request, mock_event_bus
    ):
        """Test event publishing failure."""
        mock_event_bus.publish_event.side_effect = Exception("Bus error")

        request = PublishEventRequest(**sample_crud_event_request)
        correlation_id = "test-correlation-id"

        with patch("api.events.logger") as mock_logger:
            with pytest.raises(HTTPException) as exc_info:
                await publish_event(
                    request=request,
                    correlation_id=correlation_id,
                    event_bus=mock_event_bus,
                )

        assert exc_info.value.status_code == 500
        assert "Event publishing failed" in str(exc_info.value.detail)

        # Verify error logging
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_event_bus_status_success(self, mock_event_bus):
        """Test successful event bus status retrieval."""
        from api.events import get_event_bus_status

        response = await get_event_bus_status(event_bus=mock_event_bus)

        assert isinstance(response, EventBusStatusResponse)
        assert response.connected is True
        assert response.environment == "test"
        assert response.subscribers == 2
        assert response.stream_info["length"] == 100

    @pytest.mark.asyncio
    async def test_get_event_bus_status_failure(self, mock_event_bus):
        """Test event bus status retrieval failure."""
        from api.events import get_event_bus_status

        mock_event_bus.get_stream_info.side_effect = Exception("Status error")

        with patch("api.events.logger") as mock_logger:
            with pytest.raises(HTTPException) as exc_info:
                await get_event_bus_status(event_bus=mock_event_bus)

        assert exc_info.value.status_code == 500
        assert "Status retrieval failed" in str(exc_info.value.detail)

        # Verify error logging
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_etl_status_success(self, mock_etl_service):
        """Test successful ETL status retrieval."""
        from api.events import get_etl_status

        response = await get_etl_status(etl_pipeline=mock_etl_service)

        assert isinstance(response, ETLStatusResponse)
        assert response.running is True
        assert response.events_processed == 1000
        assert response.batches_processed == 50
        assert response.errors_count == 2
        assert response.buffer_size == 25
        assert response.environment == "test"
        assert response.s3_bucket == "test-bucket"

    @pytest.mark.asyncio
    async def test_get_etl_status_failure(self, mock_etl_service):
        """Test ETL status retrieval failure."""
        from api.events import get_etl_status

        mock_etl_service.get_metrics.side_effect = Exception("ETL error")

        with patch("api.events.logger") as mock_logger:
            with pytest.raises(HTTPException) as exc_info:
                await get_etl_status(etl_pipeline=mock_etl_service)

        assert exc_info.value.status_code == 500
        assert "ETL status retrieval failed" in str(exc_info.value.detail)

        # Verify error logging
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_etl_pipeline_success(self, mock_etl_service):
        """Test successful ETL pipeline start."""
        from fastapi import BackgroundTasks

        from api.events import start_etl_pipeline

        background_tasks = BackgroundTasks()

        with patch("api.events.logger") as mock_logger:
            response = await start_etl_pipeline(
                background_tasks=background_tasks,
                etl_pipeline=mock_etl_service,
            )

        assert response["status"] == "starting"
        assert "ETL pipeline start initiated" in response["message"]

        # Verify logging
        mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_etl_pipeline_failure(self, mock_etl_service):
        """Test ETL pipeline start failure."""
        from fastapi import BackgroundTasks

        from api.events import start_etl_pipeline

        background_tasks = BackgroundTasks()

        with patch("api.events.logger") as mock_logger:
            with patch.object(
                background_tasks,
                "add_task",
                side_effect=Exception("Start error"),
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await start_etl_pipeline(
                        background_tasks=background_tasks,
                        etl_pipeline=mock_etl_service,
                    )

        assert exc_info.value.status_code == 500
        assert "ETL pipeline start failed" in str(exc_info.value.detail)

        # Verify error logging
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_etl_pipeline_success(self, mock_etl_service):
        """Test successful ETL pipeline stop."""
        from fastapi import BackgroundTasks

        from api.events import stop_etl_pipeline

        background_tasks = BackgroundTasks()

        with patch("api.events.logger") as mock_logger:
            response = await stop_etl_pipeline(
                background_tasks=background_tasks,
                etl_pipeline=mock_etl_service,
            )

        assert response["status"] == "stopping"
        assert "ETL pipeline stop initiated" in response["message"]

        # Verify logging
        mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_etl_pipeline_failure(self, mock_etl_service):
        """Test ETL pipeline stop failure."""
        from fastapi import BackgroundTasks

        from api.events import stop_etl_pipeline

        background_tasks = BackgroundTasks()

        with patch("api.events.logger") as mock_logger:
            with patch.object(
                background_tasks,
                "add_task",
                side_effect=Exception("Stop error"),
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await stop_etl_pipeline(
                        background_tasks=background_tasks,
                        etl_pipeline=mock_etl_service,
                    )

        assert exc_info.value.status_code == 500
        assert "ETL pipeline stop failed" in str(exc_info.value.detail)

        # Verify error logging
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_event_types(self):
        """Test get_event_types endpoint."""
        response = await get_event_types()

        assert "event_types" in response
        assert "severities" in response
        assert isinstance(response["event_types"], list)
        assert isinstance(response["severities"], list)

        # Verify some expected values
        event_types = response["event_types"]
        severities = response["severities"]

        assert "user.created" in event_types
        assert "user.updated" in event_types
        assert "low" in severities
        assert "high" in severities

    def test_publish_event_request_model_validation(self):
        """Test PublishEventRequest model validation."""
        # Valid minimal request
        valid_data = {
            "event_type": EventType.USER_CREATED,
            "resource_type": "user",
            "resource_id": "user-123",
        }
        request = PublishEventRequest(**valid_data)
        assert request.event_type == EventType.USER_CREATED
        assert request.severity == EventSeverity.LOW  # Default value
        assert request.metadata == {}  # Default value

    def test_publish_event_response_model(self):
        """Test PublishEventResponse model."""
        event_id = str(uuid4())
        correlation_id = "test-correlation-id"

        response = PublishEventResponse(
            event_id=event_id,
            correlation_id=correlation_id,
        )

        assert response.event_id == event_id
        assert response.correlation_id == correlation_id
        assert response.status == "published"  # Default value

    def test_event_bus_status_response_model(self):
        """Test EventBusStatusResponse model."""
        response = EventBusStatusResponse(
            connected=True,
            environment="test",
            stream_info={"length": 100},
            subscribers=2,
        )

        assert response.connected is True
        assert response.environment == "test"
        stream_info = getattr(response, "stream_info", {})
        assert stream_info.get("length") == 100
        assert response.subscribers == 2

    def test_etl_status_response_model(self):
        """Test ETLStatusResponse model."""
        response = ETLStatusResponse(
            running=True,
            events_processed=1000,
            batches_processed=50,
            errors_count=2,
            buffer_size=25,
            environment="test",
            s3_bucket="test-bucket",
        )

        assert response.running is True
        assert response.events_processed == 1000
        assert response.batches_processed == 50
        assert response.errors_count == 2
        assert response.buffer_size == 25
        assert response.environment == "test"
        assert response.s3_bucket == "test-bucket"

    @pytest.mark.asyncio
    async def test_dependency_injection_functions(self):
        """Test dependency injection functions."""
        # Test get_event_bus_service
        with patch("api.events.get_event_bus") as mock_get_bus:
            mock_bus = AsyncMock()
            mock_get_bus.return_value = mock_bus

            result = await get_event_bus_service()
            assert result == mock_bus
            mock_get_bus.assert_called_once()

        # Test get_etl_service
        with patch("api.events.get_etl_pipeline") as mock_get_etl:
            mock_etl = AsyncMock()
            mock_get_etl.return_value = mock_etl

            result = await get_etl_service()
            assert result == mock_etl
            mock_get_etl.assert_called_once()

    def test_router_configuration(self):
        """Test router configuration."""
        assert router.prefix == "/events"
        assert "events" in router.tags

    @pytest.mark.asyncio
    async def test_publish_event_with_default_outcome(self, mock_event_bus):
        """Test business event with default outcome."""
        request_data = {
            "event_type": EventType.APPOINTMENT_SCHEDULED,
            "resource_type": "appointment",
            "resource_id": "appt-123",
            "business_process": "appointment_booking",
            # outcome not provided, should default to "SUCCESS"
        }
        request = PublishEventRequest(**request_data)
        correlation_id = "test-correlation-id"

        response = await publish_event(
            request=request,
            correlation_id=correlation_id,
            event_bus=mock_event_bus,
        )

        assert isinstance(response, PublishEventResponse)

        # Verify default outcome is set
        published_event = mock_event_bus.publish_event.call_args[0][0]
        assert published_event.outcome == "SUCCESS"

    @pytest.mark.asyncio
    async def test_publish_event_with_default_success(self, mock_event_bus):
        """Test auth event with default success value."""
        request_data = {
            "event_type": EventType.USER_CREATED,
            "resource_type": "user",
            "resource_id": "user-123",
            "auth_type": "LOGIN",
            # success not provided, should default to False
        }
        request = PublishEventRequest(**request_data)
        correlation_id = "test-correlation-id"

        response = await publish_event(
            request=request,
            correlation_id=correlation_id,
            event_bus=mock_event_bus,
        )

        assert isinstance(response, PublishEventResponse)

        # Verify default success is set
        published_event = mock_event_bus.publish_event.call_args[0][0]
        assert published_event.success is False

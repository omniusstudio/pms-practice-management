"""Tests for logging middleware."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request, Response
from starlette.datastructures import Headers

from middleware.logging import CorrelationIDMiddleware, get_correlation_id


class TestCorrelationIDMiddleware:
    """Test cases for CorrelationIDMiddleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        return CorrelationIDMiddleware(app=MagicMock())

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/test"
        request.headers = Headers({"user-agent": "test-agent"})
        request.state = MagicMock()
        return request

    @pytest.fixture
    def mock_response(self):
        """Create mock response."""
        response = MagicMock(spec=Response)
        response.status_code = 200
        response.headers = {}
        return response

    @pytest.mark.asyncio
    async def test_dispatch_with_existing_correlation_id(
        self, middleware, mock_request, mock_response
    ):
        """Test dispatch creates new correlation ID when none provided."""
        # Setup
        mock_request.headers = {"user-agent": "test-agent"}
        call_next = AsyncMock(return_value=mock_response)

        with patch("middleware.logging.logger") as mock_logger:
            with patch("middleware.logging.time.time", side_effect=[1000.0, 1001.5]):
                with patch(
                    "middleware.logging.uuid.uuid4",
                    return_value=uuid.UUID("12345678-1234-5678-9012-123456789012"),
                ):
                    result = await middleware.dispatch(mock_request, call_next)

                    # Verify correlation ID was set
                    expected_id = "12345678-1234-5678-9012-123456789012"
                    assert mock_request.state.correlation_id == expected_id
                    assert result.headers["X-Correlation-ID"] == expected_id

                    # Verify logging calls
                    assert mock_logger.bind.called
                    bind_call = mock_logger.bind.call_args[1]
                    assert bind_call["correlation_id"] == expected_id
                    assert bind_call["method"] == "GET"
                    assert bind_call["path"] == "/api/test"
                    assert bind_call["user_agent"] == "test-agent"

    @pytest.mark.asyncio
    async def test_dispatch_uses_existing_correlation_id_from_headers(
        self, middleware, mock_request, mock_response
    ):
        """Test dispatch uses existing correlation ID from headers."""
        # Setup
        existing_id = "existing-correlation-id"
        mock_request.headers = Headers(
            {
                "X-Correlation-ID": existing_id,
                "user-agent": "test-agent",
            }
        )
        call_next = AsyncMock(return_value=mock_response)

        with patch("middleware.logging.logger") as mock_logger:
            with patch("middleware.logging.time.time", side_effect=[1000.0, 1001.5]):
                result = await middleware.dispatch(mock_request, call_next)

                # Verify existing correlation ID was used
                assert mock_request.state.correlation_id == existing_id
                assert result.headers["X-Correlation-ID"] == existing_id

                # Verify logging calls
                bind_call = mock_logger.bind.call_args[1]
                assert bind_call["correlation_id"] == existing_id

    @pytest.mark.asyncio
    async def test_dispatch_logs_request_start_and_completion(
        self, middleware, mock_request, mock_response
    ):
        """Test that request start and completion are logged."""
        call_next = AsyncMock(return_value=mock_response)

        with patch("middleware.logging.logger") as mock_logger:
            mock_logger_with_context = MagicMock()
            mock_logger.bind.return_value = mock_logger_with_context

            with patch("middleware.logging.time.time", side_effect=[1000.0, 1001.5]):
                await middleware.dispatch(mock_request, call_next)

                # Verify request start logging
                start_call = mock_logger_with_context.info.call_args_list[0]
                assert start_call[0][0] == "Request started"
                assert start_call[1]["request_start"] is True
                assert start_call[1]["timestamp"] == 1000.0

                # Verify request completion logging
                complete_call = mock_logger_with_context.info.call_args_list[1]
                assert complete_call[0][0] == "Request completed"
                assert complete_call[1]["request_complete"] is True
                assert complete_call[1]["status_code"] == 200
                assert complete_call[1]["duration_ms"] == 1500.0

    @pytest.mark.asyncio
    async def test_dispatch_handles_missing_user_agent(
        self, middleware, mock_request, mock_response
    ):
        """Test dispatch handles missing user-agent header."""
        # Setup request without user-agent
        mock_request.headers = Headers({})
        call_next = AsyncMock(return_value=mock_response)

        with patch("middleware.logging.logger") as mock_logger:
            with patch("middleware.logging.time.time", side_effect=[1000.0, 1001.0]):
                await middleware.dispatch(mock_request, call_next)

                # Verify user_agent defaults to 'unknown'
                bind_call = mock_logger.bind.call_args[1]
                assert bind_call["user_agent"] == "unknown"

    @pytest.mark.asyncio
    async def test_dispatch_handles_exception(self, middleware, mock_request):
        """Test dispatch handles and logs exceptions."""
        # Setup call_next to raise exception
        test_exception = ValueError("Test error")
        call_next = AsyncMock(side_effect=test_exception)

        with patch("middleware.logging.logger") as mock_logger:
            mock_logger_with_context = MagicMock()
            mock_logger.bind.return_value = mock_logger_with_context

            with patch("middleware.logging.time.time", side_effect=[1000.0, 1002.0]):
                # Verify exception is re-raised
                with pytest.raises(ValueError, match="Test error"):
                    await middleware.dispatch(mock_request, call_next)

                # Verify error logging
                error_call = mock_logger_with_context.error.call_args
                assert error_call[0][0] == "Request failed"
                assert error_call[1]["request_error"] is True
                assert error_call[1]["error_type"] == "ValueError"
                assert error_call[1]["duration_ms"] == 2000.0

    @pytest.mark.asyncio
    async def test_dispatch_calculates_duration_correctly(
        self, middleware, mock_request, mock_response
    ):
        """Test that request duration is calculated correctly."""
        call_next = AsyncMock(return_value=mock_response)

        with patch("middleware.logging.logger") as mock_logger:
            mock_logger_with_context = MagicMock()
            mock_logger.bind.return_value = mock_logger_with_context

            # Mock time to simulate 250ms request
            with patch(
                "middleware.logging.time.time",
                side_effect=[1000.0, 1000.25],
            ):
                await middleware.dispatch(mock_request, call_next)

                # Verify duration calculation
                complete_call = mock_logger_with_context.info.call_args_list[1]
                assert complete_call[1]["duration_ms"] == 250.0

    @pytest.mark.asyncio
    async def test_dispatch_adds_correlation_id_to_response(
        self, middleware, mock_request, mock_response
    ):
        """Test that correlation ID is added to response headers."""
        call_next = AsyncMock(return_value=mock_response)

        with patch(
            "middleware.logging.uuid.uuid4",
            return_value=uuid.UUID("12345678-1234-5678-9012-123456789012"),
        ):
            with patch("middleware.logging.logger"):
                with patch(
                    "middleware.logging.time.time",
                    side_effect=[1000.0, 1001.0],
                ):
                    result = await middleware.dispatch(mock_request, call_next)

                    # Verify correlation ID in response headers
                    expected_id = "12345678-1234-5678-9012-123456789012"
                    assert result.headers["X-Correlation-ID"] == expected_id


class TestGetCorrelationId:
    """Test cases for get_correlation_id function."""

    def test_get_correlation_id_with_existing_id(self):
        """Test getting correlation ID when it exists in request state."""
        mock_request = MagicMock(spec=Request)
        mock_request.state.correlation_id = "test-correlation-id"

        result = get_correlation_id(mock_request)

        assert result == "test-correlation-id"

    def test_get_correlation_id_without_id(self):
        """Test getting correlation ID when it doesn't exist."""
        mock_request = MagicMock(spec=Request)
        # Simulate missing correlation_id attribute
        del mock_request.state.correlation_id

        result = get_correlation_id(mock_request)

        assert result == "unknown"

    def test_get_correlation_id_with_none_state(self):
        """Test getting correlation ID when request state is None."""
        mock_request = MagicMock(spec=Request)
        mock_request.state = None

        result = get_correlation_id(mock_request)

        assert result == "unknown"

"""Tests for error handling utilities."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from utils.error_handlers import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
    ErrorResponse,
    NotFoundError,
    ValidationError,
    api_error_handler,
    general_exception_handler,
    handle_database_error,
    log_and_raise_error,
)


class TestErrorResponse:
    """Test cases for ErrorResponse model."""

    def test_error_response_creation(self):
        """Test ErrorResponse model creation."""
        response = ErrorResponse(
            error="TEST_ERROR",
            message="Test message",
            correlation_id="test-123",
            details={"key": "value"},
        )

        assert response.error == "TEST_ERROR"
        assert response.message == "Test message"
        assert response.correlation_id == "test-123"
        assert response.details == {"key": "value"}

    def test_error_response_without_details(self):
        """Test ErrorResponse model without details."""
        response = ErrorResponse(
            error="TEST_ERROR", message="Test message", correlation_id="test-123"
        )

        assert response.details is None


class TestAPIError:
    """Test cases for APIError class."""

    def test_api_error_default_values(self):
        """Test APIError with default values."""
        error = APIError("Test message")

        assert error.message == "Test message"
        assert error.error_type == "API_ERROR"
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error.details == {}
        assert error.correlation_id is not None

    def test_api_error_custom_values(self):
        """Test APIError with custom values."""
        error = APIError(
            message="Custom message",
            error_type="CUSTOM_ERROR",
            status_code=400,
            details={"field": "error"},
            correlation_id="custom-123",
        )

        assert error.message == "Custom message"
        assert error.error_type == "CUSTOM_ERROR"
        assert error.status_code == 400
        assert error.details == {"field": "error"}
        assert error.correlation_id == "custom-123"


class TestValidationError:
    """Test cases for ValidationError class."""

    def test_validation_error_default(self):
        """Test ValidationError with default values."""
        error = ValidationError("Validation failed")

        assert error.message == "Validation failed"
        assert error.error_type == "VALIDATION_ERROR"
        assert error.status_code == status.HTTP_400_BAD_REQUEST

    def test_validation_error_with_details(self):
        """Test ValidationError with details."""
        error = ValidationError(
            "Field error", details={"field": "required"}, correlation_id="val-123"
        )

        assert error.details == {"field": "required"}
        assert error.correlation_id == "val-123"


class TestAuthenticationError:
    """Test cases for AuthenticationError class."""

    def test_authentication_error_default(self):
        """Test AuthenticationError with default message."""
        error = AuthenticationError()

        assert error.message == "Authentication failed"
        assert error.error_type == "AUTHENTICATION_ERROR"
        assert error.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authentication_error_custom(self):
        """Test AuthenticationError with custom message."""
        error = AuthenticationError("Invalid token")

        assert error.message == "Invalid token"


class TestAuthorizationError:
    """Test cases for AuthorizationError class."""

    def test_authorization_error_default(self):
        """Test AuthorizationError with default message."""
        error = AuthorizationError()

        assert error.message == "Access denied"
        assert error.error_type == "AUTHORIZATION_ERROR"
        assert error.status_code == status.HTTP_403_FORBIDDEN

    def test_authorization_error_custom(self):
        """Test AuthorizationError with custom message."""
        error = AuthorizationError("Insufficient permissions")

        assert error.message == "Insufficient permissions"


class TestNotFoundError:
    """Test cases for NotFoundError class."""

    def test_not_found_error_default(self):
        """Test NotFoundError with default message."""
        error = NotFoundError()

        assert error.message == "Resource not found"
        assert error.error_type == "NOT_FOUND_ERROR"
        assert error.status_code == status.HTTP_404_NOT_FOUND

    def test_not_found_error_custom(self):
        """Test NotFoundError with custom message."""
        error = NotFoundError("User not found")

        assert error.message == "User not found"


class TestDatabaseError:
    """Test cases for DatabaseError class."""

    def test_database_error_default(self):
        """Test DatabaseError with default message."""
        error = DatabaseError()

        assert error.message == "Database operation failed"
        assert error.error_type == "DATABASE_ERROR"
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_database_error_custom(self):
        """Test DatabaseError with custom message."""
        error = DatabaseError("Connection failed")

        assert error.message == "Connection failed"


class TestHandleDatabaseError:
    """Test cases for handle_database_error function."""

    def test_handle_integrity_error(self):
        """Test handling IntegrityError."""
        orig_error = Exception("UNIQUE constraint failed")
        integrity_error = IntegrityError(
            "statement", "params", orig_error, "connection_invalidated"
        )

        result = handle_database_error(integrity_error, "test-123", "insert operation")

        assert isinstance(result, ValidationError)
        assert result.message == "Data integrity constraint violation"
        assert result.correlation_id == "test-123"
        assert "operation" in result.details
        assert "constraint_error" in result.details

    def test_handle_sqlalchemy_error(self):
        """Test handling general SQLAlchemyError."""
        sql_error = SQLAlchemyError("Database connection lost")

        result = handle_database_error(sql_error, "test-456", "select operation")

        assert isinstance(result, DatabaseError)
        assert result.message == "Database select operation failed"
        assert result.correlation_id == "test-456"
        assert result.details["operation"] == "select operation"

    def test_handle_generic_error(self):
        """Test handling generic exception."""
        generic_error = ValueError("Invalid value")

        result = handle_database_error(generic_error, "test-789", "update operation")

        assert isinstance(result, APIError)
        assert "Unexpected error during update operation" in result.message
        assert result.correlation_id == "test-789"


class TestLogAndRaiseError:
    """Test cases for log_and_raise_error function."""

    @patch("utils.error_handlers.logger")
    def test_log_and_raise_basic_error(self, mock_logger):
        """Test logging and raising basic APIError."""
        error = APIError("Test error", correlation_id="test-123")

        with pytest.raises(Exception):
            log_and_raise_error(error)

        mock_logger.error.assert_called_once()

    @patch("utils.error_handlers.logger")
    def test_log_and_raise_with_db_session(self, mock_logger):
        """Test logging with database session rollback."""
        mock_session = MagicMock()
        error = APIError("Test error")

        with pytest.raises(Exception):
            log_and_raise_error(error, db_session=mock_session)

        mock_session.rollback.assert_called_once()

    @patch("utils.error_handlers.log_authentication_event")
    @patch("utils.error_handlers.logger")
    def test_log_authentication_error(self, mock_logger, mock_audit_log):
        """Test logging authentication error with audit."""
        error = AuthenticationError("Invalid credentials")

        with pytest.raises(Exception):
            log_and_raise_error(error, user_id="user123", operation="login")

        mock_audit_log.assert_called_once()
        call_args = mock_audit_log.call_args[1]
        assert call_args["event_type"] == "AUTHENTICATION_FAILED"
        assert call_args["user_id"] == "user123"
        assert call_args["success"] is False


class TestAPIErrorHandler:
    """Test cases for api_error_handler function."""

    @pytest.mark.asyncio
    async def test_api_error_handler(self):
        """Test API error handler returns proper JSONResponse."""
        request = MagicMock(spec=Request)
        error = APIError(
            "Test error",
            error_type="TEST_ERROR",
            status_code=400,
            correlation_id="test-123",
            details={"field": "error"},
        )

        response = await api_error_handler(request, error)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 400


class TestGeneralExceptionHandler:
    """Test cases for general_exception_handler function."""

    @pytest.mark.asyncio
    @patch("utils.error_handlers.get_correlation_id")
    @patch("utils.error_handlers.logger")
    async def test_general_exception_handler(self, mock_logger, mock_get_corr):
        """Test general exception handler."""
        mock_get_corr.return_value = "test-correlation-123"
        request = MagicMock(spec=Request)
        request.url.path = "/test/path"
        request.method = "GET"

        exception = ValueError("Test exception")

        response = await general_exception_handler(request, exception)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch("utils.error_handlers.get_correlation_id")
    @patch("utils.error_handlers.logger")
    async def test_general_exception_handler_correlation_error(
        self, mock_logger, mock_get_corr
    ):
        """Test general exception handler when correlation ID fails."""
        mock_get_corr.side_effect = Exception("Correlation error")
        request = MagicMock(spec=Request)
        request.url.path = "/test/path"
        request.method = "POST"

        exception = RuntimeError("Test runtime error")

        response = await general_exception_handler(request, exception)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        mock_logger.error.assert_called_once()

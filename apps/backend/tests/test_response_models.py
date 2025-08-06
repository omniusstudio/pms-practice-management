"""Tests for response models utilities."""

from datetime import datetime
from uuid import uuid4

from utils.response_models import (
    APIResponse,
    ErrorResponse,
    HealthCheckResponse,
    ListResponse,
    PaginationMeta,
    create_error_response,
    create_list_response,
    create_success_response,
)


class TestPaginationMeta:
    """Test cases for PaginationMeta model."""

    def test_pagination_meta_creation(self):
        """Test PaginationMeta model creation."""
        pagination = PaginationMeta(
            page=2,
            per_page=10,
            total_items=25,
            total_pages=3,
            has_next=True,
            has_prev=True,
        )

        assert pagination.page == 2
        assert pagination.per_page == 10
        assert pagination.total_items == 25
        assert pagination.total_pages == 3
        assert pagination.has_next is True
        assert pagination.has_prev is True

    def test_pagination_meta_first_page(self):
        """Test PaginationMeta for first page."""
        pagination = PaginationMeta(
            page=1,
            per_page=5,
            total_items=20,
            total_pages=4,
            has_next=True,
            has_prev=False,
        )

        assert pagination.page == 1
        assert pagination.has_next is True
        assert pagination.has_prev is False

    def test_pagination_meta_last_page(self):
        """Test PaginationMeta for last page."""
        pagination = PaginationMeta(
            page=4,
            per_page=5,
            total_items=20,
            total_pages=4,
            has_next=False,
            has_prev=True,
        )

        assert pagination.page == 4
        assert pagination.has_next is False
        assert pagination.has_prev is True


class TestAPIResponse:
    """Test cases for APIResponse model."""

    def test_api_response_with_data(self):
        """Test APIResponse with data."""
        test_data = {"id": 1, "name": "Test"}
        response = APIResponse(
            success=True, data=test_data, message="Success", correlation_id="test-123"
        )

        assert response.success is True
        assert response.data == test_data
        assert response.message == "Success"
        assert response.correlation_id == "test-123"
        assert isinstance(response.timestamp, datetime)

    def test_api_response_without_data(self):
        """Test APIResponse without data."""
        response = APIResponse(success=True, correlation_id="test-456")

        assert response.success is True
        assert response.data is None
        assert response.message is None
        assert response.correlation_id == "test-456"

    def test_api_response_json_encoders(self):
        """Test APIResponse JSON encoders."""
        test_uuid = uuid4()
        test_datetime = datetime.utcnow()

        response = APIResponse(
            success=True,
            data={"uuid": test_uuid, "created_at": test_datetime},
            correlation_id="test-789",
        )

        # Test that the model can be created with UUID and datetime
        assert response.data["uuid"] == test_uuid
        assert response.data["created_at"] == test_datetime


class TestListResponse:
    """Test cases for ListResponse model."""

    def test_list_response_creation(self):
        """Test ListResponse creation."""
        test_data = [{"id": 1}, {"id": 2}]
        pagination = PaginationMeta(
            page=1,
            per_page=10,
            total_items=2,
            total_pages=1,
            has_next=False,
            has_prev=False,
        )

        response = ListResponse(
            success=True,
            data=test_data,
            pagination=pagination,
            message="List retrieved",
            correlation_id="list-123",
        )

        assert response.success is True
        assert response.data == test_data
        assert response.pagination == pagination
        assert response.message == "List retrieved"
        assert response.correlation_id == "list-123"
        assert isinstance(response.timestamp, datetime)

    def test_list_response_empty_data(self):
        """Test ListResponse with empty data."""
        pagination = PaginationMeta(
            page=1,
            per_page=10,
            total_items=0,
            total_pages=0,
            has_next=False,
            has_prev=False,
        )

        response = ListResponse(
            success=True, data=[], pagination=pagination, correlation_id="empty-123"
        )

        assert response.data == []
        assert response.pagination.total_items == 0


class TestErrorResponse:
    """Test cases for ErrorResponse model."""

    def test_error_response_creation(self):
        """Test ErrorResponse creation."""
        details = {"field": "required", "code": "VALIDATION_ERROR"}
        response = ErrorResponse(
            success=False,
            error="VALIDATION_ERROR",
            message="Validation failed",
            details=details,
            correlation_id="error-123",
        )

        assert response.success is False
        assert response.error == "VALIDATION_ERROR"
        assert response.message == "Validation failed"
        assert response.details == details
        assert response.correlation_id == "error-123"
        assert isinstance(response.timestamp, datetime)

    def test_error_response_without_details(self):
        """Test ErrorResponse without details."""
        response = ErrorResponse(
            success=False,
            error="NOT_FOUND",
            message="Resource not found",
            correlation_id="error-456",
        )

        assert response.details is None

    def test_error_response_default_success_false(self):
        """Test ErrorResponse has success=False by default."""
        response = ErrorResponse(
            error="TEST_ERROR", message="Test error", correlation_id="test-789"
        )

        assert response.success is False


class TestHealthCheckResponse:
    """Test cases for HealthCheckResponse model."""

    def test_health_check_response_full(self):
        """Test HealthCheckResponse with all fields."""
        services = {"database": "healthy", "redis": "healthy"}
        response = HealthCheckResponse(
            status="healthy",
            version="1.0.0",
            environment="production",
            services=services,
        )

        assert response.status == "healthy"
        assert response.version == "1.0.0"
        assert response.environment == "production"
        assert response.services == services
        assert isinstance(response.timestamp, datetime)

    def test_health_check_response_minimal(self):
        """Test HealthCheckResponse with minimal fields."""
        response = HealthCheckResponse(status="unhealthy")

        assert response.status == "unhealthy"
        assert response.version is None
        assert response.environment is None
        assert response.services is None


class TestCreateSuccessResponse:
    """Test cases for create_success_response function."""

    def test_create_success_response_with_all_params(self):
        """Test create_success_response with all parameters."""
        test_data = {"id": 1, "name": "Test"}
        response = create_success_response(
            data=test_data, message="Operation successful", correlation_id="success-123"
        )

        assert isinstance(response, APIResponse)
        assert response.success is True
        assert response.data == test_data
        assert response.message == "Operation successful"
        assert response.correlation_id == "success-123"

    def test_create_success_response_minimal(self):
        """Test create_success_response with minimal parameters."""
        test_data = "simple string data"
        response = create_success_response(data=test_data)

        assert response.success is True
        assert response.data == test_data
        assert response.message is None
        assert response.correlation_id == "unknown"

    def test_create_success_response_none_data(self):
        """Test create_success_response with None data."""
        response = create_success_response(data=None)

        assert response.success is True
        assert response.data is None


class TestCreateListResponse:
    """Test cases for create_list_response function."""

    def test_create_list_response_full(self):
        """Test create_list_response with all parameters."""
        test_data = [{"id": 1}, {"id": 2}, {"id": 3}]
        response = create_list_response(
            data=test_data,
            page=2,
            per_page=10,
            total_items=25,
            message="List retrieved",
            correlation_id="list-123",
        )

        assert isinstance(response, ListResponse)
        assert response.success is True
        assert response.data == test_data
        assert response.message == "List retrieved"
        assert response.correlation_id == "list-123"

        # Check pagination calculation
        assert response.pagination.page == 2
        assert response.pagination.per_page == 10
        assert response.pagination.total_items == 25
        assert response.pagination.total_pages == 3
        assert response.pagination.has_next is True
        assert response.pagination.has_prev is True

    def test_create_list_response_first_page(self):
        """Test create_list_response for first page."""
        response = create_list_response(
            data=[{"id": 1}], page=1, per_page=5, total_items=10
        )

        assert response.pagination.page == 1
        assert response.pagination.total_pages == 2
        assert response.pagination.has_next is True
        assert response.pagination.has_prev is False
        assert response.correlation_id == "unknown"

    def test_create_list_response_last_page(self):
        """Test create_list_response for last page."""
        response = create_list_response(
            data=[{"id": 10}], page=2, per_page=5, total_items=10
        )

        assert response.pagination.page == 2
        assert response.pagination.total_pages == 2
        assert response.pagination.has_next is False
        assert response.pagination.has_prev is True

    def test_create_list_response_single_page(self):
        """Test create_list_response for single page."""
        response = create_list_response(
            data=[{"id": 1}, {"id": 2}], page=1, per_page=10, total_items=2
        )

        assert response.pagination.total_pages == 1
        assert response.pagination.has_next is False
        assert response.pagination.has_prev is False

    def test_create_list_response_empty(self):
        """Test create_list_response with empty data."""
        response = create_list_response(data=[], page=1, per_page=10, total_items=0)

        assert response.data == []
        assert response.pagination.total_items == 0
        assert response.pagination.total_pages == 0
        assert response.pagination.has_next is False
        assert response.pagination.has_prev is False


class TestCreateErrorResponse:
    """Test cases for create_error_response function."""

    def test_create_error_response_full(self):
        """Test create_error_response with all parameters."""
        details = {"field": "email", "code": "INVALID_FORMAT"}
        response = create_error_response(
            error="VALIDATION_ERROR",
            message="Invalid email format",
            details=details,
            correlation_id="error-123",
        )

        assert isinstance(response, ErrorResponse)
        assert response.success is False
        assert response.error == "VALIDATION_ERROR"
        assert response.message == "Invalid email format"
        assert response.details == details
        assert response.correlation_id == "error-123"

    def test_create_error_response_minimal(self):
        """Test create_error_response with minimal parameters."""
        response = create_error_response(
            error="NOT_FOUND", message="Resource not found"
        )

        assert response.success is False
        assert response.error == "NOT_FOUND"
        assert response.message == "Resource not found"
        assert response.details is None
        assert response.correlation_id == "unknown"

    def test_create_error_response_with_details_none(self):
        """Test create_error_response with explicit None details."""
        response = create_error_response(
            error="SERVER_ERROR",
            message="Internal server error",
            details=None,
            correlation_id="server-error-456",
        )

        assert response.details is None
        assert response.correlation_id == "server-error-456"

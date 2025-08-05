"""Standardized response models for API endpoints."""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

# Generic type for response data
T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""

    page: int = Field(..., description="Current page number (1-based)")
    per_page: int = Field(..., description="Items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class APIResponse(BaseModel, Generic[T]):
    """Standardized API response format."""

    success: bool = Field(True, description="Whether the request was successful")
    data: Optional[T] = Field(None, description="Response data")
    message: Optional[str] = Field(None, description="Human-readable message")
    correlation_id: str = Field(..., description="Request correlation ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class ListResponse(BaseModel, Generic[T]):
    """Standardized list response with pagination."""

    success: bool = Field(True, description="Whether the request was successful")
    data: List[T] = Field(..., description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    message: Optional[str] = Field(None, description="Human-readable message")
    correlation_id: str = Field(..., description="Request correlation ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class ErrorResponse(BaseModel):
    """Standardized error response format."""

    success: bool = Field(False, description="Always false for error responses")
    error: str = Field(..., description="Error type/code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    correlation_id: str = Field(..., description="Request correlation ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class HealthCheckResponse(BaseModel):
    """Health check response format."""

    status: str = Field(..., description="Health status (healthy/unhealthy)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Check timestamp"
    )
    version: Optional[str] = Field(None, description="Application version")
    environment: Optional[str] = Field(None, description="Environment name")
    services: Optional[Dict[str, str]] = Field(
        None, description="Service health status"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


def create_success_response(
    data: T, message: Optional[str] = None, correlation_id: Optional[str] = None
) -> APIResponse[T]:
    """Create a standardized success response."""
    return APIResponse(
        success=True,
        data=data,
        message=message,
        correlation_id=correlation_id or "unknown",
    )


def create_list_response(
    data: List[T],
    page: int,
    per_page: int,
    total_items: int,
    message: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> ListResponse[T]:
    """Create a standardized list response with pagination."""
    total_pages = (total_items + per_page - 1) // per_page

    pagination = PaginationMeta(
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )

    return ListResponse(
        success=True,
        data=data,
        pagination=pagination,
        message=message,
        correlation_id=correlation_id or "unknown",
    )


def create_error_response(
    error: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> ErrorResponse:
    """Create a standardized error response."""
    return ErrorResponse(
        success=False,
        error=error,
        message=message,
        details=details,
        correlation_id=correlation_id or "unknown",
    )

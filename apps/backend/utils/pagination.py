"""Pagination utilities for standardized API responses.

This module provides utilities for consistent pagination across all API
endpoints, ensuring HIPAA compliance and proper error handling.
"""

import math
from typing import Any, Dict, List, Optional, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Query as SQLQuery

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Standard pagination parameters for API endpoints."""

    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    per_page: int = Field(
        default=20, ge=1, le=100, description="Items per page (max 100)"
    )


class PaginationMeta(BaseModel):
    """Pagination metadata for API responses."""

    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class PaginatedResult(BaseModel):
    """Generic paginated result container."""

    items: List[Any] = Field(..., description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
) -> PaginationParams:
    """FastAPI dependency for pagination parameters.

    Args:
        page: Page number (1-based)
        per_page: Items per page (max 100)

    Returns:
        PaginationParams: Validated pagination parameters
    """
    return PaginationParams(page=page, per_page=per_page)


def paginate_query(
    query: SQLQuery, page: int, per_page: int, count_query: Optional[SQLQuery] = None
) -> PaginatedResult:
    """Paginate a SQLAlchemy query.

    Args:
        query: SQLAlchemy query to paginate
        page: Page number (1-based)
        per_page: Items per page
        count_query: Optional separate count query for performance

    Returns:
        PaginatedResult: Paginated results with metadata
    """
    # Calculate offset
    offset = (page - 1) * per_page

    # Get total count
    if count_query is not None:
        total_items = count_query.scalar()
    else:
        total_items = query.count()

    # Calculate pagination metadata
    total_pages = math.ceil(total_items / per_page) if total_items > 0 else 0
    has_next = page < total_pages
    has_prev = page > 1

    # Get paginated items
    items = query.offset(offset).limit(per_page).all()

    # Create pagination metadata
    pagination = PaginationMeta(
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
    )

    return PaginatedResult(items=items, pagination=pagination)


def paginate_list(items: List[T], page: int, per_page: int) -> PaginatedResult:
    """Paginate a list of items.

    Args:
        items: List of items to paginate
        page: Page number (1-based)
        per_page: Items per page

    Returns:
        PaginatedResult: Paginated results with metadata
    """
    total_items = len(items)
    total_pages = math.ceil(total_items / per_page) if total_items > 0 else 0

    # Calculate offset
    offset = (page - 1) * per_page

    # Get paginated items
    paginated_items = items[offset : offset + per_page]

    # Calculate pagination metadata
    has_next = page < total_pages
    has_prev = page > 1

    # Create pagination metadata
    pagination = PaginationMeta(
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
    )

    return PaginatedResult(items=paginated_items, pagination=pagination)


def create_pagination_response(
    items: List[Any], pagination: PaginationMeta, message: Optional[str] = None
) -> Dict[str, Any]:
    """Create a standardized pagination response.

    Args:
        items: List of items
        pagination: Pagination metadata
        message: Optional success message

    Returns:
        Dict: Standardized API response with pagination
    """
    return {
        "success": True,
        "data": items,
        "pagination": pagination.dict(),
        "message": message or f"Retrieved {len(items)} items",
    }

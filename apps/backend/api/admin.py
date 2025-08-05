"""Admin API endpoints for role and user management.

This module provides RBAC administration endpoints that allow
administrators to manage user roles and permissions.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth_middleware import AuthenticatedUser, require_admin_role
from models.user import User
from utils.response_models import APIResponse

router = APIRouter(prefix="/admin", tags=["admin"])


class UserRoleUpdate(BaseModel):
    """Request model for updating user roles."""

    user_id: UUID
    roles: List[str]

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "roles": ["clinician"],
            }
        }


class UserResponse(BaseModel):
    """Response model for user information."""

    id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    display_name: Optional[str]
    roles: List[str]
    permissions: List[str]
    is_active: bool
    is_admin: bool

    class Config:
        from_attributes = True


@router.get(
    "/users", response_model=APIResponse[List[UserResponse]], summary="List all users"
)
async def list_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of users to return"),
    role_filter: Optional[str] = Query(None, description="Filter users by role"),
    current_user: AuthenticatedUser = Depends(require_admin_role),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[List[UserResponse]]:
    """List all users with optional role filtering.

    Only administrators can access this endpoint.
    """
    try:
        # Build query conditions
        conditions = {}
        if role_filter:
            # Note: This is a simplified filter - in production you might
            # want more sophisticated role filtering
            conditions["roles"] = role_filter

        query = select(User)
        if role_filter:
            query = query.where(User.roles.contains([role_filter]))
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        users = result.scalars().all()

        user_responses = [UserResponse.model_validate(user) for user in users]

        return APIResponse(
            success=True,
            data=user_responses,
            message=f"Retrieved {len(user_responses)} users",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve users: {str(e)}"
        )


@router.get(
    "/users/{user_id}",
    response_model=APIResponse[UserResponse],
    summary="Get user by ID",
)
async def get_user(
    user_id: UUID,
    current_user: AuthenticatedUser = Depends(require_admin_role),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[UserResponse]:
    """Get a specific user by ID.

    Only administrators can access this endpoint.
    """
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_response = UserResponse.model_validate(user)

        return APIResponse(
            success=True, data=user_response, message="User retrieved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve user: {str(e)}"
        )


@router.put(
    "/users/{user_id}/roles",
    response_model=APIResponse[UserResponse],
    summary="Update user roles",
)
async def update_user_roles(
    user_id: UUID,
    role_update: UserRoleUpdate,
    current_user: AuthenticatedUser = Depends(require_admin_role),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[UserResponse]:
    """Update a user's roles.

    Only administrators can access this endpoint.
    Validates that the provided roles are valid RBAC roles.
    """
    try:
        # Validate roles
        valid_roles = {"admin", "clinician", "biller", "front_desk"}
        invalid_roles = set(role_update.roles) - valid_roles
        if invalid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid roles: {', '.join(invalid_roles)}. "
                f"Valid roles are: {', '.join(valid_roles)}",
            )

        # Get the user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Prevent removing admin role from the last admin
        if "admin" in user.roles and "admin" not in role_update.roles:
            admin_count_result = await db.execute(
                select(func.count(User.id)).where(User.roles.contains(["admin"]))
            )
            admin_count = admin_count_result.scalar()
            if admin_count <= 1:
                raise HTTPException(
                    status_code=400,
                    detail=("Cannot remove admin role from the last administrator"),
                )

        # Update roles
        user.roles = role_update.roles
        user.is_admin = "admin" in role_update.roles

        await db.commit()
        await db.refresh(user)
        updated_user = user
        user_response = UserResponse.model_validate(updated_user)

        return APIResponse(
            success=True,
            data=user_response,
            message=f"User roles updated to: {', '.join(role_update.roles)}",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update user roles: {str(e)}"
        )


@router.get(
    "/roles",
    response_model=APIResponse[dict],
    summary="Get available roles and their permissions",
)
async def get_roles_info(
    current_user: AuthenticatedUser = Depends(require_admin_role),
) -> APIResponse[dict]:
    """Get information about available RBAC roles and their permissions.

    Only administrators can access this endpoint.
    """
    roles_info = {
        "admin": {
            "name": "Administrator",
            "description": "Full system access including user management",
            "permissions": [
                "read",
                "write",
                "delete",
                "manage",
                "read_ledger",
                "read_financial_reports",
            ],
        },
        "clinician": {
            "name": "Clinician",
            "description": "Patient care and clinical documentation",
            "permissions": ["read", "write"],
        },
        "biller": {
            "name": "Biller",
            "description": "Billing and financial management",
            "permissions": ["read", "read_ledger", "read_financial_reports"],
        },
        "front_desk": {
            "name": "Front Desk",
            "description": "Appointments and patient registration",
            "permissions": ["read"],
        },
    }

    return APIResponse(
        success=True,
        data=roles_info,
        message="RBAC roles information retrieved successfully",
    )

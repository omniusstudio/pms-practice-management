"""Access Review API endpoints for Phase 2 RBAC Implementation.

This module provides quarterly access review functionality including:
- Access review report generation
- User access audit endpoints
- Access review checklist automation
- HIPAA compliance reporting
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth_middleware import AuthenticatedUser, require_admin_role
from middleware.rbac_enhanced import enhanced_rbac
from models.user import User
from utils.response_models import APIResponse

router = APIRouter(prefix="/access-review", tags=["access-review"])


class AccessReviewReport(BaseModel):
    """Model for access review report."""

    report_id: str
    generated_at: datetime
    review_period_start: datetime
    review_period_end: datetime
    total_users: int
    active_users: int
    inactive_users: int
    users_by_role: Dict[str, int]
    excessive_permissions: List[Dict[str, Any]]
    unused_permissions: List[Dict[str, Any]]
    overdue_reviews: List[Dict[str, Any]]
    compliance_score: float
    recommendations: List[str]

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class UserAccessSummary(BaseModel):
    """Model for individual user access summary."""

    user_id: UUID
    email: str
    display_name: Optional[str]
    roles: List[str]
    permissions: List[str]
    last_login: Optional[datetime]
    last_access: Optional[datetime]
    access_frequency: int
    excessive_permissions: List[str]
    unused_permissions: List[str]
    risk_score: float
    recommendations: List[str]

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class AccessReviewChecklist(BaseModel):
    """Model for access review checklist."""

    checklist_id: str
    created_at: datetime
    review_period: str
    items: List[Dict[str, Any]]
    completed_items: int
    total_items: int
    completion_percentage: float
    overdue_items: List[Dict[str, Any]]

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


@router.get(
    "/report",
    response_model=APIResponse[AccessReviewReport],
    summary="Generate quarterly access review report",
)
async def generate_access_review_report(
    quarter: Optional[int] = Query(
        None, ge=1, le=4, description="Quarter (1-4) for the report"
    ),
    year: Optional[int] = Query(None, ge=2020, description="Year for the report"),
    current_user: AuthenticatedUser = Depends(require_admin_role),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[AccessReviewReport]:
    """Generate comprehensive access review report.

    Only administrators can access this endpoint.
    """
    try:
        # Determine review period
        if not quarter or not year:
            now = datetime.now(timezone.utc)
            current_quarter = (now.month - 1) // 3 + 1
            quarter = quarter or current_quarter
            year = year or now.year

        # Calculate period dates
        period_start = datetime(year, (quarter - 1) * 3 + 1, 1, tzinfo=timezone.utc)
        if quarter == 4:
            period_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            period_end = datetime(year, quarter * 3 + 1, 1, tzinfo=timezone.utc)

        # Get all users
        users_result = await db.execute(select(User))
        users = users_result.scalars().all()

        # Calculate statistics
        total_users = len(users)
        active_users = len([u for u in users if u.is_active])
        inactive_users = total_users - active_users

        # Users by role
        users_by_role = {}
        for user in users:
            for role in user.roles or []:
                users_by_role[role] = users_by_role.get(role, 0) + 1

        # Analyze excessive permissions
        excessive_permissions = []
        unused_permissions = []
        overdue_reviews = []

        for user in users:
            # Check role validation
            validation_result = enhanced_rbac.validate_role_hierarchy(user.roles or [])

            if not validation_result.valid:
                excessive_permissions.append(
                    {
                        "user_id": str(user.id),
                        "email": user.email,
                        "excessive_roles": validation_result.excessive_permissions,
                        "recommendations": validation_result.recommendations,
                    }
                )

            # Check for unused permissions (simplified)
            user_logs = enhanced_rbac.get_access_logs(
                user_id=user.id, start_date=period_start, end_date=period_end
            )

            if not user_logs and user.is_active:
                unused_permissions.append(
                    {
                        "user_id": str(user.id),
                        "email": user.email,
                        "roles": user.roles,
                        "last_login": (
                            user.last_login_at.isoformat()
                            if user.last_login_at
                            else None
                        ),
                    }
                )

            # Check for overdue reviews (users not reviewed in 90 days)
            if user.last_login_at:
                days_since_login = (
                    datetime.now(timezone.utc) - user.last_login_at
                ).days
                if days_since_login > 90:
                    overdue_reviews.append(
                        {
                            "user_id": str(user.id),
                            "email": user.email,
                            "days_since_login": days_since_login,
                            "roles": user.roles,
                        }
                    )

        # Calculate compliance score
        total_issues = (
            len(excessive_permissions) + len(unused_permissions) + len(overdue_reviews)
        )
        compliance_score = max(0, 100 - (total_issues * 10))

        # Generate recommendations
        recommendations = []
        if excessive_permissions:
            recommendations.append(
                f"Review and remove excessive permissions for "
                f"{len(excessive_permissions)} users"
            )
        if unused_permissions:
            recommendations.append(
                f"Review inactive accounts: {len(unused_permissions)} "
                f"users have not accessed the system recently"
            )
        if overdue_reviews:
            recommendations.append(
                f"Complete overdue access reviews for " f"{len(overdue_reviews)} users"
            )

        if compliance_score < 80:
            recommendations.append("Implement automated access review process")
            recommendations.append("Schedule monthly access review meetings")

        report = AccessReviewReport(
            report_id=f"AR-{year}Q{quarter}-{int(datetime.now().timestamp())}",
            generated_at=datetime.now(timezone.utc),
            review_period_start=period_start,
            review_period_end=period_end,
            total_users=total_users,
            active_users=active_users,
            inactive_users=inactive_users,
            users_by_role=users_by_role,
            excessive_permissions=excessive_permissions,
            unused_permissions=unused_permissions,
            overdue_reviews=overdue_reviews,
            compliance_score=compliance_score,
            recommendations=recommendations,
        )

        return APIResponse(
            success=True,
            data=report,
            message=f"Access review report generated for Q{quarter} {year}",
            correlation_id="access-review-report",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate access review report: {str(e)}"
        )


@router.get(
    "/users/{user_id}/summary",
    response_model=APIResponse[UserAccessSummary],
    summary="Get user access summary",
)
async def get_user_access_summary(
    user_id: UUID,
    days: int = Query(90, ge=1, le=365, description="Days to analyze"),
    current_user: AuthenticatedUser = Depends(require_admin_role),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[UserAccessSummary]:
    """Get detailed access summary for a specific user.

    Only administrators can access this endpoint.
    """
    try:
        # Get user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get access logs for the period
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        access_logs = enhanced_rbac.get_access_logs(
            user_id=user_id, start_date=start_date
        )

        # Calculate access frequency
        access_frequency = len(access_logs)

        # Get last access time
        last_access = None
        if access_logs:
            last_access = max(log.timestamp for log in access_logs)

        # Validate roles and permissions
        validation_result = enhanced_rbac.validate_role_hierarchy(user.roles or [])

        excessive_permissions = validation_result.excessive_permissions

        # Identify unused permissions (simplified)
        used_permissions = set()
        for log in access_logs:
            if log.permission_required.startswith("permissions:"):
                perms = log.permission_required.replace("permissions:", "").split(",")
                used_permissions.update(perms)

        all_permissions = set(user.permissions or [])
        unused_permissions = list(all_permissions - used_permissions)

        # Calculate risk score
        risk_score = 0.0
        if excessive_permissions:
            risk_score += len(excessive_permissions) * 10
        if unused_permissions:
            risk_score += len(unused_permissions) * 5
        if not access_logs:
            risk_score += 20  # No recent activity

        risk_score = min(100.0, risk_score)

        # Generate recommendations
        recommendations = []
        if excessive_permissions:
            recommendations.append(
                f"Remove excessive roles: " f"{', '.join(excessive_permissions)}"
            )
        if unused_permissions:
            recommendations.append("Review and remove unused permissions")
        if access_frequency == 0:
            recommendations.append("Consider deactivating account due to inactivity")
        elif access_frequency < 5:
            recommendations.append("Low activity - review if access is still needed")

        summary = UserAccessSummary(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            roles=user.roles or [],
            permissions=user.permissions or [],
            last_login=user.last_login_at,
            last_access=last_access,
            access_frequency=access_frequency,
            excessive_permissions=excessive_permissions,
            unused_permissions=unused_permissions,
            risk_score=risk_score,
            recommendations=recommendations,
        )

        return APIResponse(
            success=True,
            data=summary,
            message=f"Access summary generated for user {user.email}",
            correlation_id="user-access-summary",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate user access summary: {str(e)}"
        )


@router.get(
    "/checklist",
    response_model=APIResponse[AccessReviewChecklist],
    summary="Generate access review checklist",
)
async def generate_access_review_checklist(
    current_user: AuthenticatedUser = Depends(require_admin_role),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[AccessReviewChecklist]:
    """Generate automated access review checklist.

    Only administrators can access this endpoint.
    """
    try:
        now = datetime.now(timezone.utc)
        current_quarter = (now.month - 1) // 3 + 1

        # Define checklist items
        checklist_items = [
            {
                "id": "user_audit",
                "title": "Review all user accounts",
                "description": "Verify all users still require access",
                "priority": "high",
                "estimated_time": "2 hours",
                "completed": False,
                "due_date": (now + timedelta(days=7)).isoformat(),
            },
            {
                "id": "role_validation",
                "title": "Validate user roles",
                "description": "Ensure roles match job responsibilities",
                "priority": "high",
                "estimated_time": "1 hour",
                "completed": False,
                "due_date": (now + timedelta(days=7)).isoformat(),
            },
            {
                "id": "permission_cleanup",
                "title": "Remove excessive permissions",
                "description": "Clean up unnecessary role assignments",
                "priority": "medium",
                "estimated_time": "1 hour",
                "completed": False,
                "due_date": (now + timedelta(days=14)).isoformat(),
            },
            {
                "id": "inactive_accounts",
                "title": "Review inactive accounts",
                "description": "Disable or remove unused accounts",
                "priority": "medium",
                "estimated_time": "30 minutes",
                "completed": False,
                "due_date": (now + timedelta(days=14)).isoformat(),
            },
            {
                "id": "compliance_check",
                "title": "HIPAA compliance verification",
                "description": "Ensure minimum necessary access",
                "priority": "high",
                "estimated_time": "1 hour",
                "completed": False,
                "due_date": (now + timedelta(days=7)).isoformat(),
            },
            {
                "id": "documentation_update",
                "title": "Update access documentation",
                "description": "Document all access changes",
                "priority": "low",
                "estimated_time": "30 minutes",
                "completed": False,
                "due_date": (now + timedelta(days=21)).isoformat(),
            },
        ]

        # Check for overdue items
        overdue_items = []
        for item in checklist_items:
            due_date = datetime.fromisoformat(item["due_date"].replace("Z", "+00:00"))
            if due_date < now and not item["completed"]:
                overdue_items.append(item)

        completed_items = sum(1 for item in checklist_items if item["completed"])
        total_items = len(checklist_items)
        completion_percentage = (completed_items / total_items) * 100

        checklist = AccessReviewChecklist(
            checklist_id=f"CL-{now.year}Q{current_quarter}-{int(now.timestamp())}",
            created_at=now,
            review_period=f"Q{current_quarter} {now.year}",
            items=checklist_items,
            completed_items=completed_items,
            total_items=total_items,
            completion_percentage=completion_percentage,
            overdue_items=overdue_items,
        )

        return APIResponse(
            success=True,
            data=checklist,
            message="Access review checklist generated successfully",
            correlation_id="access-review-checklist",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate access review checklist: {str(e)}",
        )


@router.post(
    "/checklist/{checklist_id}/items/{item_id}/complete",
    response_model=APIResponse[dict],
    summary="Mark checklist item as complete",
)
async def complete_checklist_item(
    checklist_id: str,
    item_id: str,
    current_user: AuthenticatedUser = Depends(require_admin_role),
) -> APIResponse[dict]:
    """Mark a checklist item as completed.

    Only administrators can access this endpoint.
    """
    try:
        # In a real implementation, this would update a database record
        # For now, we'll just return a success response

        return APIResponse(
            success=True,
            data={
                "checklist_id": checklist_id,
                "item_id": item_id,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "completed_by": current_user.user_id,
            },
            message=f"Checklist item {item_id} marked as complete",
            correlation_id="complete-checklist-item",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to complete checklist item: {str(e)}"
        )


@router.get(
    "/logs", response_model=APIResponse[List[dict]], summary="Get access review logs"
)
async def get_access_review_logs(
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    resource: Optional[str] = Query(None, description="Filter by resource"),
    days: int = Query(30, ge=1, le=365, description="Days to retrieve"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum logs to return"),
    current_user: AuthenticatedUser = Depends(require_admin_role),
) -> APIResponse[List[dict]]:
    """Get access review logs for audit purposes.

    Only administrators can access this endpoint.
    """
    try:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        logs = enhanced_rbac.get_access_logs(
            user_id=user_id, resource=resource, start_date=start_date
        )

        # Limit results
        logs = logs[:limit]

        # Convert to dict for JSON serialization
        log_dicts = []
        for log in logs:
            log_dict = {
                "user_id": str(log.user_id),
                "resource": log.resource,
                "action": log.action,
                "permission_required": log.permission_required,
                "access_granted": log.access_granted,
                "timestamp": log.timestamp.isoformat(),
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "correlation_id": log.correlation_id,
            }
            log_dicts.append(log_dict)

        return APIResponse(
            success=True,
            data=log_dicts,
            message=f"Retrieved {len(log_dicts)} access logs",
            correlation_id="access-review-logs",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve access logs: {str(e)}"
        )

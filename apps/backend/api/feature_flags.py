"""Feature flags API endpoints."""

from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from middleware.correlation import get_correlation_id
from routers.auth_router import get_current_user
from services.feature_flags_service import (
    FeatureFlagsService,
    get_feature_flags_service,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])


class FlagEvaluationRequest(BaseModel):
    """Request model for flag evaluation."""

    flag_name: str = Field(..., description="Name of the feature flag")
    user_id: Optional[str] = Field(None, description="User ID for user-specific flags")
    default: bool = Field(False, description="Default value if flag is not found")
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context for evaluation"
    )


class FlagEvaluationResponse(BaseModel):
    """Response model for flag evaluation."""

    flag_name: str
    enabled: bool
    environment: str
    correlation_id: str


class AllFlagsResponse(BaseModel):
    """Response model for all flags."""

    flags: Dict[str, bool]
    environment: str
    user_id: Optional[str]
    correlation_id: str


class FlagInfoResponse(BaseModel):
    """Response model for flag information."""

    name: str
    default_value: Optional[bool]
    provider: str
    environment: str
    cached: bool
    correlation_id: str


@router.post(
    "/evaluate",
    response_model=FlagEvaluationResponse,
    summary="Evaluate a feature flag",
    description="Evaluate a specific feature flag for a user or context",
)
async def evaluate_flag(
    request: FlagEvaluationRequest,
    http_request: Request,
    current_user: dict = Depends(get_current_user),
    flags_service: FeatureFlagsService = Depends(get_feature_flags_service),
) -> FlagEvaluationResponse:
    """Evaluate a feature flag.

    This endpoint allows authorized users to evaluate feature flags.
    The evaluation considers user context and returns the current state
    of the flag.
    """
    correlation_id = get_correlation_id()

    try:
        # Use the authenticated user's ID if not provided in request
        user_id = request.user_id or current_user.get("sub")

        # Add request context
        context = request.context.copy()
        context.update(
            {
                "user_agent": http_request.headers.get("user-agent"),
                "ip_address": (
                    http_request.client.host if http_request.client else None
                ),
                "correlation_id": correlation_id,
            }
        )

        # Remove user_id from context to avoid conflicts
        context.pop("user_id", None)

        # Evaluate the flag
        enabled = flags_service.is_enabled(
            request.flag_name, user_id=user_id, default=request.default, **context
        )

        logger.info(
            "Feature flag evaluated via API",
            flag_name=request.flag_name,
            enabled=enabled,
            user_id_hash=(flags_service._hash_user_id(user_id) if user_id else None),
            correlation_id=correlation_id,
        )

        return FlagEvaluationResponse(
            flag_name=request.flag_name,
            enabled=enabled,
            environment=flags_service.config.environment,
            correlation_id=correlation_id,
        )

    except Exception as e:
        logger.error(
            "Error evaluating feature flag via API",
            flag_name=request.flag_name,
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=500, detail="Internal server error during flag evaluation"
        )


@router.get(
    "/all",
    response_model=AllFlagsResponse,
    summary="Get all feature flags",
    description="Get all feature flags for the current user",
)
async def get_all_flags(
    http_request: Request,
    user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    flags_service: FeatureFlagsService = Depends(get_feature_flags_service),
) -> AllFlagsResponse:
    """Get all feature flags for a user.

    This endpoint returns all available feature flags and their
    current state for the specified user or the authenticated user.
    """
    correlation_id = get_correlation_id()

    try:
        # Use the authenticated user's ID if not provided
        effective_user_id = user_id or current_user.get("sub")

        # Add request context
        context = {
            "user_agent": http_request.headers.get("user-agent"),
            "ip_address": (http_request.client.host if http_request.client else None),
            "correlation_id": correlation_id,
        }

        # Get all flags
        flags = flags_service.get_all_flags(effective_user_id, **context)

        logger.info(
            "All feature flags retrieved via API",
            flags_count=len(flags),
            user_id_hash=flags_service._hash_user_id(effective_user_id)
            if effective_user_id
            else None,
            correlation_id=correlation_id,
        )

        return AllFlagsResponse(
            flags=flags,
            environment=flags_service.config.environment,
            user_id=effective_user_id,
            correlation_id=correlation_id,
        )

    except Exception as e:
        logger.error(
            "Error retrieving all feature flags via API",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=500, detail="Internal server error during flags retrieval"
        )


@router.get(
    "/{flag_name}/info",
    response_model=FlagInfoResponse,
    summary="Get feature flag information",
    description="Get detailed information about a specific feature flag",
)
async def get_flag_info(
    flag_name: str,
    current_user: dict = Depends(get_current_user),
    flags_service: FeatureFlagsService = Depends(get_feature_flags_service),
) -> FlagInfoResponse:
    """Get information about a specific feature flag.

    This endpoint provides metadata about a feature flag including
    its default value, provider, and cache status.
    """
    correlation_id = get_correlation_id()

    try:
        flag_info = flags_service.get_flag_info(flag_name)

        logger.info(
            "Feature flag info retrieved via API",
            flag_name=flag_name,
            correlation_id=correlation_id,
        )

        return FlagInfoResponse(
            name=flag_info["name"],
            default_value=flag_info["default_value"],
            provider=flag_info["provider"],
            environment=flag_info["environment"],
            cached=flag_info["cached"],
            correlation_id=correlation_id,
        )

    except Exception as e:
        logger.error(
            "Error retrieving feature flag info via API",
            flag_name=flag_name,
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=500, detail="Internal server error during flag info retrieval"
        )


@router.post(
    "/cache/clear",
    summary="Clear feature flags cache",
    description="Clear the feature flags cache (admin only)",
)
async def clear_flags_cache(
    current_user: dict = Depends(get_current_user),
    flags_service: FeatureFlagsService = Depends(get_feature_flags_service),
) -> Dict[str, str]:
    """Clear the feature flags cache.

    This endpoint allows administrators to clear the feature flags cache,
    forcing fresh evaluation of all flags.
    """
    correlation_id = get_correlation_id()

    try:
        # Check if user has admin role
        user_roles = current_user.get("roles", [])
        if "admin" not in user_roles and "system_admin" not in user_roles:
            raise HTTPException(
                status_code=403, detail="Insufficient permissions to clear cache"
            )

        flags_service.clear_cache()

        logger.info(
            "Feature flags cache cleared via API",
            user_id_hash=flags_service._hash_user_id(current_user.get("sub"))
            if current_user.get("sub")
            else None,
            correlation_id=correlation_id,
        )

        return {
            "message": "Feature flags cache cleared successfully",
            "correlation_id": correlation_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error clearing feature flags cache via API",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=500, detail="Internal server error during cache clear"
        )


# Convenience endpoints for kill-switch flags
@router.get(
    "/video-calls/enabled",
    summary="Check if video calls are enabled",
    description="Check if video calls feature is enabled (kill-switch)",
)
async def is_video_calls_enabled(
    user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    flags_service: FeatureFlagsService = Depends(get_feature_flags_service),
) -> Dict[str, Any]:
    """Check if video calls feature is enabled."""
    correlation_id = get_correlation_id()
    effective_user_id = user_id or current_user.get("sub")

    enabled = flags_service.is_enabled(
        "video_calls_enabled", effective_user_id, default=False
    )

    return {
        "enabled": enabled,
        "flag_name": "video_calls_enabled",
        "user_id": effective_user_id,
        "correlation_id": correlation_id,
    }


@router.get(
    "/edi-integration/enabled",
    summary="Check if EDI integration is enabled",
    description="Check if EDI integration feature is enabled (kill-switch)",
)
async def is_edi_integration_enabled(
    user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    flags_service: FeatureFlagsService = Depends(get_feature_flags_service),
) -> Dict[str, Any]:
    """Check if EDI integration feature is enabled."""
    correlation_id = get_correlation_id()
    effective_user_id = user_id or current_user.get("sub")

    enabled = flags_service.is_enabled(
        "edi_integration_enabled", effective_user_id, default=False
    )

    return {
        "enabled": enabled,
        "flag_name": "edi_integration_enabled",
        "user_id": effective_user_id,
        "correlation_id": correlation_id,
    }


@router.get(
    "/payments/enabled",
    summary="Check if payments are enabled",
    description="Check if payments feature is enabled (kill-switch)",
)
async def is_payments_enabled(
    user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    flags_service: FeatureFlagsService = Depends(get_feature_flags_service),
) -> Dict[str, Any]:
    """Check if payments feature is enabled."""
    correlation_id = get_correlation_id()
    effective_user_id = user_id or current_user.get("sub")

    enabled = flags_service.is_enabled(
        "payments_enabled", effective_user_id, default=False
    )

    return {
        "enabled": enabled,
        "flag_name": "payments_enabled",
        "user_id": effective_user_id,
        "correlation_id": correlation_id,
    }

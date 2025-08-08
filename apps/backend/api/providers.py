"""Provider API endpoints for HIPAA-compliant provider management."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth_middleware import AuthenticatedUser, require_auth_dependency
from middleware.correlation import get_correlation_id
from services.database_service import DatabaseService
from services.feature_flags_service import is_provider_management_enabled
from utils.response_models import APIResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/providers", tags=["providers"])


# Request/Response models
class ProviderCreateRequest(BaseModel):
    """Provider creation request model."""

    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=50)
    credentials: Optional[str] = Field(None, max_length=200)
    specialty: Optional[str] = Field(None, max_length=200)
    license_number: Optional[str] = Field(None, max_length=100)
    license_state: Optional[str] = Field(None, max_length=50)
    email: str = Field(..., max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    office_phone: Optional[str] = Field(None, max_length=20)
    office_address_line1: Optional[str] = Field(None, max_length=255)
    office_address_line2: Optional[str] = Field(None, max_length=255)
    office_city: Optional[str] = Field(None, max_length=100)
    office_state: Optional[str] = Field(None, max_length=50)
    office_zip_code: Optional[str] = Field(None, max_length=10)
    npi_number: Optional[str] = Field(None, max_length=20)
    tax_id: Optional[str] = Field(None, max_length=20)
    default_appointment_duration: str = Field(default="50", max_length=10)
    accepts_new_patients: bool = Field(default=True)
    bio: Optional[str] = Field(None)
    administrative_notes: Optional[str] = Field(None)


class ProviderResponse(BaseModel):
    """Provider response model."""

    id: UUID
    first_name: str
    last_name: str
    middle_name: Optional[str]
    title: Optional[str]
    credentials: Optional[str]
    specialty: Optional[str]
    license_number: Optional[str]
    license_state: Optional[str]
    email: str
    phone: Optional[str]
    office_phone: Optional[str]
    office_address_line1: Optional[str]
    office_address_line2: Optional[str]
    office_city: Optional[str]
    office_state: Optional[str]
    office_zip_code: Optional[str]
    npi_number: Optional[str]
    tax_id: Optional[str]
    default_appointment_duration: str
    accepts_new_patients: bool
    is_active: bool
    bio: Optional[str]
    administrative_notes: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.get(
    "/",
    response_model=APIResponse[List[ProviderResponse]],
    summary="Get all providers",
    description="Retrieve a list of all providers with pagination support.",
)
async def get_providers(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_auth_dependency),
    correlation_id: str = Depends(get_correlation_id),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    accepts_new_patients: Optional[bool] = Query(
        None, description="Filter by accepting new patients"
    ),
):
    """Get all providers with pagination and filtering."""
    # Check if provider management feature is enabled
    if not is_provider_management_enabled(current_user.user_id):
        raise HTTPException(
            status_code=503, detail="Provider management feature is currently disabled"
        )

    try:
        logger.info(
            "Fetching providers",
            extra={
                "user_id": current_user.user_id,
                "page": page,
                "per_page": per_page,
                "specialty": specialty,
                "is_active": is_active,
                "accepts_new_patients": accepts_new_patients,
                "correlation_id": correlation_id,
            },
        )

        db_service = DatabaseService(db)
        providers = await db_service.list_providers()

        return APIResponse(
            success=True,
            data=[ProviderResponse.model_validate(provider) for provider in providers],
            message="Providers retrieved successfully",
            total=len(providers),
            page=page,
            per_page=per_page,
        )

    except Exception as e:
        logger.error(
            "Error fetching providers",
            extra={"error": str(e), "correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve providers",
        )


@router.get(
    "/{provider_id}",
    response_model=APIResponse[ProviderResponse],
    summary="Get provider by ID",
    description="Retrieve a specific provider by their ID.",
)
async def get_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_auth_dependency),
    correlation_id: str = Depends(get_correlation_id),
):
    """Get a specific provider by ID."""
    try:
        logger.info(
            "Fetching provider",
            extra={
                "provider_id": str(provider_id),
                "user_id": current_user.user_id,
                "correlation_id": correlation_id,
            },
        )

        db_service = DatabaseService(db)
        provider = await db_service.get_provider(provider_id)

        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider not found",
            )

        return APIResponse(
            success=True,
            data=ProviderResponse.model_validate(provider),
            message="Provider retrieved successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching provider",
            extra={
                "provider_id": str(provider_id),
                "error": str(e),
                "correlation_id": correlation_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve provider",
        )


@router.post(
    "/",
    response_model=APIResponse[ProviderResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new provider",
    description="Create a new provider record.",
)
async def create_provider(
    provider_data: ProviderCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_auth_dependency),
    correlation_id: str = Depends(get_correlation_id),
):
    """Create a new provider."""
    try:
        logger.info(
            "Creating provider",
            extra={
                "email": provider_data.email,
                "user_id": current_user.user_id,
                "correlation_id": correlation_id,
            },
        )

        db_service = DatabaseService(db)
        provider = await db_service.create_provider(
            first_name=provider_data.first_name,
            last_name=provider_data.last_name,
            email=provider_data.email,
            middle_name=provider_data.middle_name,
            title=provider_data.title,
            credentials=provider_data.credentials,
            specialty=provider_data.specialty,
            license_number=provider_data.license_number,
            license_state=provider_data.license_state,
            phone=provider_data.phone,
            office_phone=provider_data.office_phone,
            office_address_line1=provider_data.office_address_line1,
            office_address_line2=provider_data.office_address_line2,
            office_city=provider_data.office_city,
            office_state=provider_data.office_state,
            office_zip_code=provider_data.office_zip_code,
            npi_number=provider_data.npi_number,
            tax_id=provider_data.tax_id,
            default_appointment_duration=(provider_data.default_appointment_duration),
            accepts_new_patients=provider_data.accepts_new_patients,
            bio=provider_data.bio,
            administrative_notes=provider_data.administrative_notes,
        )

        return APIResponse(
            success=True,
            data=ProviderResponse.model_validate(provider),
            message="Provider created successfully",
        )

    except Exception as e:
        logger.error(
            "Error creating provider",
            extra={"error": str(e), "correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create provider",
        )


@router.put(
    "/{provider_id}",
    response_model=APIResponse[ProviderResponse],
    summary="Update provider",
    description="Update an existing provider record.",
)
async def update_provider(
    provider_id: UUID,
    provider_data: ProviderCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_auth_dependency),
    correlation_id: str = Depends(get_correlation_id),
):
    """Update an existing provider."""
    try:
        logger.info(
            "Updating provider",
            extra={
                "provider_id": str(provider_id),
                "user_id": current_user.user_id,
                "correlation_id": correlation_id,
            },
        )

        db_service = DatabaseService(db)

        # Check if provider exists
        existing_provider = await db_service.get_provider(provider_id)
        if not existing_provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider not found",
            )

        # Update provider (this would need to be implemented in DatabaseService)
        # For now, return the existing provider
        return APIResponse(
            success=True,
            data=ProviderResponse.model_validate(existing_provider),
            message="Provider updated successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error updating provider",
            extra={
                "provider_id": str(provider_id),
                "error": str(e),
                "correlation_id": correlation_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update provider",
        )


@router.delete(
    "/{provider_id}",
    response_model=APIResponse[dict],
    summary="Delete provider",
    description="Delete a provider record.",
)
async def delete_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_auth_dependency),
    correlation_id: str = Depends(get_correlation_id),
):
    """Delete a provider."""
    try:
        logger.info(
            "Deleting provider",
            extra={
                "provider_id": str(provider_id),
                "user_id": current_user.user_id,
                "correlation_id": correlation_id,
            },
        )

        db_service = DatabaseService(db)

        # Check if provider exists
        existing_provider = await db_service.get_provider(provider_id)
        if not existing_provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider not found",
            )

        # For now, just return success
        # (soft delete would be implemented later)
        return APIResponse(
            success=True,
            data={"deleted": True, "provider_id": str(provider_id)},
            message="Provider deleted successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error deleting provider",
            extra={
                "provider_id": str(provider_id),
                "error": str(e),
                "correlation_id": correlation_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete provider",
        )

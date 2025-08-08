"""Patient API endpoints for HIPAA-compliant patient management."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth_middleware import AuthenticatedUser, require_auth_dependency
from middleware.correlation import get_correlation_id
from services.database_service import DatabaseService
from services.feature_flags_service import is_enabled, is_patient_management_enabled
from utils.audit_logger import log_crud_action, log_data_access
from utils.response_models import APIResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/patients", tags=["patients"])


# Request/Response models
class PatientCreateRequest(BaseModel):
    """Patient creation request model."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    date_of_birth: str = Field(..., description="Date in YYYY-MM-DD format")
    address: Optional[str] = Field(None, max_length=500)
    emergency_contact_name: Optional[str] = Field(None, max_length=200)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)


class PatientUpdateRequest(BaseModel):
    """Patient update request model."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    date_of_birth: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")
    address: Optional[str] = Field(None, max_length=500)
    emergency_contact_name: Optional[str] = Field(None, max_length=200)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)


class PatientResponse(BaseModel):
    """Patient response model."""

    id: UUID
    first_name: str
    last_name: str
    email: str
    phone: str
    date_of_birth: str
    address: Optional[str]
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.get(
    "/",
    response_model=APIResponse[List[PatientResponse]],
    summary="Get all patients",
    description="Retrieve a list of all patients with pagination " "support.",
)
async def get_patients(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_auth_dependency),
    correlation_id: str = Depends(get_correlation_id),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
):
    """Get all patients with pagination."""
    # Check if patient management feature is enabled
    if not is_patient_management_enabled(current_user.user_id):
        raise HTTPException(
            status_code=503, detail="Patient management feature is currently disabled"
        )

    try:
        # Log data access for enhanced audit trail
        if is_enabled("audit_trail_enhanced", current_user.user_id):
            log_data_access(
                resource="Patient",
                user_id=current_user.user_id,
                correlation_id=correlation_id,
                query_params=dict(request.query_params),
                metadata={"action": "list_all", "enhanced_audit": True},
            )

        logger.info(
            "Fetching patients",
            extra={
                "user_id": current_user.user_id,
                "page": page,
                "per_page": per_page,
                "correlation_id": correlation_id,
            },
        )

        # TODO: Implement actual database query with DatabaseService
        db_service = DatabaseService()
        patients = await db_service.list_clients(active_only=True)

        return APIResponse(
            success=True,
            data=[
                PatientResponse(
                    id=p.id,
                    first_name=p.first_name,
                    last_name=p.last_name,
                    email=p.email,
                    phone=p.phone,
                    date_of_birth=p.date_of_birth,
                    address=getattr(p, "address", None),
                    emergency_contact_name=getattr(p, "emergency_contact_name", None),
                    emergency_contact_phone=getattr(p, "emergency_contact_phone", None),
                    created_at=p.created_at.isoformat(),
                    updated_at=p.updated_at.isoformat(),
                )
                for p in patients
            ],
            message="Patients retrieved successfully",
            total=len(patients),
            page=page,
            per_page=per_page,
        )

    except Exception as e:
        logger.error(
            "Error fetching patients",
            extra={"error": str(e), "correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve patients",
        )


@router.get(
    "/{patient_id}",
    response_model=APIResponse[PatientResponse],
    summary="Get patient by ID",
    description="Retrieve a specific patient by their ID.",
)
async def get_patient(
    patient_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_auth_dependency),
    correlation_id: str = Depends(get_correlation_id),
):
    """Get a specific patient by ID."""
    try:
        # Log data access for enhanced audit trail
        if is_enabled("audit_trail_enhanced", current_user.user_id):
            log_data_access(
                resource="Patient",
                user_id=current_user.user_id,
                correlation_id=correlation_id,
                resource_id=str(patient_id),
                metadata={"action": "get_by_id", "enhanced_audit": True},
            )

        logger.info(
            "Fetching patient",
            extra={
                "user_id": current_user.user_id,
                "patient_id": str(patient_id),
                "correlation_id": correlation_id,
            },
        )

        # TODO: Implement actual database query with DatabaseService
        db_service = DatabaseService()
        patient = await db_service.get_client(patient_id)

        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found",
            )

        return APIResponse(
            success=True,
            data=PatientResponse(
                id=patient.id,
                first_name=patient.first_name,
                last_name=patient.last_name,
                email=patient.email,
                phone=patient.phone,
                date_of_birth=patient.date_of_birth,
                address=getattr(patient, "address", None),
                emergency_contact_name=getattr(patient, "emergency_contact_name", None),
                emergency_contact_phone=getattr(
                    patient, "emergency_contact_phone", None
                ),
                created_at=patient.created_at.isoformat(),
                updated_at=patient.updated_at.isoformat(),
            ),
            message="Patient retrieved successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching patient",
            extra={
                "error": str(e),
                "patient_id": str(patient_id),
                "correlation_id": correlation_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve patient",
        )


@router.post(
    "/",
    response_model=APIResponse[PatientResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new patient",
    description="Create a new patient record.",
)
async def create_patient(
    patient_data: PatientCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_auth_dependency),
    correlation_id: str = Depends(get_correlation_id),
):
    """Create a new patient."""
    try:
        logger.info(
            "Creating patient",
            extra={
                "user_id": current_user.user_id,
                "correlation_id": correlation_id,
            },
        )

        # Create patient data dictionary
        patient_dict = {
            "first_name": patient_data.first_name,
            "last_name": patient_data.last_name,
            "email": patient_data.email,
            "phone": patient_data.phone,
            "date_of_birth": patient_data.date_of_birth,
            "address": patient_data.address,
            "emergency_contact_name": patient_data.emergency_contact_name,
            "emergency_contact_phone": patient_data.emergency_contact_phone,
            "is_active": True,
            "user_id": current_user.user_id,
        }

        # Create the patient using DatabaseService
        db_service = DatabaseService()
        new_patient = await db_service.create_client(patient_dict)

        # Enhanced audit logging
        if is_enabled("audit_trail_enhanced", current_user.user_id):
            log_crud_action(
                action="CREATE",
                resource="Patient",
                user_id=current_user.user_id,
                correlation_id=correlation_id,
                resource_id=str(new_patient.id),
                changes=patient_dict,
                metadata={"enhanced_audit": True},
            )

        return APIResponse(
            success=True,
            data=PatientResponse(
                id=new_patient.id,
                first_name=new_patient.first_name,
                last_name=new_patient.last_name,
                email=new_patient.email,
                phone=new_patient.phone,
                date_of_birth=new_patient.date_of_birth,
                address=getattr(new_patient, "address", None),
                emergency_contact_name=getattr(
                    new_patient, "emergency_contact_name", None
                ),
                emergency_contact_phone=getattr(
                    new_patient, "emergency_contact_phone", None
                ),
                created_at=new_patient.created_at.isoformat(),
                updated_at=new_patient.updated_at.isoformat(),
            ),
            message="Patient created successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error creating patient",
            extra={"error": str(e), "correlation_id": correlation_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create patient",
        )


@router.put(
    "/{patient_id}",
    response_model=APIResponse[PatientResponse],
    summary="Update patient",
    description="Update an existing patient record.",
)
async def update_patient(
    patient_id: UUID,
    patient_data: PatientUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_auth_dependency),
    correlation_id: str = Depends(get_correlation_id),
):
    """Update an existing patient with audit logging."""
    try:
        logger.info(
            "Updating patient",
            extra={
                "user_id": current_user.user_id,
                "patient_id": str(patient_id),
                "correlation_id": correlation_id,
            },
        )

        # Get existing patient for audit trail
        db_service = DatabaseService()
        existing_patient = await db_service.get_client(patient_id)

        if not existing_patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found",
            )

        # Prepare update data
        update_data = {}
        if patient_data.first_name is not None:
            update_data["first_name"] = patient_data.first_name
        if patient_data.last_name is not None:
            update_data["last_name"] = patient_data.last_name
        if patient_data.email is not None:
            update_data["email"] = patient_data.email
        if patient_data.phone is not None:
            update_data["phone"] = patient_data.phone
        if patient_data.date_of_birth is not None:
            update_data["date_of_birth"] = patient_data.date_of_birth
        if patient_data.address is not None:
            update_data["address"] = patient_data.address
        if patient_data.emergency_contact_name is not None:
            update_data["emergency_contact_name"] = patient_data.emergency_contact_name
        if patient_data.emergency_contact_phone is not None:
            update_data[
                "emergency_contact_phone"
            ] = patient_data.emergency_contact_phone

        # Update the patient
        updated_patient = await db_service.update_client(patient_id, update_data)

        # Enhanced audit logging
        if is_enabled("audit_trail_enhanced", current_user.user_id):
            log_crud_action(
                action="UPDATE",
                resource="Patient",
                user_id=current_user.user_id,
                correlation_id=correlation_id,
                resource_id=str(patient_id),
                changes=update_data,
                metadata={
                    "enhanced_audit": True,
                    "old_values": {
                        "first_name": existing_patient.first_name,
                        "last_name": existing_patient.last_name,
                        "email": existing_patient.email,
                        "phone": existing_patient.phone,
                    },
                },
            )

        return APIResponse(
            success=True,
            data=PatientResponse(
                id=updated_patient.id,
                first_name=updated_patient.first_name,
                last_name=updated_patient.last_name,
                email=updated_patient.email,
                phone=updated_patient.phone,
                date_of_birth=updated_patient.date_of_birth,
                address=getattr(updated_patient, "address", None),
                emergency_contact_name=getattr(
                    updated_patient, "emergency_contact_name", None
                ),
                emergency_contact_phone=getattr(
                    updated_patient, "emergency_contact_phone", None
                ),
                created_at=updated_patient.created_at.isoformat(),
                updated_at=updated_patient.updated_at.isoformat(),
            ),
            message="Patient updated successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error updating patient",
            extra={
                "error": str(e),
                "patient_id": str(patient_id),
                "correlation_id": correlation_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update patient",
        )


@router.delete(
    "/{patient_id}",
    response_model=APIResponse[dict],
    summary="Delete patient",
    description="Delete a patient record.",
)
async def delete_patient(
    patient_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_auth_dependency),
    correlation_id: str = Depends(get_correlation_id),
):
    """Delete a patient (soft delete) with audit logging."""
    try:
        logger.info(
            "Deleting patient",
            extra={
                "user_id": current_user.user_id,
                "patient_id": str(patient_id),
                "correlation_id": correlation_id,
            },
        )

        # Perform soft delete using DatabaseService
        db_service = DatabaseService()
        success = await db_service.delete_client(patient_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found",
            )

        # Enhanced audit logging
        if is_enabled("audit_trail_enhanced", current_user.user_id):
            log_crud_action(
                action="DELETE",
                resource="Patient",
                user_id=current_user.user_id,
                correlation_id=correlation_id,
                resource_id=str(patient_id),
                metadata={"enhanced_audit": True, "soft_delete": True},
            )

        return APIResponse(
            success=True, data={}, message="Patient deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error deleting patient",
            extra={
                "error": str(e),
                "patient_id": str(patient_id),
                "correlation_id": correlation_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete patient",
        )

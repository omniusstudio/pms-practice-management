"""Ledger API endpoints for financial transactions."""

from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_db
from middleware.auth_middleware import AuthenticatedUser, require_auth_dependency
from models.ledger import PaymentMethod, TransactionType
from services.database_service import DatabaseService
from services.feature_flags_service import is_financial_ledger_enabled

router = APIRouter(prefix="/ledger", tags=["ledger"])


class LedgerEntryCreateRequest(BaseModel):
    """Request model for creating a ledger entry."""

    client_id: UUID
    transaction_type: TransactionType
    amount: Decimal
    description: str = Field(..., max_length=500)
    service_date: Optional[date] = None
    billing_code: Optional[str] = Field(None, max_length=20)
    diagnosis_code: Optional[str] = Field(None, max_length=20)
    payment_method: Optional[PaymentMethod] = None
    reference_number: Optional[str] = Field(None, max_length=100)
    check_number: Optional[str] = Field(None, max_length=50)
    insurance_claim_number: Optional[str] = Field(None, max_length=100)
    insurance_authorization: Optional[str] = Field(None, max_length=100)
    is_posted: bool = True
    notes: Optional[str] = None


class LedgerEntryUpdateRequest(BaseModel):
    """Request model for updating a ledger entry."""

    transaction_type: Optional[TransactionType] = None
    amount: Optional[Decimal] = None
    description: Optional[str] = Field(None, max_length=500)
    service_date: Optional[date] = None
    billing_code: Optional[str] = Field(None, max_length=20)
    diagnosis_code: Optional[str] = Field(None, max_length=20)
    payment_method: Optional[PaymentMethod] = None
    reference_number: Optional[str] = Field(None, max_length=100)
    check_number: Optional[str] = Field(None, max_length=50)
    insurance_claim_number: Optional[str] = Field(None, max_length=100)
    insurance_authorization: Optional[str] = Field(None, max_length=100)
    is_posted: Optional[bool] = None
    notes: Optional[str] = None


class LedgerEntryResponse(BaseModel):
    """Response model for ledger entries."""

    id: UUID
    client_id: UUID
    transaction_type: TransactionType
    amount: Decimal
    description: str
    service_date: Optional[date]
    billing_code: Optional[str]
    diagnosis_code: Optional[str]
    payment_method: Optional[PaymentMethod]
    reference_number: Optional[str]
    check_number: Optional[str]
    insurance_claim_number: Optional[str]
    insurance_authorization: Optional[str]
    is_posted: bool
    is_reconciled: bool
    reconciliation_date: Optional[date]
    notes: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class ReconcileRequest(BaseModel):
    """Request model for reconciling a ledger entry."""

    reconciliation_date: Optional[date] = None


@router.get("/", response_model=List[LedgerEntryResponse])
async def get_ledger_entries(
    client_id: Optional[UUID] = Query(None, description="Filter by client ID"),
    transaction_type: Optional[TransactionType] = Query(
        None, description="Filter by transaction type"
    ),
    is_posted: Optional[bool] = Query(None, description="Filter by posted status"),
    is_reconciled: Optional[bool] = Query(
        None, description="Filter by reconciled status"
    ),
    service_date_from: Optional[date] = Query(
        None, description="Filter by service date from"
    ),
    service_date_to: Optional[date] = Query(
        None, description="Filter by service date to"
    ),
    skip: int = Query(0, ge=0, description="Number of entries to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of entries to return"),
    db: AsyncSession = Depends(get_async_db),
    current_user: AuthenticatedUser = Depends(require_auth_dependency),
) -> List[LedgerEntryResponse]:
    """Get ledger entries with optional filtering."""
    # Check if financial ledger feature is enabled
    if not is_financial_ledger_enabled(current_user.user_id):
        raise HTTPException(
            status_code=503, detail="Financial ledger feature is currently disabled"
        )

    # For now, return empty list - will be implemented with database service
    return []


@router.get("/{entry_id}", response_model=LedgerEntryResponse)
async def get_ledger_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> LedgerEntryResponse:
    """Get a specific ledger entry by ID."""
    db_service = DatabaseService(session=db)
    entry = await db_service.get_ledger_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Ledger entry not found")
    return LedgerEntryResponse.model_validate(entry)


@router.post("/", response_model=LedgerEntryResponse, status_code=201)
async def create_ledger_entry(
    entry_data: LedgerEntryCreateRequest,
    db: AsyncSession = Depends(get_async_db),
) -> LedgerEntryResponse:
    """Create a new ledger entry."""
    db_service = DatabaseService(session=db)
    entry_dict = {
        "client_id": entry_data.client_id,
        "transaction_type": entry_data.transaction_type,
        "amount": entry_data.amount,
        "description": entry_data.description,
        "service_date": entry_data.service_date,
        "billing_code": entry_data.billing_code,
        "diagnosis_code": entry_data.diagnosis_code,
        "payment_method": entry_data.payment_method,
        "reference_number": entry_data.reference_number,
        "check_number": entry_data.check_number,
        "insurance_claim_number": entry_data.insurance_claim_number,
        "insurance_authorization": entry_data.insurance_authorization,
        "is_posted": entry_data.is_posted,
        "notes": entry_data.notes,
    }
    entry = await db_service.create_ledger_entry(entry_dict)
    return LedgerEntryResponse.model_validate(entry)


@router.put("/{entry_id}", response_model=LedgerEntryResponse)
async def update_ledger_entry(
    entry_id: UUID,
    entry_data: LedgerEntryUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
) -> LedgerEntryResponse:
    """Update an existing ledger entry."""
    db_service = DatabaseService(session=db)
    # Check if entry exists
    existing_entry = await db_service.get_ledger_entry(entry_id)
    if not existing_entry:
        raise HTTPException(status_code=404, detail="Ledger entry not found")

    # Update entry
    updated_entry = await db_service.update_ledger_entry(
        entry_id=entry_id,
        **entry_data.model_dump(exclude_unset=True),
    )
    return LedgerEntryResponse.model_validate(updated_entry)


@router.delete("/{entry_id}", status_code=204)
async def delete_ledger_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> None:
    """Delete a ledger entry."""
    db_service = DatabaseService(session=db)
    # Check if entry exists
    existing_entry = await db_service.get_ledger_entry(entry_id)
    if not existing_entry:
        raise HTTPException(status_code=404, detail="Ledger entry not found")

    await db_service.delete_ledger_entry(entry_id)


@router.post("/{entry_id}/reconcile", response_model=LedgerEntryResponse)
async def reconcile_ledger_entry(
    entry_id: UUID,
    reconcile_data: ReconcileRequest,
    db: AsyncSession = Depends(get_async_db),
) -> LedgerEntryResponse:
    """Reconcile a ledger entry."""
    db_service = DatabaseService(session=db)
    # Check if entry exists
    existing_entry = await db_service.get_ledger_entry(entry_id)
    if not existing_entry:
        raise HTTPException(status_code=404, detail="Ledger entry not found")

    if existing_entry.is_reconciled:
        raise HTTPException(status_code=400, detail="Entry is already reconciled")

    # Update reconciliation status
    update_data = {
        "is_reconciled": True,
        "reconciliation_date": (reconcile_data.reconciliation_date or date.today()),
    }
    updated_entry = await db_service.update_ledger_entry(entry_id, update_data)
    return LedgerEntryResponse.model_validate(updated_entry)


@router.get("/client/{client_id}/balance")
async def get_client_balance(
    client_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """Get the current balance for a client."""
    db_service = DatabaseService(session=db)
    balance = await db_service.get_client_balance(client_id)
    return {
        "client_id": client_id,
        "balance": balance,
        "balance_formatted": f"${balance:.2f}",
    }

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.mock.edi_mock_service import EDIMockService
from services.mock.stripe_mock_service import StripeMockService
from services.mock.video_mock_service import VideoMockService
from utils.feature_flags import get_feature_flags
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/mock", tags=["mock-services"])

# Service instances
edi_service = EDIMockService()
stripe_service = StripeMockService()
video_service = VideoMockService()


# Pydantic models for request/response validation
class ClaimSubmissionRequest(BaseModel):
    patient_id: str = Field(..., min_length=1, description="Patient ID cannot be empty")
    provider_id: str
    services: List[Dict[str, Any]] = Field(
        ..., min_length=1, description="Services list cannot be empty"
    )
    claim_amount: float = Field(..., gt=0, description="Claim amount must be positive")
    diagnosis_codes: List[str]
    metadata: Optional[Dict[str, str]] = None


class PaymentIntentRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Amount must be positive")
    currency: str = Field(
        default="usd",
        pattern="^[a-z]{3}$",
        description="Currency must be 3-letter code",
    )
    customer_id: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


class CustomerRequest(BaseModel):
    email: str
    name: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


class SubscriptionRequest(BaseModel):
    customer_id: str
    price_id: str
    metadata: Optional[Dict[str, str]] = None


class VideoSessionRequest(BaseModel):
    session_name: str = Field(
        ..., min_length=1, description="Session name cannot be empty"
    )
    max_participants: int = Field(
        default=2, gt=0, description="Max participants must be positive"
    )
    recording_enabled: bool = True
    metadata: Optional[Dict[str, str]] = None


class JoinSessionRequest(BaseModel):
    participant_name: str
    participant_role: str = "patient"
    participant_metadata: Optional[Dict[str, str]] = None


# EDI Mock Endpoints
@router.post("/edi/submit-claim")
async def submit_edi_claim(
    request: ClaimSubmissionRequest, feature_flags=Depends(get_feature_flags)
) -> Dict[str, Any]:
    """Submit EDI 837 claim for processing."""
    if not feature_flags.is_mock_edi_enabled():
        raise HTTPException(status_code=503, detail="Mock EDI service is not enabled")

    try:
        claim_data = {
            "patient_id": request.patient_id,
            "provider_id": request.provider_id,
            "services": request.services,
            "claim_amount": request.claim_amount,
            "diagnosis_codes": request.diagnosis_codes,
            "metadata": request.metadata or {},
        }

        result = await edi_service.submit_837_claim(claim_data)

        await logger.ainfo(
            "EDI claim submitted",
            transaction_id=result.get("transaction_id"),
            status=result.get("status"),
        )

        return result

    except Exception as e:
        await logger.aerror("EDI claim submission failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edi/remittance/{transaction_id}")
async def get_edi_remittance(
    transaction_id: str, feature_flags=Depends(get_feature_flags)
) -> Dict[str, Any]:
    """Get EDI 835 remittance advice for a transaction."""
    if not feature_flags.is_mock_edi_enabled():
        raise HTTPException(status_code=503, detail="Mock EDI service is not enabled")

    try:
        # First get the claim status to check if it exists
        claim_status = await edi_service.get_claim_status(transaction_id)

        if "error" in claim_status:
            raise HTTPException(
                status_code=404, detail=f"Transaction not found: {transaction_id}"
            )

        # Generate remittance data based on the claim
        remittance_data = {
            "claim_id": claim_status.get("claim_id"),
            "provider_id": claim_status.get("provider_id"),
            "claim_amount": claim_status.get("claim_amount", 100.0),
            "payer_id": "PAYER001",
        }

        result = await edi_service.process_835_remittance(remittance_data)

        await logger.ainfo(
            "EDI remittance retrieved",
            transaction_id=transaction_id,
            remittance_id=result.get("remittance_id"),
        )

        # Flatten the response structure to match test expectations
        response = result.copy()
        response["transaction_id"] = transaction_id
        return response

    except HTTPException:
        raise
    except Exception as e:
        await logger.aerror(
            "EDI remittance retrieval failed",
            transaction_id=transaction_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edi/health")
async def get_edi_health(feature_flags=Depends(get_feature_flags)) -> Dict[str, Any]:
    """Get EDI service health status."""
    if not feature_flags.is_mock_edi_enabled():
        raise HTTPException(status_code=503, detail="Mock EDI service is not enabled")

    return await edi_service.get_service_health()


# Stripe Mock Endpoints
@router.post("/payments/payment-intents")
async def create_payment_intent(
    request: PaymentIntentRequest, feature_flags=Depends(get_feature_flags)
) -> Dict[str, Any]:
    """Create a Stripe payment intent."""
    if not feature_flags.is_mock_payments_enabled():
        raise HTTPException(
            status_code=503, detail="Mock payments service is not enabled"
        )

    try:
        result = await stripe_service.create_payment_intent(
            amount=request.amount,
            currency=request.currency,
            customer_id=request.customer_id,
            metadata=request.metadata,
        )

        await logger.ainfo(
            "Payment intent created",
            payment_intent_id=result.get("id"),
            amount=request.amount,
            status=result.get("status"),
        )

        return result

    except Exception as e:
        await logger.aerror("Payment intent creation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments/payment-intents/{payment_intent_id}")
async def get_payment_intent(
    payment_intent_id: str, feature_flags=Depends(get_feature_flags)
) -> Dict[str, Any]:
    """Retrieve a payment intent by ID."""
    if not feature_flags.is_mock_payments_enabled():
        raise HTTPException(
            status_code=503, detail="Mock payments service is not enabled"
        )

    try:
        result = await stripe_service.retrieve_payment_intent(payment_intent_id)

        if not result:
            raise HTTPException(
                status_code=404, detail=f"Payment intent {payment_intent_id} not found"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        await logger.aerror(
            "Payment intent retrieval failed",
            payment_intent_id=payment_intent_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payments/payment-intents/{payment_intent_id}/confirm")
async def confirm_payment_intent(
    payment_intent_id: str,
    payment_method: Optional[str] = None,
    feature_flags=Depends(get_feature_flags),
) -> Dict[str, Any]:
    """Confirm a payment intent."""
    if not feature_flags.is_mock_payments_enabled():
        raise HTTPException(
            status_code=503, detail="Mock payments service is not enabled"
        )

    try:
        result = await stripe_service.confirm_payment_intent(
            payment_intent_id, payment_method
        )

        await logger.ainfo(
            "Payment intent confirmed",
            payment_intent_id=payment_intent_id,
            status=result.get("status"),
        )

        return result

    except Exception as e:
        await logger.aerror(
            "Payment intent confirmation failed",
            payment_intent_id=payment_intent_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payments/customers")
async def create_customer(
    request: CustomerRequest, feature_flags=Depends(get_feature_flags)
) -> Dict[str, Any]:
    """Create a Stripe customer."""
    if not feature_flags.is_mock_payments_enabled():
        raise HTTPException(
            status_code=503, detail="Mock payments service is not enabled"
        )

    try:
        result = await stripe_service.create_customer(
            email=request.email, name=request.name, metadata=request.metadata
        )

        await logger.ainfo(
            "Customer created", customer_id=result.get("id"), email=request.email
        )

        return result

    except Exception as e:
        await logger.aerror("Customer creation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payments/subscriptions")
async def create_subscription(
    request: SubscriptionRequest, feature_flags=Depends(get_feature_flags)
) -> Dict[str, Any]:
    """Create a Stripe subscription."""
    if not feature_flags.is_mock_payments_enabled():
        raise HTTPException(
            status_code=503, detail="Mock payments service is not enabled"
        )

    try:
        result = await stripe_service.create_subscription(
            customer_id=request.customer_id,
            price_id=request.price_id,
            metadata=request.metadata,
        )

        await logger.ainfo(
            "Subscription created",
            subscription_id=result.get("id"),
            customer_id=request.customer_id,
            price_id=request.price_id,
        )

        return result

    except Exception as e:
        await logger.aerror("Subscription creation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments/health")
async def get_payments_health(
    feature_flags=Depends(get_feature_flags),
) -> Dict[str, Any]:
    """Get payments service health status."""
    if not feature_flags.is_mock_payments_enabled():
        raise HTTPException(
            status_code=503, detail="Mock payments service is not enabled"
        )

    return await stripe_service.get_service_health()


# Video Mock Endpoints
@router.post("/video/sessions")
async def create_video_session(
    request: VideoSessionRequest, feature_flags=Depends(get_feature_flags)
) -> Dict[str, Any]:
    """Create a video conferencing session."""
    if not feature_flags.is_mock_video_enabled():
        raise HTTPException(status_code=503, detail="Mock video service is not enabled")

    try:
        result = await video_service.create_session(
            session_name=request.session_name,
            max_participants=request.max_participants,
            recording_enabled=request.recording_enabled,
            metadata=request.metadata,
        )

        await logger.ainfo(
            "Video session created",
            session_id=result.get("id"),
            session_name=request.session_name,
        )

        return result

    except Exception as e:
        await logger.aerror("Video session creation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video/sessions/{session_id}/join")
async def join_video_session(
    session_id: str,
    request: JoinSessionRequest,
    feature_flags=Depends(get_feature_flags),
) -> Dict[str, Any]:
    """Join a video session as a participant."""
    if not feature_flags.is_mock_video_enabled():
        raise HTTPException(status_code=503, detail="Mock video service is not enabled")

    try:
        result = await video_service.join_session(
            session_id=session_id,
            participant_name=request.participant_name,
            participant_role=request.participant_role,
            participant_metadata=request.participant_metadata,
        )

        await logger.ainfo(
            "Participant joined video session",
            session_id=session_id,
            participant_name=request.participant_name,
            participant_role=request.participant_role,
        )

        return result

    except Exception as e:
        await logger.aerror(
            "Video session join failed", session_id=session_id, error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/video/sessions/{session_id}/participants/{participant_id}")
async def leave_video_session(
    session_id: str, participant_id: str, feature_flags=Depends(get_feature_flags)
) -> Dict[str, Any]:
    """Leave a video session."""
    if not feature_flags.is_mock_video_enabled():
        raise HTTPException(status_code=503, detail="Mock video service is not enabled")

    try:
        result = await video_service.leave_session(
            session_id=session_id, participant_id=participant_id
        )

        await logger.ainfo(
            "Participant left video session",
            session_id=session_id,
            participant_id=participant_id,
        )

        return result

    except Exception as e:
        await logger.aerror(
            "Video session leave failed",
            session_id=session_id,
            participant_id=participant_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/sessions/{session_id}")
async def get_video_session(
    session_id: str, feature_flags=Depends(get_feature_flags)
) -> Dict[str, Any]:
    """Get video session information."""
    if not feature_flags.is_mock_video_enabled():
        raise HTTPException(status_code=503, detail="Mock video service is not enabled")

    try:
        result = await video_service.get_session_info(session_id)

        if not result:
            raise HTTPException(
                status_code=404, detail=f"Video session {session_id} not found"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        await logger.aerror(
            "Video session retrieval failed", session_id=session_id, error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/recordings")
async def list_video_recordings(
    session_id: Optional[str] = None, feature_flags=Depends(get_feature_flags)
) -> List[Dict[str, Any]]:
    """List video recordings."""
    if not feature_flags.is_mock_video_enabled():
        raise HTTPException(status_code=503, detail="Mock video service is not enabled")

    try:
        result = await video_service.list_recordings(session_id)
        return result

    except Exception as e:
        await logger.aerror("Video recordings listing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/recordings/{recording_id}")
async def get_video_recording(
    recording_id: str, feature_flags=Depends(get_feature_flags)
) -> Dict[str, Any]:
    """Get video recording information."""
    if not feature_flags.is_mock_video_enabled():
        raise HTTPException(status_code=503, detail="Mock video service is not enabled")

    try:
        result = await video_service.get_recording_info(recording_id)

        if not result:
            raise HTTPException(
                status_code=404, detail=f"Video recording {recording_id} not found"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        await logger.aerror(
            "Video recording retrieval failed", recording_id=recording_id, error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/health")
async def get_video_health(feature_flags=Depends(get_feature_flags)) -> Dict[str, Any]:
    """Get video service health status."""
    if not feature_flags.is_mock_video_enabled():
        raise HTTPException(status_code=503, detail="Mock video service is not enabled")

    return await video_service.get_service_health()


# General health endpoint
@router.get("/health")
async def get_mock_services_health(
    feature_flags=Depends(get_feature_flags),
) -> Dict[str, Any]:
    """Get overall mock services health status."""
    services: Dict[str, Any] = {}

    if feature_flags.is_mock_edi_enabled():
        services["edi"] = await edi_service.get_service_health()

    if feature_flags.is_mock_payments_enabled():
        services["payments"] = await stripe_service.get_service_health()

    if feature_flags.is_mock_video_enabled():
        services["video"] = await video_service.get_service_health()

    return {"timestamp": "2024-01-01T00:00:00Z", "services": services}

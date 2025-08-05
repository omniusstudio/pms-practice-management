"""Event API endpoints for event bus and ETL management."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from middleware.correlation import get_correlation_id
from schemas.events import (
    AuthEvent,
    BaseEvent,
    BusinessEvent,
    CRUDEvent,
    EventSeverity,
    EventType,
    SystemEvent,
)
from services.etl_pipeline import ETLError, get_etl_pipeline
from services.event_bus import EventBusError, get_event_bus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["events"])


# Request/Response models
class PublishEventRequest(BaseModel):
    """Request model for publishing events."""

    event_type: EventType = Field(..., description="Type of event")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: str = Field(
        ..., description="Resource identifier (will be PHI-scrubbed)"
    )
    severity: EventSeverity = Field(
        default=EventSeverity.LOW, description="Event severity"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional event metadata"
    )
    user_id: Optional[str] = Field(
        None, description="User ID (will be PHI-scrubbed if needed)"
    )

    # Event-specific fields
    operation: Optional[str] = Field(
        None, description="CRUD operation (for CRUD events)"
    )
    changes: Optional[Dict[str, Any]] = Field(
        None, description="Changes made (for CRUD events)"
    )
    auth_type: Optional[str] = Field(
        None, description="Authentication type (for auth events)"
    )
    success: Optional[bool] = Field(
        None, description="Success status (for auth events)"
    )
    ip_address: Optional[str] = Field(None, description="Client IP (for auth events)")
    user_agent: Optional[str] = Field(None, description="User agent (for auth events)")
    component: Optional[str] = Field(
        None, description="System component (for system events)"
    )
    error_code: Optional[str] = Field(
        None, description="Error code (for system events)"
    )
    stack_trace: Optional[str] = Field(
        None, description="Stack trace (for system events)"
    )
    business_process: Optional[str] = Field(
        None, description="Business process (for business events)"
    )
    outcome: Optional[str] = Field(
        None, description="Process outcome (for business events)"
    )
    duration_ms: Optional[int] = Field(
        None, description="Duration in ms (for business events)"
    )


class PublishEventResponse(BaseModel):
    """Response model for event publishing."""

    event_id: str = Field(..., description="Published event ID")
    correlation_id: str = Field(..., description="Request correlation ID")
    status: str = Field(default="published", description="Publishing status")


class EventBusStatusResponse(BaseModel):
    """Response model for event bus status."""

    connected: bool = Field(..., description="Connection status")
    environment: str = Field(..., description="Current environment")
    stream_info: Dict[str, Any] = Field(..., description="Stream information")
    subscribers: int = Field(..., description="Number of active subscribers")


class ETLStatusResponse(BaseModel):
    """Response model for ETL pipeline status."""

    running: bool = Field(..., description="Pipeline running status")
    events_processed: int = Field(..., description="Total events processed")
    batches_processed: int = Field(..., description="Total batches processed")
    errors_count: int = Field(..., description="Total error count")
    buffer_size: int = Field(..., description="Current buffer size")
    environment: str = Field(..., description="Current environment")
    s3_bucket: str = Field(..., description="S3 bucket for data storage")


# Dependency functions
async def get_event_bus_service() -> Any:
    """Get event bus service dependency."""
    try:
        return get_event_bus()
    except EventBusError as e:
        raise HTTPException(status_code=503, detail=f"Event bus not available: {e}")


async def get_etl_service() -> Any:
    """Get ETL pipeline service dependency."""
    try:
        return get_etl_pipeline()
    except ETLError as e:
        raise HTTPException(status_code=503, detail=f"ETL pipeline not available: {e}")


# API endpoints
@router.post("/publish", response_model=PublishEventResponse)
async def publish_event(
    request: PublishEventRequest,
    correlation_id: str = Depends(get_correlation_id),
    event_bus=Depends(get_event_bus_service),
) -> PublishEventResponse:
    """Publish an event to the event bus.

    This endpoint allows publishing various types of events with automatic
    PHI scrubbing and correlation ID tracking.
    """
    try:
        # Create appropriate event based on type and provided fields
        event_data = {
            "event_type": request.event_type,
            "correlation_id": correlation_id,
            "resource_type": request.resource_type,
            "resource_id": request.resource_id,
            "severity": request.severity,
            "metadata": request.metadata,
            "user_id": request.user_id,
        }

        # Determine event class and add specific fields
        if request.operation is not None:
            # CRUD event
            event_data.update(
                {
                    "operation": request.operation,
                    "changes": request.changes,
                }
            )
            event_data["metadata"]["category"] = "crud"
            event = CRUDEvent(**event_data)

        elif request.auth_type is not None:
            # Auth event
            event_data.update(
                {
                    "auth_type": request.auth_type,
                    "success": request.success or False,
                    "ip_address": request.ip_address,
                    "user_agent": request.user_agent,
                }
            )
            event_data["metadata"]["category"] = "auth"
            event = AuthEvent(**event_data)

        elif request.component is not None:
            # System event
            event_data.update(
                {
                    "component": request.component,
                    "error_code": request.error_code,
                    "stack_trace": request.stack_trace,
                }
            )
            event_data["metadata"]["category"] = "system"
            event = SystemEvent(**event_data)

        elif request.business_process is not None:
            # Business event
            event_data.update(
                {
                    "business_process": request.business_process,
                    "outcome": request.outcome or "SUCCESS",
                    "duration_ms": request.duration_ms,
                }
            )
            event_data["metadata"]["category"] = "business"
            event = BusinessEvent(**event_data)

        else:
            # Base event
            event = BaseEvent(**event_data)

        # Publish event
        event_id = await event_bus.publish_event(event, correlation_id)

        logger.info(
            "Event published via API",
            extra={
                "event_id": event_id,
                "event_type": request.event_type,
                "correlation_id": correlation_id,
            },
        )

        return PublishEventResponse(event_id=event_id, correlation_id=correlation_id)

    except Exception as e:
        logger.error(
            "Failed to publish event via API",
            extra={
                "event_type": request.event_type,
                "correlation_id": correlation_id,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=500, detail=f"Event publishing failed: {e}")


@router.get("/bus/status", response_model=EventBusStatusResponse)
async def get_event_bus_status(
    event_bus=Depends(get_event_bus_service),
) -> EventBusStatusResponse:
    """Get event bus status and metrics."""
    try:
        stream_info = await event_bus.get_stream_info()

        return EventBusStatusResponse(
            connected=event_bus._redis is not None,
            environment=event_bus.environment,
            stream_info=stream_info,
            subscribers=len(event_bus._subscribers),
        )

    except Exception as e:
        logger.error("Failed to get event bus status", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {e}")


@router.get("/etl/status", response_model=ETLStatusResponse)
async def get_etl_status(etl_pipeline=Depends(get_etl_service)) -> ETLStatusResponse:
    """Get ETL pipeline status and metrics."""
    try:
        metrics = etl_pipeline.get_metrics()

        return ETLStatusResponse(
            running=metrics["running"],
            events_processed=metrics["events_processed"],
            batches_processed=metrics["batches_processed"],
            errors_count=metrics["errors_count"],
            buffer_size=metrics["buffer_size"],
            environment=metrics["environment"],
            s3_bucket=metrics["s3_bucket"],
        )

    except Exception as e:
        logger.error("Failed to get ETL status", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"ETL status retrieval failed: {e}")


@router.post("/etl/start")
async def start_etl_pipeline(
    background_tasks: BackgroundTasks, etl_pipeline=Depends(get_etl_service)
) -> Dict[str, str]:
    """Start the ETL pipeline."""
    try:
        background_tasks.add_task(etl_pipeline.start)

        logger.info("ETL pipeline start requested via API")

        return {"status": "starting", "message": "ETL pipeline start initiated"}

    except Exception as e:
        logger.error("Failed to start ETL pipeline", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"ETL pipeline start failed: {e}")


@router.post("/etl/stop")
async def stop_etl_pipeline(
    background_tasks: BackgroundTasks, etl_pipeline=Depends(get_etl_service)
) -> Dict[str, str]:
    """Stop the ETL pipeline."""
    try:
        background_tasks.add_task(etl_pipeline.stop)

        logger.info("ETL pipeline stop requested via API")

        return {"status": "stopping", "message": "ETL pipeline stop initiated"}

    except Exception as e:
        logger.error("Failed to stop ETL pipeline", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"ETL pipeline stop failed: {e}")


@router.get("/types")
async def get_event_types() -> Dict[str, List[str]]:
    """Get available event types and severities."""
    return {
        "event_types": [event_type.value for event_type in EventType],
        "severities": [severity.value for severity in EventSeverity],
    }

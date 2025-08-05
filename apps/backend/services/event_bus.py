"""HIPAA-compliant event bus service for PMS system."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Union

import redis.asyncio as redis
from pydantic import ValidationError

from schemas.events import BaseEvent, create_event_from_dict
from utils.phi_scrubber import scrub_phi_from_dict

logger = logging.getLogger(__name__)


class EventBusError(Exception):
    """Base exception for event bus operations."""

    pass


class EventPublishError(EventBusError):
    """Exception raised when event publishing fails."""

    pass


class EventSubscriptionError(EventBusError):
    """Exception raised when event subscription fails."""

    pass


class EventBus:
    """HIPAA-compliant event bus using Redis Streams.

    Features:
    - PHI scrubbing for all events
    - Correlation ID tracking
    - Environment-specific routing
    - Dead letter queue for failed events
    - Audit logging for all operations
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        environment: str = "development",
        stream_prefix: str = "pms_events",
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize event bus.

        Args:
            redis_url: Redis connection URL
            environment: Current environment (dev/staging/prod)
            stream_prefix: Prefix for Redis stream names
            max_retries: Maximum retry attempts for failed operations
            retry_delay: Delay between retry attempts in seconds
        """
        self.redis_url = redis_url
        self.environment = environment
        self.stream_prefix = stream_prefix
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self._redis: Optional[redis.Redis] = None
        self._subscribers: Dict[str, List[Callable]] = {}
        self._consumer_tasks: Set[asyncio.Task] = set()
        self._running = False

        # Stream names
        self.main_stream = f"{stream_prefix}:{environment}"
        self.dlq_stream = f"{stream_prefix}:dlq:{environment}"
        self.audit_stream = f"{stream_prefix}:audit:{environment}"

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self._redis = redis.from_url(
                self.redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                health_check_interval=30,
            )

            # Test connection
            await self._redis.ping()

            logger.info(
                "Connected to Redis event bus",
                extra={
                    "environment": self.environment,
                    "stream_prefix": self.stream_prefix,
                },
            )

        except Exception as e:
            logger.error(
                "Failed to connect to Redis event bus",
                extra={"error": str(e), "redis_url": self.redis_url},
            )
            raise EventBusError(f"Redis connection failed: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Redis and cleanup resources."""
        self._running = False

        # Cancel all consumer tasks
        for task in self._consumer_tasks:
            task.cancel()

        if self._consumer_tasks:
            await asyncio.gather(*self._consumer_tasks, return_exceptions=True)

        if self._redis:
            await self._redis.close()
            self._redis = None

        logger.info("Disconnected from Redis event bus")

    async def publish_event(
        self, event: BaseEvent, correlation_id: Optional[str] = None
    ) -> str:
        """Publish event to the bus with PHI scrubbing.

        Args:
            event: Event to publish
            correlation_id: Optional correlation ID override

        Returns:
            Event ID of published event

        Raises:
            EventPublishError: If publishing fails
        """
        if not self._redis:
            raise EventPublishError("Event bus not connected")

        try:
            # Override correlation ID if provided
            if correlation_id:
                event.correlation_id = correlation_id

            # Ensure environment matches
            event.environment = self.environment

            # Convert to dict and scrub PHI
            event_dict = event.dict()
            scrubbed_dict = scrub_phi_from_dict(event_dict)

            # Add publishing metadata
            scrubbed_dict["published_at"] = datetime.now(timezone.utc).isoformat()
            scrubbed_dict["publisher"] = "event_bus"

            # Publish to main stream
            stream_id = await self._redis.xadd(
                self.main_stream, scrubbed_dict, maxlen=10000  # Keep last 10k events
            )

            # Audit log the publication
            await self._audit_event_operation(
                "PUBLISH",
                event.event_type,
                event.event_id,
                event.correlation_id,
                {"stream_id": stream_id},
            )

            logger.info(
                "Event published successfully",
                extra={
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "correlation_id": event.correlation_id,
                    "stream_id": stream_id,
                },
            )

            return event.event_id

        except Exception as e:
            logger.error(
                "Failed to publish event",
                extra={
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "error": str(e),
                },
            )
            raise EventPublishError(f"Event publishing failed: {e}")

    async def subscribe(
        self,
        event_type: str,
        handler: Union[
            Callable[[BaseEvent], None],
            Callable[[BaseEvent], Coroutine[Any, Any, None]],
        ],
        consumer_group: str = "default",
    ) -> None:
        """Subscribe to events of a specific type.

        Args:
            event_type: Type of events to subscribe to
            handler: Async function to handle events
            consumer_group: Consumer group name for load balancing
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(handler)

        # Start consumer task if not already running
        if not self._running:
            await self._start_consumers(consumer_group)

        logger.info(
            "Subscribed to event type",
            extra={
                "event_type": event_type,
                "consumer_group": consumer_group,
                "handler": handler.__name__,
            },
        )

    async def _start_consumers(self, consumer_group: str) -> None:
        """Start event consumer tasks."""
        if not self._redis:
            raise EventSubscriptionError("Event bus not connected")

        self._running = True

        try:
            # Create consumer group if it doesn't exist
            try:
                await self._redis.xgroup_create(
                    self.main_stream, consumer_group, id="0", mkstream=True
                )
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise

            # Start consumer task
            task = asyncio.create_task(self._consume_events(consumer_group))
            self._consumer_tasks.add(task)

            logger.info(
                "Started event consumers", extra={"consumer_group": consumer_group}
            )

        except Exception as e:
            logger.error("Failed to start event consumers", extra={"error": str(e)})
            raise EventSubscriptionError(f"Consumer startup failed: {e}")

    async def _consume_events(self, consumer_group: str) -> None:
        """Consume events from Redis stream."""
        task = asyncio.current_task()
        task_name = task.get_name() if task else "unknown"
        consumer_name = f"consumer_{task_name}"

        while self._running:
            try:
                # Read from stream
                if not self._redis:
                    break
                messages = await self._redis.xreadgroup(
                    consumer_group,
                    consumer_name,
                    {self.main_stream: ">"},
                    count=10,
                    block=1000,  # 1 second timeout
                )

                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        await self._process_message(
                            msg_id, fields, consumer_group, consumer_name
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Error in event consumer",
                    extra={
                        "error": str(e),
                        "consumer_group": consumer_group,
                        "consumer_name": consumer_name,
                    },
                )
                await asyncio.sleep(self.retry_delay)

    async def _process_message(
        self,
        msg_id: str,
        fields: Dict[str, Any],
        consumer_group: str,
        consumer_name: str,
    ) -> None:
        """Process a single event message."""
        try:
            # Reconstruct event from fields
            event = create_event_from_dict(fields)

            # Find and execute handlers
            handlers = self._subscribers.get(event.event_type, [])

            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)

                except Exception as e:
                    logger.error(
                        "Event handler failed",
                        extra={
                            "event_id": event.event_id,
                            "event_type": event.event_type,
                            "handler": handler.__name__,
                            "error": str(e),
                        },
                    )
                    # Continue processing other handlers

            # Acknowledge message
            if self._redis:
                await self._redis.xack(self.main_stream, consumer_group, msg_id)

            # Audit successful processing
            await self._audit_event_operation(
                "PROCESS",
                event.event_type,
                event.event_id,
                event.correlation_id,
                {"msg_id": msg_id, "handlers_count": len(handlers)},
            )

        except ValidationError as e:
            logger.error(
                "Invalid event format",
                extra={"msg_id": msg_id, "fields": fields, "error": str(e)},
            )
            # Move to dead letter queue
            await self._move_to_dlq(msg_id, fields, str(e))

        except Exception as e:
            logger.error(
                "Failed to process event", extra={"msg_id": msg_id, "error": str(e)}
            )
            # Move to dead letter queue
            await self._move_to_dlq(msg_id, fields, str(e))

    async def _move_to_dlq(
        self, msg_id: str, fields: Dict[str, Any], error: str
    ) -> None:
        """Move failed message to dead letter queue."""
        try:
            dlq_fields = fields.copy()
            dlq_fields.update(
                {
                    "original_msg_id": msg_id,
                    "error": error,
                    "dlq_timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            if self._redis:
                await self._redis.xadd(
                    self.dlq_stream,
                    dlq_fields,
                    maxlen=1000,  # Keep last 1k failed events
                )

            logger.warning(
                "Event moved to dead letter queue",
                extra={"msg_id": msg_id, "error": error},
            )

        except Exception as e:
            logger.error(
                "Failed to move event to DLQ", extra={"msg_id": msg_id, "error": str(e)}
            )

    async def _audit_event_operation(
        self,
        operation: str,
        event_type: str,
        event_id: str,
        correlation_id: str,
        metadata: Dict[str, Any],
    ) -> None:
        """Audit event bus operations."""
        try:
            audit_data = {
                "operation": operation,
                "event_type": event_type,
                "event_id": event_id,
                "correlation_id": correlation_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "environment": self.environment,
                "metadata": json.dumps(metadata),
            }

            if self._redis:
                await self._redis.xadd(
                    self.audit_stream,
                    audit_data,
                    maxlen=50000,  # Keep last 50k audit events
                )

        except Exception as e:
            logger.error(
                "Failed to audit event operation",
                extra={"operation": operation, "event_id": event_id, "error": str(e)},
            )

    async def get_stream_info(self) -> Dict[str, Any]:
        """Get information about event streams."""
        if not self._redis:
            raise EventBusError("Event bus not connected")

        try:
            info = {}

            for stream_name in [self.main_stream, self.dlq_stream, self.audit_stream]:
                try:
                    stream_info = await self._redis.xinfo_stream(stream_name)
                    info[stream_name] = {
                        "length": stream_info.get("length", 0),
                        "first_entry": stream_info.get("first-entry"),
                        "last_entry": stream_info.get("last-entry"),
                        "groups": stream_info.get("groups", 0),
                    }
                except redis.ResponseError:
                    # Stream doesn't exist yet
                    info[stream_name] = {"length": 0, "exists": False}

            return info

        except Exception as e:
            logger.error("Failed to get stream info", extra={"error": str(e)})
            raise EventBusError(f"Stream info retrieval failed: {e}")


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get global event bus instance."""
    if _event_bus is None:
        raise EventBusError("Event bus not initialized")
    return _event_bus


def initialize_event_bus(
    redis_url: str = "redis://localhost:6379", environment: str = "development"
) -> EventBus:
    """Initialize global event bus instance."""
    global _event_bus
    _event_bus = EventBus(redis_url=redis_url, environment=environment)
    return _event_bus

"""ETL Pipeline service for analytics and reporting."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from schemas.events import BaseEvent
from services.event_bus import get_event_bus
from utils.phi_scrubber import scrub_phi_from_dict

logger = logging.getLogger(__name__)


class ETLError(Exception):
    """Base exception for ETL operations."""

    pass


class DataExtractionError(ETLError):
    """Exception raised during data extraction."""

    pass


class DataTransformationError(ETLError):
    """Exception raised during data transformation."""

    pass


class DataLoadError(ETLError):
    """Exception raised during data loading."""

    pass


class ETLPipeline:
    """HIPAA-compliant ETL pipeline for analytics data.

    Features:
    - Event-driven data extraction
    - PHI scrubbing and anonymization
    - Batch processing with configurable intervals
    - S3 data lake storage
    - Athena-compatible partitioning
    - Error handling and retry logic
    """

    def __init__(
        self,
        environment: str = "development",
        s3_bucket: str = "pms-analytics-data",
        s3_prefix: str = "events",
        batch_size: int = 1000,
        batch_interval: int = 300,  # 5 minutes
        aws_region: str = "us-east-1",
    ):
        """Initialize ETL pipeline.

        Args:
            environment: Current environment
            s3_bucket: S3 bucket for data storage
            s3_prefix: S3 key prefix for events
            batch_size: Maximum events per batch
            batch_interval: Batch processing interval in seconds
            aws_region: AWS region for services
        """
        self.environment = environment
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.aws_region = aws_region

        # AWS clients
        self.s3_client = boto3.client("s3", region_name=aws_region)

        # Event buffer for batching
        self._event_buffer: List[Dict[str, Any]] = []
        self._buffer_lock = asyncio.Lock()
        self._processing_task: Optional[asyncio.Task] = None
        self._running = False

        # Metrics
        self._events_processed = 0
        self._batches_processed = 0
        self._errors_count = 0

    async def start(self) -> None:
        """Start the ETL pipeline."""
        if self._running:
            logger.warning("ETL pipeline already running")
            return

        self._running = True

        try:
            # Subscribe to all events
            event_bus = get_event_bus()
            await event_bus.subscribe(
                "*",  # Subscribe to all event types
                self._handle_event,
                consumer_group="etl_pipeline",
            )

            # Start batch processing task
            self._processing_task = asyncio.create_task(self._batch_processor())

            logger.info(
                "ETL pipeline started",
                extra={
                    "environment": self.environment,
                    "batch_size": self.batch_size,
                    "batch_interval": self.batch_interval,
                },
            )

        except Exception as e:
            self._running = False
            logger.error("Failed to start ETL pipeline", extra={"error": str(e)})
            raise ETLError(f"ETL pipeline startup failed: {e}")

    async def stop(self) -> None:
        """Stop the ETL pipeline."""
        self._running = False

        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        # Process remaining events in buffer
        if self._event_buffer:
            await self._process_batch()

        logger.info("ETL pipeline stopped")

    async def _handle_event(self, event: BaseEvent) -> None:
        """Handle incoming event for ETL processing.

        Args:
            event: Event to process
        """
        try:
            # Transform event for analytics
            transformed_event = await self._transform_event(event)

            # Add to buffer
            async with self._buffer_lock:
                self._event_buffer.append(transformed_event)

                # Process batch if buffer is full
                if len(self._event_buffer) >= self.batch_size:
                    await self._process_batch()

        except Exception as e:
            self._errors_count += 1
            logger.error(
                "Failed to handle event in ETL pipeline",
                extra={
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "error": str(e),
                },
            )

    async def _transform_event(self, event: BaseEvent) -> Dict[str, Any]:
        """Transform event for analytics storage.

        Args:
            event: Original event

        Returns:
            Transformed event data

        Raises:
            DataTransformationError: If transformation fails
        """
        try:
            # Convert to dict and scrub PHI
            event_dict = event.dict()
            scrubbed_dict = scrub_phi_from_dict(event_dict)

            # Add ETL metadata
            transformed = {
                "event_id": scrubbed_dict["event_id"],
                "event_type": scrubbed_dict["event_type"],
                "timestamp": scrubbed_dict["timestamp"],
                "correlation_id": scrubbed_dict["correlation_id"],
                "environment": scrubbed_dict["environment"],
                "resource_type": scrubbed_dict["resource_type"],
                "resource_id": scrubbed_dict["resource_id"],
                "severity": scrubbed_dict["severity"],
                "metadata": scrubbed_dict.get("metadata", {}),
                # ETL-specific fields
                "etl_processed_at": datetime.now(timezone.utc).isoformat(),
                "etl_version": "1.0",
                "data_classification": self._classify_event(event),
                # Partitioning fields for Athena
                "year": event.timestamp.year,
                "month": event.timestamp.month,
                "day": event.timestamp.day,
                "hour": event.timestamp.hour,
            }

            # Add event-specific transformations
            if hasattr(event, "operation"):
                transformed["operation"] = getattr(event, "operation")

            if hasattr(event, "auth_type"):
                transformed["auth_type"] = getattr(event, "auth_type")
                transformed["success"] = getattr(event, "success", None)

            if hasattr(event, "component"):
                transformed["component"] = getattr(event, "component")
                transformed["error_code"] = getattr(event, "error_code", None)

            if hasattr(event, "business_process"):
                transformed["business_process"] = getattr(event, "business_process")
                transformed["outcome"] = getattr(event, "outcome")
                transformed["duration_ms"] = getattr(event, "duration_ms", None)

            return transformed

        except Exception as e:
            logger.error(
                "Event transformation failed",
                extra={"event_id": event.event_id, "error": str(e)},
            )
            raise DataTransformationError(f"Transformation failed: {e}")

    def _classify_event(self, event: BaseEvent) -> str:
        """Classify event for data governance.

        Args:
            event: Event to classify

        Returns:
            Data classification level
        """
        # Classify based on event type and content
        if "auth" in event.event_type.lower():
            return "sensitive"
        elif "audit" in event.event_type.lower():
            return "restricted"
        elif "payment" in event.event_type.lower():
            return "confidential"
        elif "system" in event.event_type.lower():
            return "internal"
        else:
            return "general"

    async def _batch_processor(self) -> None:
        """Background task for batch processing."""
        while self._running:
            try:
                await asyncio.sleep(self.batch_interval)

                async with self._buffer_lock:
                    if self._event_buffer:
                        await self._process_batch()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._errors_count += 1
                logger.error("Batch processor error", extra={"error": str(e)})
                await asyncio.sleep(60)  # Wait before retrying

    async def _process_batch(self) -> None:
        """Process current batch of events.

        Note: This method assumes _buffer_lock is already acquired.
        """
        if not self._event_buffer:
            return

        batch = self._event_buffer.copy()
        self._event_buffer.clear()

        try:
            # Group events by partition for efficient storage
            partitioned_events = self._partition_events(batch)

            # Upload each partition
            for partition_key, events in partitioned_events.items():
                await self._upload_partition(partition_key, events)

            self._batches_processed += 1
            self._events_processed += len(batch)

            logger.info(
                "Batch processed successfully",
                extra={
                    "batch_size": len(batch),
                    "partitions": len(partitioned_events),
                    "total_events": self._events_processed,
                    "total_batches": self._batches_processed,
                },
            )

        except Exception as e:
            self._errors_count += 1
            logger.error(
                "Batch processing failed",
                extra={"batch_size": len(batch), "error": str(e)},
            )
            # Re-add events to buffer for retry
            self._event_buffer.extend(batch)
            raise DataLoadError(f"Batch processing failed: {e}")

    def _partition_events(
        self, events: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Partition events by date and type for efficient storage.

        Args:
            events: List of events to partition

        Returns:
            Dictionary mapping partition keys to event lists
        """
        partitions: Dict[str, List[Dict[str, Any]]] = {}

        for event in events:
            # Create partition key: year/month/day/hour/event_type
            partition_key = (
                f"year={event['year']}/"
                f"month={event['month']:02d}/"
                f"day={event['day']:02d}/"
                f"hour={event['hour']:02d}/"
                f"event_type={event['event_type']}"
            )

            if partition_key not in partitions:
                partitions[partition_key] = []

            partitions[partition_key].append(event)

        return partitions

    async def _upload_partition(
        self, partition_key: str, events: List[Dict[str, Any]]
    ) -> None:
        """Upload partition to S3.

        Args:
            partition_key: Partition identifier
            events: Events in this partition

        Raises:
            DataLoadError: If upload fails
        """
        try:
            # Create JSONL content
            jsonl_content = "\n".join(
                json.dumps(event, default=str) for event in events
            )

            # Generate S3 key
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            s3_key = (
                f"{self.s3_prefix}/{self.environment}/"
                f"{partition_key}/"
                f"events_{timestamp}_{len(events)}.jsonl"
            )

            # Upload to S3
            await asyncio.get_event_loop().run_in_executor(
                None, self._upload_to_s3, s3_key, jsonl_content
            )

            logger.debug(
                "Partition uploaded to S3",
                extra={
                    "partition_key": partition_key,
                    "event_count": len(events),
                    "s3_key": s3_key,
                },
            )

        except Exception as e:
            logger.error(
                "Failed to upload partition",
                extra={
                    "partition_key": partition_key,
                    "event_count": len(events),
                    "error": str(e),
                },
            )
            raise DataLoadError(f"Partition upload failed: {e}")

    def _upload_to_s3(self, s3_key: str, content: str) -> None:
        """Upload content to S3 (synchronous).

        Args:
            s3_key: S3 object key
            content: Content to upload

        Raises:
            ClientError: If S3 upload fails
        """
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=content.encode("utf-8"),
                ContentType="application/x-ndjson",
                ServerSideEncryption="AES256",
                Metadata={
                    "environment": self.environment,
                    "etl_version": "1.0",
                    "data_classification": "analytics",
                },
            )

        except ClientError as e:
            logger.error(
                "S3 upload failed",
                extra={"s3_key": s3_key, "bucket": self.s3_bucket, "error": str(e)},
            )
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get ETL pipeline metrics.

        Returns:
            Dictionary containing pipeline metrics
        """
        return {
            "running": self._running,
            "events_processed": self._events_processed,
            "batches_processed": self._batches_processed,
            "errors_count": self._errors_count,
            "buffer_size": len(self._event_buffer),
            "batch_size": self.batch_size,
            "batch_interval": self.batch_interval,
            "environment": self.environment,
            "s3_bucket": self.s3_bucket,
        }


# Global ETL pipeline instance
_etl_pipeline: Optional[ETLPipeline] = None


def get_etl_pipeline() -> ETLPipeline:
    """Get global ETL pipeline instance."""
    if _etl_pipeline is None:
        raise ETLError("ETL pipeline not initialized")
    return _etl_pipeline


def initialize_etl_pipeline(
    environment: str = "development",
    s3_bucket: str = "pms-analytics-data",
    aws_region: str = "us-east-1",
) -> ETLPipeline:
    """Initialize global ETL pipeline instance."""
    global _etl_pipeline
    _etl_pipeline = ETLPipeline(
        environment=environment, s3_bucket=s3_bucket, aws_region=aws_region
    )
    return _etl_pipeline

"""Alert routing service for critical error notifications."""

import logging
import os
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from utils.phi_scrubber import scrub_phi

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertChannel(str, Enum):
    """Alert delivery channels."""

    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    EMAIL = "email"


class Alert(BaseModel):
    """Alert data model."""

    title: str
    message: str
    severity: AlertSeverity
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    service: str = "pms-backend"
    environment: str = "development"
    metadata: Optional[Dict[str, Any]] = None


class AlertService:
    """Service for routing alerts to various channels."""

    def __init__(self):
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.pagerduty_key = os.getenv("PAGERDUTY_INTEGRATION_KEY")
        self.critical_channel = os.getenv(
            "ALERT_CHANNEL_CRITICAL", "#pms-critical-alerts"
        )
        self.warning_channel = os.getenv("ALERT_CHANNEL_WARNING", "#pms-alerts")
        self.environment = os.getenv("SENTRY_ENVIRONMENT", "development")

    async def send_alert(
        self, alert: Alert, channels: Optional[List[AlertChannel]] = None
    ) -> Dict[str, bool]:
        """Send alert to specified channels.

        Args:
            alert: Alert to send
            channels: List of channels to send to (default: auto-select)

        Returns:
            Dict mapping channel names to success status
        """
        if channels is None:
            channels = self._get_default_channels(alert.severity)

        # Scrub PHI from alert data
        scrubbed_alert = self._scrub_alert_data(alert)

        results = {}

        for channel in channels:
            try:
                if channel == AlertChannel.SLACK:
                    success = await self._send_slack_alert(scrubbed_alert)
                    results["slack"] = success
                elif channel == AlertChannel.PAGERDUTY:
                    success = await self._send_pagerduty_alert(scrubbed_alert)
                    results["pagerduty"] = success
                else:
                    logger.warning(f"Unsupported alert channel: {channel}")
                    results[channel] = False

            except Exception as e:
                logger.error(f"Failed to send alert to {channel}: {e}")
                results[channel] = False

        return results

    def _get_default_channels(self, severity: AlertSeverity) -> List[AlertChannel]:
        """Get default channels based on severity."""
        if severity == AlertSeverity.CRITICAL:
            channels = [AlertChannel.SLACK]
            if self.pagerduty_key:
                channels.append(AlertChannel.PAGERDUTY)
            return channels
        elif severity == AlertSeverity.WARNING:
            return [AlertChannel.SLACK]
        else:
            return [AlertChannel.SLACK]

    def _scrub_alert_data(self, alert: Alert) -> Alert:
        """Scrub PHI from alert data."""
        scrubbed_data = alert.dict()

        # Scrub message and title
        scrubbed_data["title"] = scrub_phi(scrubbed_data["title"])
        scrubbed_data["message"] = scrub_phi(scrubbed_data["message"])

        # Anonymize user ID
        if scrubbed_data.get("user_id"):
            user_hash = hash(scrubbed_data["user_id"]) % 10000
            scrubbed_data["user_id"] = f"user_{user_hash:04d}"

        # Scrub metadata
        if scrubbed_data.get("metadata"):
            scrubbed_data["metadata"] = scrub_phi(scrubbed_data["metadata"])

        return Alert(**scrubbed_data)

    async def _send_slack_alert(self, alert: Alert) -> bool:
        """Send alert to Slack."""
        if not self.slack_webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False

        # Determine channel based on severity
        channel = (
            self.critical_channel
            if alert.severity == AlertSeverity.CRITICAL
            else self.warning_channel
        )

        # Create Slack message
        color = {
            AlertSeverity.CRITICAL: "danger",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.INFO: "good",
        }.get(alert.severity, "warning")

        payload = {
            "channel": channel,
            "username": "PMS Alert Bot",
            "icon_emoji": ":warning:",
            "attachments": [
                {
                    "color": color,
                    "title": f"[{alert.severity.upper()}] {alert.title}",
                    "text": alert.message,
                    "fields": [
                        {"title": "Service", "value": alert.service, "short": True},
                        {
                            "title": "Environment",
                            "value": alert.environment,
                            "short": True,
                        },
                    ],
                    "footer": "PMS Error Tracking",
                    "ts": int(alert.metadata.get("timestamp", 0))
                    if alert.metadata
                    else 0,
                }
            ],
        }

        # Add correlation ID if available
        if alert.correlation_id:
            payload["attachments"][0]["fields"].append(
                {
                    "title": "Correlation ID",
                    "value": alert.correlation_id,
                    "short": True,
                }
            )

        # Add user ID if available (anonymized)
        if alert.user_id:
            payload["attachments"][0]["fields"].append(
                {"title": "User", "value": alert.user_id, "short": True}
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.slack_webhook_url, json=payload, timeout=10.0
                )

                if response.status_code == 200:
                    logger.info(f"Slack alert sent successfully: {alert.title}")
                    return True
                else:
                    logger.error(
                        f"Slack alert failed: {response.status_code} - "
                        f"{response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

    async def _send_pagerduty_alert(self, alert: Alert) -> bool:
        """Send alert to PagerDuty."""
        if not self.pagerduty_key:
            logger.warning("PagerDuty integration key not configured")
            return False

        # Only send critical alerts to PagerDuty
        if alert.severity != AlertSeverity.CRITICAL:
            logger.info("Skipping non-critical alert for PagerDuty")
            return True

        payload = {
            "routing_key": self.pagerduty_key,
            "event_action": "trigger",
            "dedup_key": f"pms-{alert.correlation_id or 'unknown'}",
            "payload": {
                "summary": f"[{alert.service}] {alert.title}",
                "source": alert.service,
                "severity": "critical",
                "component": "pms-backend",
                "group": "pms",
                "class": "error",
                "custom_details": {
                    "message": alert.message,
                    "environment": alert.environment,
                    "correlation_id": alert.correlation_id,
                    "user_id": alert.user_id,
                    "metadata": alert.metadata,
                },
            },
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                    timeout=10.0,
                )

                if response.status_code == 202:
                    logger.info(f"PagerDuty alert sent: {alert.title}")
                    return True
                else:
                    logger.error(
                        f"PagerDuty alert failed: {response.status_code} - "
                        f"{response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Failed to send PagerDuty alert: {e}")
            return False

    async def send_error_alert(
        self,
        exception: Exception,
        severity: AlertSeverity = AlertSeverity.CRITICAL,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, bool]:
        """Send an alert for an exception.

        Args:
            exception: The exception that occurred
            severity: Alert severity level
            user_id: User ID (will be anonymized)
            correlation_id: Request correlation ID
            extra_context: Additional context

        Returns:
            Dict mapping channel names to success status
        """
        alert = Alert(
            title=f"Exception: {type(exception).__name__}",
            message=str(exception),
            severity=severity,
            correlation_id=correlation_id,
            user_id=user_id,
            environment=self.environment,
            metadata=extra_context or {},
        )

        return await self.send_alert(alert)

    async def send_test_alert(self) -> Dict[str, bool]:
        """Send a test alert for validation.

        Returns:
            Dict mapping channel names to success status
        """
        alert = Alert(
            title="Test Alert - Error Tracking Validation",
            message="This is a test alert to validate error tracking "
            "and alerting system. PHI test: Patient John Doe "
            "SSN 123-45-6789",
            severity=AlertSeverity.WARNING,
            correlation_id="test-correlation-id",
            user_id="test-user-123",
            environment=self.environment,
            metadata={
                "test_type": "validation",
                "timestamp": 1234567890,
                "test_data": "Patient: Jane Smith, DOB: 1990-01-01",
            },
        )

        return await self.send_alert(alert)


# Global alert service instance
alert_service = AlertService()


def get_alert_service() -> AlertService:
    """Get the global alert service instance."""
    return alert_service

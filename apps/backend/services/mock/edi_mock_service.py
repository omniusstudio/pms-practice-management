"""Mock EDI service for testing EDI 837/835 transactions."""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Any, Dict
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


class EDIMockService:
    """Mock EDI service for claims processing and remittance."""

    def __init__(self):
        """Initialize the mock EDI service."""
        self.processed_claims: Dict[str, Dict] = {}
        self.remittance_data: Dict[str, Dict] = {}

    async def submit_837_claim(
        self, claim_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate EDI 837 claim submission.

        Args:
            claim_data: Claim information including patient, provider, services

        Returns:
            Dictionary with transaction ID, status, and acknowledgment
        """
        # Simulate processing delay
        await asyncio.sleep(random.uniform(0.1, 0.5))

        transaction_id = f"EDI837_{uuid4().hex[:8].upper()}"

        # Simulate various response scenarios
        scenarios = [
            {"status": "accepted", "ack_code": "AA", "weight": 0.85},
            {"status": "rejected", "ack_code": "AE", "weight": 0.10},
            {"status": "pending", "ack_code": "AR", "weight": 0.05},
        ]

        weights = [float(s["weight"]) for s in scenarios]
        scenario = random.choices(scenarios, weights=weights)[0]

        response = {
            "transaction_id": transaction_id,
            "status": scenario["status"],
            "ack_code": scenario["ack_code"],
            "timestamp": datetime.utcnow().isoformat(),
            "claim_id": claim_data.get("claim_id", f"CLM_{uuid4().hex[:6]}"),
            "patient_id": claim_data.get("patient_id"),
            "provider_id": claim_data.get("provider_id"),
            "claim_amount": claim_data.get("claim_amount", 0.0),
        }

        # Add error details for rejected claims
        if scenario["status"] == "rejected":
            response["error_codes"] = ["INV001", "DUP002"]
            response["error_description"] = (
                "Invalid patient ID or duplicate claim"
            )

        # Store for later remittance processing (always store for testing)
        # In production, only accepted claims would be stored
        self.processed_claims[transaction_id] = response

        logger.info(
            "EDI 837 claim processed",
            transaction_id=transaction_id,
            status=scenario["status"],
            claim_id=response["claim_id"],
        )

        return response

    async def process_835_remittance(
        self, remittance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate EDI 835 payment remittance processing.

        Args:
            remittance_data: Payment remittance information

        Returns:
            Dictionary with remittance details and payment information
        """
        # Simulate processing delay
        await asyncio.sleep(random.uniform(0.2, 0.8))

        remittance_id = f"EDI835_{uuid4().hex[:8].upper()}"

        # Generate realistic payment scenarios
        payment_scenarios = [
            {"status": "paid_full", "adjustment_reason": None, "weight": 0.70},
            {
                "status": "paid_partial",
                "adjustment_reason": "CO-45",
                "weight": 0.20,
            },
            {"status": "denied", "adjustment_reason": "CO-97", "weight": 0.10},
        ]

        weights = [float(s["weight"]) for s in payment_scenarios]
        scenario = random.choices(payment_scenarios, weights=weights)[0]

        original_amount = remittance_data.get("claim_amount", 100.0)

        if scenario["status"] == "paid_full":
            paid_amount = original_amount
        elif scenario["status"] == "paid_partial":
            paid_amount = round(
                original_amount * random.uniform(0.6, 0.9), 2
            )
        else:
            paid_amount = 0.0

        response = {
            "remittance_id": remittance_id,
            "status": scenario["status"],
            "timestamp": datetime.utcnow().isoformat(),
            "payer_id": remittance_data.get("payer_id", "PAYER001"),
            "provider_id": remittance_data.get("provider_id"),
            "claim_id": remittance_data.get("claim_id"),
            "original_amount": original_amount,
            "paid_amount": paid_amount,
            "adjustment_amount": original_amount - paid_amount,
            "check_number": f"CHK{random.randint(100000, 999999)}",
            "payment_date": (
                datetime.utcnow() + timedelta(days=1)
            ).isoformat(),
        }

        if scenario["adjustment_reason"]:
            response["adjustment_reason"] = scenario["adjustment_reason"]
            response["adjustment_description"] = (
                self._get_adjustment_description(
                    scenario["adjustment_reason"]
                )
            )

        # Store remittance data
        self.remittance_data[remittance_id] = response

        logger.info(
            "EDI 835 remittance processed",
            remittance_id=remittance_id,
            status=scenario["status"],
            paid_amount=paid_amount,
        )

        return response

    async def get_claim_status(self, transaction_id: str) -> Dict[str, Any]:
        """Get status of a previously submitted claim.

        Args:
            transaction_id: EDI transaction ID

        Returns:
            Dictionary with current claim status
        """
        if transaction_id in self.processed_claims:
            claim = self.processed_claims[transaction_id].copy()

            # Simulate status progression for pending claims
            if claim["status"] == "pending":
                # 50% chance to move to accepted after some time
                if random.random() < 0.5:
                    claim["status"] = "accepted"
                    claim["ack_code"] = "AA"
                    claim["updated_at"] = datetime.utcnow().isoformat()

            return claim
        else:
            return {
                "error": "Transaction not found",
                "transaction_id": transaction_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def get_remittance_details(
        self, remittance_id: str
    ) -> Dict[str, Any]:
        """Get details of a payment remittance.

        Args:
            remittance_id: EDI remittance ID

        Returns:
            Dictionary with remittance details
        """
        if remittance_id in self.remittance_data:
            return self.remittance_data[remittance_id]
        else:
            return {
                "error": "Remittance not found",
                "remittance_id": remittance_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _get_adjustment_description(self, reason_code: str) -> str:
        """Get human-readable description for adjustment reason codes."""
        descriptions = {
            "CO-45": "Charge exceeds fee schedule/maximum allowable",
            "CO-97": "Payment adjusted because the benefit is not covered",
            "CO-16": "Claim/service lacks information for adjudication",
            "CO-18": "Duplicate claim/service",
            "CO-50": "Non-covered services",
        }
        return descriptions.get(reason_code, "Unknown adjustment reason")

    async def get_service_health(self) -> Dict[str, Any]:
        """Get mock EDI service health status."""
        return {
            "service": "edi_mock",
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "stats": {
                "processed_claims": len(self.processed_claims),
                "processed_remittances": len(self.remittance_data),
            },
            "uptime_seconds": random.randint(3600, 86400),
        }

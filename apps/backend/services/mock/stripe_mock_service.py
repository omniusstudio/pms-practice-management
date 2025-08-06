import asyncio
import random
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, cast
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


class StripeMockService:
    """Mock Stripe service for payment processing simulation.

    Simulates Stripe payment intents, subscriptions, webhooks,
    and customer management for development and testing.
    """

    def __init__(self):
        self.payment_intents: Dict[str, Dict] = {}
        self.customers: Dict[str, Dict] = {}
        self.subscriptions: Dict[str, Dict] = {}
        self.webhook_events: Dict[str, Dict] = {}

    async def create_payment_intent(
        self,
        amount: int,
        currency: str = "usd",
        customer_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a mock Stripe payment intent.

        Args:
            amount: Amount in cents
            currency: Currency code (default: usd)
            customer_id: Optional customer ID
            metadata: Optional metadata dictionary

        Returns:
            Payment intent object with client secret
        """
        await asyncio.sleep(random.uniform(0.1, 0.3))  # Simulate API delay

        payment_intent_id = f"pi_{uuid4().hex[:24]}"
        client_secret = f"{payment_intent_id}_secret_{uuid4().hex[:16]}"

        # Simulate various payment scenarios
        scenarios = [
            {"status": "requires_payment_method", "weight": 0.05},
            {"status": "requires_confirmation", "weight": 0.10},
            {"status": "processing", "weight": 0.05},
            {"status": "succeeded", "weight": 0.75},
            {"status": "requires_action", "weight": 0.03},
            {"status": "canceled", "weight": 0.02},
        ]

        weights = [cast(float, s["weight"]) for s in scenarios]
        scenario = random.choices(scenarios, weights=weights)[0]

        payment_intent = {
            "id": payment_intent_id,
            "object": "payment_intent",
            "amount": amount,
            "currency": currency,
            "status": scenario["status"],
            "client_secret": client_secret,
            "created": int(datetime.utcnow().timestamp()),
            "customer": customer_id,
            "metadata": metadata or {},
            "payment_method_types": ["card"],
            "confirmation_method": "automatic",
            "capture_method": "automatic",
        }

        # Add scenario-specific fields
        if scenario["status"] == "succeeded":
            payment_intent.update(
                {
                    "charges": {
                        "object": "list",
                        "data": [
                            {
                                "id": f"ch_{uuid4().hex[:24]}",
                                "amount": amount,
                                "currency": currency,
                                "status": "succeeded",
                                "paid": True,
                                "receipt_url": (
                                    f"https://pay.stripe.com/receipts/"
                                    f"{uuid4().hex[:32]}"
                                ),
                            }
                        ],
                    }
                }
            )
        elif scenario["status"] == "requires_action":
            payment_intent["next_action"] = {
                "type": "use_stripe_sdk",
                "use_stripe_sdk": {
                    "type": "three_d_secure_redirect",
                    "stripe_js": "https://js.stripe.com/v3/",
                },
            }

        self.payment_intents[payment_intent_id] = payment_intent

        await logger.ainfo(
            "Mock payment intent created",
            payment_intent_id=payment_intent_id,
            amount=amount,
            status=scenario["status"],
        )

        return payment_intent

    async def retrieve_payment_intent(
        self, payment_intent_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a payment intent by ID.

        Args:
            payment_intent_id: Payment intent ID

        Returns:
            Payment intent object or None if not found
        """
        await asyncio.sleep(random.uniform(0.05, 0.15))
        return self.payment_intents.get(payment_intent_id)

    async def confirm_payment_intent(
        self, payment_intent_id: str, payment_method: Optional[str] = None
    ) -> Dict[str, Any]:
        """Confirm a payment intent.

        Args:
            payment_intent_id: Payment intent ID
            payment_method: Payment method ID

        Returns:
            Updated payment intent object
        """
        await asyncio.sleep(random.uniform(0.2, 0.5))

        payment_intent = self.payment_intents.get(payment_intent_id)
        if not payment_intent:
            raise ValueError(f"Payment intent {payment_intent_id} not found")

        # Simulate confirmation outcomes
        outcomes = [
            {"status": "succeeded", "weight": 0.85},
            {"status": "requires_action", "weight": 0.10},
            {"status": "payment_failed", "weight": 0.05},
        ]

        weights = [cast(float, o["weight"]) for o in outcomes]
        outcome = random.choices(outcomes, weights=weights)[0]

        payment_intent["status"] = outcome["status"]

        if outcome["status"] == "succeeded":
            payment_intent["charges"] = {
                "object": "list",
                "data": [
                    {
                        "id": f"ch_{uuid4().hex[:24]}",
                        "amount": payment_intent["amount"],
                        "currency": payment_intent["currency"],
                        "status": "succeeded",
                        "paid": True,
                        "payment_method": payment_method or "pm_card_visa",
                    }
                ],
            }
        elif outcome["status"] == "payment_failed":
            payment_intent["last_payment_error"] = {
                "type": "card_error",
                "code": "card_declined",
                "message": "Your card was declined.",
                "decline_code": "generic_decline",
            }

        await logger.ainfo(
            "Mock payment intent confirmed",
            payment_intent_id=payment_intent_id,
            status=outcome["status"],
        )

        return payment_intent

    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a mock Stripe customer.

        Args:
            email: Customer email
            name: Customer name
            metadata: Optional metadata

        Returns:
            Customer object
        """
        await asyncio.sleep(random.uniform(0.1, 0.2))

        customer_id = f"cus_{uuid4().hex[:24]}"

        customer = {
            "id": customer_id,
            "object": "customer",
            "email": email,
            "name": name,
            "created": int(datetime.utcnow().timestamp()),
            "metadata": metadata or {},
            "default_source": None,
            "subscriptions": {"object": "list", "data": []},
        }

        self.customers[customer_id] = customer

        await logger.ainfo(
            "Mock customer created", customer_id=customer_id, email=email
        )

        return customer

    async def create_subscription(
        self, customer_id: str, price_id: str, metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a mock subscription.

        Args:
            customer_id: Customer ID
            price_id: Price ID
            metadata: Optional metadata

        Returns:
            Subscription object
        """
        await asyncio.sleep(random.uniform(0.2, 0.4))

        if customer_id not in self.customers:
            raise ValueError(f"Customer {customer_id} not found")

        subscription_id = f"sub_{uuid4().hex[:24]}"

        # Mock price data
        price_data = {
            "price_monthly_basic": {"amount": 2999, "interval": "month"},
            "price_monthly_pro": {"amount": 9999, "interval": "month"},
            "price_yearly_basic": {"amount": 29999, "interval": "year"},
            "price_yearly_pro": {"amount": 99999, "interval": "year"},
        }

        price_info = price_data.get(price_id, {"amount": 2999, "interval": "month"})

        subscription = {
            "id": subscription_id,
            "object": "subscription",
            "customer": customer_id,
            "status": "active",
            "created": int(datetime.utcnow().timestamp()),
            "current_period_start": int(datetime.utcnow().timestamp()),
            "current_period_end": int(
                (datetime.utcnow() + timedelta(days=30)).timestamp()
            ),
            "items": {
                "object": "list",
                "data": [
                    {
                        "id": f"si_{uuid4().hex[:24]}",
                        "price": {
                            "id": price_id,
                            "unit_amount": price_info["amount"],
                            "currency": "usd",
                            "recurring": {"interval": price_info["interval"]},
                        },
                    }
                ],
            },
            "metadata": metadata or {},
        }

        self.subscriptions[subscription_id] = subscription

        await logger.ainfo(
            "Mock subscription created",
            subscription_id=subscription_id,
            customer_id=customer_id,
            price_id=price_id,
        )

        return subscription

    async def process_webhook_event(
        self, event_type: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a mock webhook event.

        Args:
            event_type: Stripe event type
            data: Event data

        Returns:
            Webhook event object
        """
        await asyncio.sleep(random.uniform(0.05, 0.1))

        event_id = f"evt_{uuid4().hex[:24]}"

        webhook_event = {
            "id": event_id,
            "object": "event",
            "type": event_type,
            "created": int(datetime.utcnow().timestamp()),
            "data": data,
            "livemode": False,
            "pending_webhooks": 1,
            "request": {"id": f"req_{uuid4().hex[:24]}", "idempotency_key": None},
        }

        self.webhook_events[event_id] = webhook_event

        await logger.ainfo(
            "Mock webhook event processed", event_id=event_id, event_type=event_type
        )

        return webhook_event

    async def get_service_health(self) -> Dict[str, Any]:
        """Get mock service health status.

        Returns:
            Service health information
        """
        return {
            "service": "stripe_mock",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "stats": {
                "payment_intents": len(self.payment_intents),
                "customers": len(self.customers),
                "subscriptions": len(self.subscriptions),
                "webhook_events": len(self.webhook_events),
            },
            "uptime_seconds": random.randint(3600, 86400),
        }

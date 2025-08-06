"""Test fixtures for mock services.

Provides standardized test data and fixtures for EDI, Stripe, and Video
mock services to support contract testing and development.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List
from uuid import uuid4

import pytest


# EDI Test Fixtures
@pytest.fixture
def sample_claim_data() -> Dict[str, Any]:
    """Sample EDI claim data for testing."""
    return {
        "patient_id": "PAT123456",
        "provider_id": "PRV789012",
        "services": [
            {
                "procedure_code": "90834",
                "description": "Psychotherapy, 45 minutes",
                "units": 1,
                "charge_amount": 150.00,
                "service_date": "2024-01-15",
            },
            {
                "procedure_code": "90837",
                "description": "Psychotherapy, 60 minutes",
                "units": 1,
                "charge_amount": 200.00,
                "service_date": "2024-01-22",
            },
        ],
        "claim_amount": 350.00,
        "diagnosis_codes": ["F32.9", "F41.1"],
        "metadata": {"session_type": "individual", "treatment_plan_id": "TP001"},
    }


@pytest.fixture
def expected_edi_response() -> Dict[str, Any]:
    """Expected EDI 837 submission response structure."""
    return {
        "transaction_id": str,
        "status": str,  # accepted, rejected, pending
        "ack_code": str,  # AA, AE, AR
        "timestamp": str,
        "claim_amount": float,
        "error_codes": list,  # Optional, present if rejected
        "error_description": str,  # Optional, present if rejected
    }


@pytest.fixture
def expected_remittance_response() -> Dict[str, Any]:
    """Expected EDI 835 remittance response structure."""
    return {
        "remittance_id": str,
        "transaction_id": str,
        "status": str,  # paid_full, paid_partial, denied
        "original_amount": float,
        "paid_amount": float,
        "adjustment_amount": float,
        "adjustment_reason": str,  # Optional
        "adjustment_description": str,  # Optional
        "check_number": str,
        "payment_date": str,
        "timestamp": str,
    }


# Stripe Test Fixtures
@pytest.fixture
def sample_payment_intent_request() -> Dict[str, Any]:
    """Sample Stripe payment intent request data."""
    return {
        "amount": 15000,  # $150.00 in cents
        "currency": "usd",
        "customer_id": "cus_test123",
        "metadata": {
            "patient_id": "PAT123456",
            "appointment_id": "APT789012",
            "service_type": "therapy_session",
        },
    }


@pytest.fixture
def expected_payment_intent_response() -> Dict[str, Any]:
    """Expected Stripe payment intent response structure."""
    return {
        "id": str,
        "object": "payment_intent",
        "amount": int,
        "currency": str,
        "status": str,  # requires_payment_method, succeeded, etc.
        "client_secret": str,
        "created": int,
        "customer": str,
        "metadata": dict,
        "payment_method_types": list,
        "confirmation_method": str,
        "capture_method": str,
    }


@pytest.fixture
def sample_customer_request() -> Dict[str, Any]:
    """Sample Stripe customer creation request."""
    return {
        "email": "patient@example.com",
        "name": "John Doe",
        "metadata": {"patient_id": "PAT123456", "registration_date": "2024-01-01"},
    }


@pytest.fixture
def expected_customer_response() -> Dict[str, Any]:
    """Expected Stripe customer response structure."""
    return {
        "id": str,
        "object": "customer",
        "email": str,
        "name": str,
        "created": int,
        "metadata": dict,
        "default_source": None,
        "subscriptions": dict,
    }


@pytest.fixture
def sample_subscription_request() -> Dict[str, Any]:
    """Sample Stripe subscription creation request."""
    return {
        "customer_id": "cus_test123",
        "price_id": "price_monthly_basic",
        "metadata": {"plan_type": "basic", "billing_cycle": "monthly"},
    }


@pytest.fixture
def expected_subscription_response() -> Dict[str, Any]:
    """Expected Stripe subscription response structure."""
    return {
        "id": str,
        "object": "subscription",
        "customer": str,
        "status": str,
        "created": int,
        "current_period_start": int,
        "current_period_end": int,
        "items": dict,
        "metadata": dict,
    }


# Video Service Test Fixtures
@pytest.fixture
def sample_video_session_request() -> Dict[str, Any]:
    """Sample video session creation request."""
    return {
        "session_name": "Therapy Session - John Doe",
        "max_participants": 2,
        "recording_enabled": True,
        "metadata": {
            "appointment_id": "APT789012",
            "patient_id": "PAT123456",
            "provider_id": "PRV789012",
            "session_type": "individual_therapy",
        },
    }


@pytest.fixture
def expected_video_session_response() -> Dict[str, Any]:
    """Expected video session response structure."""
    return {
        "id": str,
        "name": str,
        "status": str,  # created, active, waiting, ended
        "created_at": str,
        "max_participants": int,
        "current_participants": int,
        "recording_enabled": bool,
        "recording_status": str,  # not_started, recording, completed, disabled
        "metadata": dict,
        "join_urls": dict,
        "room_token": str,
        "expires_at": str,
    }


@pytest.fixture
def sample_join_session_request() -> Dict[str, Any]:
    """Sample video session join request."""
    return {
        "participant_name": "Dr. Smith",
        "participant_role": "provider",
        "participant_metadata": {
            "provider_id": "PRV789012",
            "license_number": "LIC123456",
        },
    }


@pytest.fixture
def expected_join_session_response() -> Dict[str, Any]:
    """Expected video session join response structure."""
    return {
        "participant": {
            "id": str,
            "name": str,
            "role": str,
            "status": str,  # connected, connection_failed, audio_only
            "joined_at": str,
            "audio_enabled": bool,
            "video_enabled": bool,
            "metadata": dict,
        },
        "session_status": str,
        "recording_status": str,
    }


@pytest.fixture
def expected_recording_response() -> Dict[str, Any]:
    """Expected video recording response structure."""
    return {
        "id": str,
        "session_id": str,
        "status": str,  # recording, processing, completed
        "started_at": str,
        "stopped_at": str,  # Optional
        "duration_seconds": int,
        "file_size_mb": int,
        "download_url": str,  # Optional
        "expires_at": str,  # Optional
    }


# Contract Test Scenarios
@pytest.fixture
def edi_contract_scenarios() -> List[Dict[str, Any]]:
    """Contract test scenarios for EDI service."""
    return [
        {
            "name": "successful_claim_submission",
            "request": {
                "patient_id": "PAT123456",
                "provider_id": "PRV789012",
                "services": [
                    {
                        "procedure_code": "90834",
                        "description": "Psychotherapy, 45 minutes",
                        "units": 1,
                        "charge_amount": 150.00,
                        "service_date": "2024-01-15",
                    }
                ],
                "claim_amount": 150.00,
                "diagnosis_codes": ["F32.9"],
            },
            "expected_status_codes": [200],
            "expected_response_fields": [
                "transaction_id",
                "status",
                "ack_code",
                "timestamp",
            ],
        },
        {
            "name": "claim_with_invalid_data",
            "request": {
                "patient_id": "",  # Invalid empty patient ID
                "provider_id": "PRV789012",
                "services": [],  # Empty services
                "claim_amount": 0.00,
                "diagnosis_codes": [],
            },
            "expected_status_codes": [400, 422],
            "expected_response_fields": ["error_codes", "error_description"],
        },
    ]


@pytest.fixture
def stripe_contract_scenarios() -> List[Dict[str, Any]]:
    """Contract test scenarios for Stripe service."""
    return [
        {
            "name": "successful_payment_intent_creation",
            "request": {
                "amount": 15000,
                "currency": "usd",
                "metadata": {"patient_id": "PAT123456"},
            },
            "expected_status_codes": [200],
            "expected_response_fields": ["id", "client_secret", "status", "amount"],
        },
        {
            "name": "invalid_amount_payment_intent",
            "request": {"amount": -100, "currency": "usd"},  # Invalid negative amount
            "expected_status_codes": [400, 422],
            "expected_response_fields": ["detail"],
        },
    ]


@pytest.fixture
def video_contract_scenarios() -> List[Dict[str, Any]]:
    """Contract test scenarios for Video service."""
    return [
        {
            "name": "successful_session_creation",
            "request": {
                "session_name": "Test Session",
                "max_participants": 2,
                "recording_enabled": True,
            },
            "expected_status_codes": [200],
            "expected_response_fields": [
                "id",
                "name",
                "status",
                "join_urls",
                "room_token",
            ],
        },
        {
            "name": "invalid_session_parameters",
            "request": {
                "session_name": "",  # Empty session name
                "max_participants": 0,  # Invalid participant count
                "recording_enabled": True,
            },
            "expected_status_codes": [400, 422],
            "expected_response_fields": ["detail"],
        },
    ]


# Health Check Fixtures
@pytest.fixture
def expected_health_response() -> Dict[str, Any]:
    """Expected health check response structure."""
    return {
        "service": str,
        "status": str,  # healthy, unhealthy
        "timestamp": str,
        "stats": dict,
        "uptime_seconds": int,
    }


# Mock Service State Fixtures
@pytest.fixture
def mock_service_state() -> Dict[str, Any]:
    """Initial state for mock services during testing."""
    return {
        "edi": {"processed_claims": {}, "remittance_data": {}},
        "stripe": {
            "payment_intents": {},
            "customers": {},
            "subscriptions": {},
            "webhook_events": {},
        },
        "video": {"sessions": {}, "recordings": {}, "participants": {}},
    }


# Utility Functions for Test Data Generation
def generate_test_transaction_id() -> str:
    """Generate a test transaction ID."""
    return f"TXN_{uuid4().hex[:16].upper()}"


def generate_test_patient_id() -> str:
    """Generate a test patient ID."""
    return f"PAT{uuid4().hex[:6].upper()}"


def generate_test_provider_id() -> str:
    """Generate a test provider ID."""
    return f"PRV{uuid4().hex[:6].upper()}"


def generate_test_session_id() -> str:
    """Generate a test video session ID."""
    return f"session_{uuid4().hex[:16]}"


def generate_test_payment_intent_id() -> str:
    """Generate a test Stripe payment intent ID."""
    return f"pi_{uuid4().hex[:24]}"


def generate_test_customer_id() -> str:
    """Generate a test Stripe customer ID."""
    return f"cus_{uuid4().hex[:24]}"


# Date/Time Utilities
def get_test_timestamp() -> str:
    """Get a test timestamp in ISO format."""
    return datetime.utcnow().isoformat()


def get_future_timestamp(days: int = 30) -> str:
    """Get a future timestamp for expiration dates."""
    return (datetime.utcnow() + timedelta(days=days)).isoformat()


def get_past_timestamp(days: int = 1) -> str:
    """Get a past timestamp for historical data."""
    return (datetime.utcnow() - timedelta(days=days)).isoformat()

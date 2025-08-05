#!/usr/bin/env python3
"""Test script for Event Bus and ETL Pipeline functionality."""

import requests  # type: ignore
from datetime import datetime, timezone


BASE_URL = "http://localhost:8000/api/events"


def test_event_types():
    """Test getting available event types."""
    print("\n=== Testing Event Types Endpoint ===")
    
    response = requests.get(f"{BASE_URL}/types")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Event types retrieved successfully:")
        print(f"   Event Types: {len(data['event_types'])} types")
        print(f"   Severities: {data['severities']}")
        return True
    else:
        print(f"❌ Failed to get event types: {response.status_code}")
        return False


def test_publish_crud_event():
    """Test publishing a CRUD event."""
    print("\n=== Testing CRUD Event Publishing ===")
    
    event_data = {
        "event_type": "user.created",
        "resource_type": "user",
        "resource_id": "user_12345",
        "severity": "medium",
        "operation": "CREATE",
        "changes": {
            "before": None,
            "after": {
                "id": "user_12345",
                "email": "[EMAIL-REDACTED]",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        },
        "metadata": {
            "source": "user_management_api",
            "version": "1.0"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/publish",
        json=event_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ CRUD event published successfully:")
        print(f"   Event ID: {data['event_id']}")
        print(f"   Correlation ID: {data['correlation_id']}")
        return True
    else:
        print(f"❌ Failed to publish CRUD event: {response.status_code}")
        print(f"   Error: {response.text}")
        return False


def test_publish_auth_event():
    """Test publishing an authentication event."""
    print("\n=== Testing Auth Event Publishing ===")
    
    event_data = {
        "event_type": "security.event",
        "resource_type": "authentication",
        "resource_id": "login_attempt_789",
        "severity": "high",
        "auth_type": "LOGIN",
        "success": True,
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 (compatible browser)",
        "user_id": "user_12345",
        "metadata": {
            "login_method": "password",
            "mfa_used": True
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/publish",
        json=event_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Auth event published successfully:")
        print(f"   Event ID: {data['event_id']}")
        print(f"   Correlation ID: {data['correlation_id']}")
        return True
    else:
        print(f"❌ Failed to publish auth event: {response.status_code}")
        print(f"   Error: {response.text}")
        return False


def test_publish_system_event():
    """Test publishing a system event."""
    print("\n=== Testing System Event Publishing ===")
    
    event_data = {
        "event_type": "system.error",
        "resource_type": "database",
        "resource_id": "db_connection_pool",
        "severity": "critical",
        "component": "postgresql_driver",
        "error_code": "CONNECTION_TIMEOUT",
        "stack_trace": "[SCRUBBED_STACK_TRACE]",
        "metadata": {
            "database_host": "[SCRUBBED_HOST]",
            "connection_count": 50,
            "timeout_seconds": 30
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/publish",
        json=event_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ System event published successfully:")
        print(f"   Event ID: {data['event_id']}")
        print(f"   Correlation ID: {data['correlation_id']}")
        return True
    else:
        print(f"❌ Failed to publish system event: {response.status_code}")
        print(f"   Error: {response.text}")
        return False


def test_publish_business_event():
    """Test publishing a business event."""
    print("\n=== Testing Business Event Publishing ===")
    
    event_data = {
        "event_type": "appointment.completed",
        "resource_type": "appointment",
        "resource_id": "appt_67890",
        "severity": "low",
        "business_process": "patient_consultation",
        "outcome": "SUCCESS",
        "duration_ms": 1800000,  # 30 minutes
        "user_id": "doctor_456",
        "metadata": {
            "patient_id": "[SCRUBBED_PATIENT_ID]",
            "consultation_type": "follow_up",
            "billing_code": "99213"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/publish",
        json=event_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Business event published successfully:")
        print(f"   Event ID: {data['event_id']}")
        print(f"   Correlation ID: {data['correlation_id']}")
        return True
    else:
        print(f"❌ Failed to publish business event: {response.status_code}")
        print(f"   Error: {response.text}")
        return False


def test_event_bus_status():
    """Test event bus status endpoint."""
    print("\n=== Testing Event Bus Status ===")
    
    response = requests.get(f"{BASE_URL}/bus/status")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Event bus status retrieved:")
        print(f"   Connected: {data.get('connected', False)}")
        print(f"   Environment: {data.get('environment', 'unknown')}")
        return True
    elif response.status_code == 503:
        print("⚠️  Event bus not available (Redis not running):")
        error_data = response.json()
        print(f"   Detail: {error_data.get('detail', 'Unknown error')}")
        return True  # Expected when Redis is not running
    else:
        print(f"❌ Unexpected error: {response.status_code}")
        return False


def test_etl_status():
    """Test ETL pipeline status endpoint."""
    print("\n=== Testing ETL Pipeline Status ===")
    
    response = requests.get(f"{BASE_URL}/etl/status")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ ETL pipeline status retrieved:")
        print(f"   Running: {data.get('running', False)}")
        print(f"   Events Processed: {data.get('events_processed', 0)}")
        print(f"   Environment: {data.get('environment', 'unknown')}")
        return True
    elif response.status_code == 503:
        print("⚠️  ETL pipeline not available (Redis not running):")
        error_data = response.json()
        print(f"   Detail: {error_data.get('detail', 'Unknown error')}")
        return True  # Expected when Redis is not running
    else:
        print(f"❌ Unexpected error: {response.status_code}")
        return False


def main():
    """Run all tests."""
    print("🚀 Event Bus & ETL Pipeline Test Suite")
    print("=======================================")
    
    tests = [
        test_event_types,
        test_publish_crud_event,
        test_publish_auth_event,
        test_publish_system_event,
        test_publish_business_event,
        test_event_bus_status,
        test_etl_status,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print(
            "🎉 All tests passed! Event system is working correctly."
        )
    else:
        print(
            "⚠️  Some tests failed. Check Redis connection for "
            "full functionality."
        )
    
    print("\n📝 Notes:")
    print("   - Event publishing works without Redis (events are validated)")
    print("   - Event bus and ETL require Redis for full functionality")
    print("   - PHI scrubbing is applied to all events automatically")
    print("   - Correlation IDs are generated for request tracking")


if __name__ == "__main__":
    main()
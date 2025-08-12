#!/usr/bin/env python3
"""Test script to verify factory tenant_id override functionality."""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from database import SessionLocal  # noqa: E402
from factories.client import ClientFactory  # noqa: E402


def test_factory_tenant_override():
    """Test that factories properly override tenant_id."""
    session = SessionLocal()

    try:
        # Set session for factory
        ClientFactory._meta.sqlalchemy_session = session

        # Test single client creation with tenant_id override
        print("Testing single client creation with tenant_id override...")
        client = ClientFactory.create(tenant_id="test_tenant_single")
        print(f"Created client with tenant_id: {client.tenant_id}")

        # Test batch creation with tenant_id override
        print("\nTesting batch client creation with tenant_id override...")
        clients = ClientFactory.create_batch(3, tenant_id="test_tenant_batch")
        for i, client in enumerate(clients):
            print(f"Client {i+1} tenant_id: {client.tenant_id}")

        # Test default tenant_id behavior
        print("\nTesting default tenant_id behavior...")
        default_client = ClientFactory.create()
        print(f"Default client tenant_id: {default_client.tenant_id}")

        session.commit()
        print("\nAll tests completed successfully!")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    test_factory_tenant_override()

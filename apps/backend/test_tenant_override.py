#!/usr/bin/env python3
"""Test script to verify tenant_id parameter override works."""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from database import SessionLocal  # noqa: E402
from factories import ClientFactory  # noqa: E402


def test_tenant_override():
    """Test that tenant_id can be overridden in create_batch."""
    session = SessionLocal()
    try:
        ClientFactory._meta.sqlalchemy_session = session

        # Test single client with tenant_id override
        client = ClientFactory(tenant_id="test_tenant_single")
        print(f"Single client tenant_id: {client.tenant_id}")

        # Test create_batch with tenant_id override
        clients = ClientFactory.create_batch(2, tenant_id="test_tenant_batch")
        print(f"Batch client 1 tenant_id: {clients[0].tenant_id}")
        print(f"Batch client 2 tenant_id: {clients[1].tenant_id}")

        # Test default tenant_id
        default_client = ClientFactory()
        print(f"Default client tenant_id: {default_client.tenant_id}")

        session.rollback()  # Don't commit test data

    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    test_tenant_override()

#!/usr/bin/env python3
"""Pytest configuration and shared fixtures for database tests."""

import asyncio
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.base import Base  # noqa: E402

# Load test environment variables from .env.test file
test_env_file = Path(__file__).parent.parent.parent.parent / ".env.test"
if test_env_file.exists():
    with open(test_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
else:
    # Fallback to hardcoded values if .env.test doesn't exist
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["ASYNC_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["ENVIRONMENT"] = "test"
    os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine for the session."""
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        },
        echo=False,  # Set to True for SQL debugging
    )

    # Create all tables
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def test_session(test_engine):
    """Create a test database session for each test."""
    Session = sessionmaker(bind=test_engine)
    session = Session()

    yield session

    # Clean up
    session.rollback()
    session.close()


@pytest.fixture
def sample_correlation_id():
    """Generate a sample correlation ID for testing."""
    import uuid

    return str(uuid.uuid4())


# Configure pytest markers
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.filterwarnings("ignore::DeprecationWarning"),
    pytest.mark.filterwarnings("ignore::PendingDeprecationWarning"),
]

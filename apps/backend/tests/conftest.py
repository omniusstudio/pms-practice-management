#!/usr/bin/env python3
"""Pytest configuration and shared fixtures for database tests."""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from main import app
from middleware.auth_middleware import AuthenticatedUser
from models.base import Base  # noqa: E402
from models.user import User

# Load test environment variables from .env.test file
test_env_file = Path(__file__).parent.parent.parent.parent / ".env.test"
if test_env_file.exists():
    with open(test_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
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


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        roles=["clinician"],
        permissions=[
            "read:patients",
            "write:patients",
            "read:appointments",
            "write:appointments",
        ],
        is_active=True,
        is_admin=False,
        provider_id="test_provider_123",
        provider_name="test_provider",
    )
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user for testing."""
    user = User(
        id=uuid4(),
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        roles=["admin"],
        permissions=[
            "read:all",
            "write:all",
            "delete:all",
            "manage:users",
            "manage:system",
            "manage:billing",
            "audit:access",
            "read:patients",
            "write:patients",
            "read:appointments",
            "write:appointments",
            "read:notes",
            "write:notes",
            "read:billing",
            "write:billing",
            "read:ledger",
            "write:ledger",
            "read:financial_reports",
        ],
        is_active=True,
        is_admin=True,
        provider_id="admin_provider_123",
        provider_name="admin_provider",
    )
    return user


@pytest.fixture
def mock_authenticated_user(mock_user):
    """Create a mock authenticated user for testing."""
    return AuthenticatedUser(
        user=mock_user,
        permissions=[
            "read:patients",
            "write:patients",
            "read:appointments",
            "write:appointments",
            "read:notes",
            "write:notes",
            "read:profile",
            "write:profile",
        ],
    )


@pytest.fixture
def mock_authenticated_admin(mock_admin_user):
    """Create a mock authenticated admin user for testing."""
    return AuthenticatedUser(
        user=mock_admin_user,
        permissions=[
            "read:all",
            "write:all",
            "delete:all",
            "manage:users",
            "manage:system",
            "manage:billing",
            "audit:access",
            "read:patients",
            "write:patients",
            "read:appointments",
            "write:appointments",
            "read:notes",
            "write:notes",
            "read:billing",
            "write:billing",
            "read:ledger",
            "write:ledger",
            "read:financial_reports",
        ],
    )


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.close = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.delete = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.rollback = AsyncMock()

    # Mock common query result patterns
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalar.return_value = 0
    mock_result.first.return_value = None
    mock_db.execute.return_value = mock_result

    return mock_db


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def client_id():
    """Generate test client ID."""
    return str(uuid4())


@pytest.fixture
def appointment_id():
    """Generate test appointment ID."""
    return str(uuid4())


@pytest.fixture
def provider_id():
    """Generate test provider ID."""
    return str(uuid4())


@pytest.fixture
def user_id():
    """Generate test user ID."""
    return str(uuid4())


# Configure pytest markers
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.filterwarnings("ignore::DeprecationWarning"),
    pytest.mark.filterwarnings("ignore::PendingDeprecationWarning"),
]

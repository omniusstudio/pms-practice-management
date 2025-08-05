"""Database configuration and connection management."""

import os
import sys
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from models.base import Base
except ImportError:
    # Fallback for import issues
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))
    from models.base import Base  # noqa: E402

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://omniusstudio:8Z3Rx04LMNw3@localhost:5432/pmsdb"
)

# Convert to async URL - handle both PostgreSQL and SQLite
if DATABASE_URL.startswith("sqlite://"):
    ASYNC_DATABASE_URL = os.getenv(
        "ASYNC_DATABASE_URL",
        DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://"),
    )
else:
    ASYNC_DATABASE_URL = os.getenv(
        "ASYNC_DATABASE_URL",
        DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    )

# Create engines
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
)

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
)

# Create session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


# Event listeners for audit logging
@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(
    conn, cursor, statement, parameters, context, executemany
):
    """Log SQL execution for audit purposes."""
    # Only log DML operations (INSERT, UPDATE, DELETE)
    dml_keywords = ["INSERT", "UPDATE", "DELETE"]
    if any(keyword in statement.upper() for keyword in dml_keywords):
        # Log would be implemented here
        pass


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """Create all database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all database tables (for testing)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def create_tables_sync():
    """Create all database tables synchronously."""
    Base.metadata.create_all(bind=engine)


def drop_tables_sync():
    """Drop all database tables synchronously (for testing)."""
    Base.metadata.drop_all(bind=engine)


# Health check function
def check_database_health() -> bool:
    """Check if database is accessible."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def check_database_health_async() -> bool:
    """Check if database is accessible (async)."""
    try:
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# Alias for backward compatibility
check_async_database_health = check_database_health_async

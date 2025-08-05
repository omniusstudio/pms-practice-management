"""Alembic environment configuration."""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models import *  # noqa: F401, F403, E402

# Import all models to ensure they're registered with SQLAlchemy
# These imports must come after sys.path modification
from models.base import Base  # noqa: F401, E402

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def get_database_url():
    """Get database URL from environment or config."""
    # Get config from context during migration execution
    config = context.config
    return os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    # Setup logging
    config = context.config
    if config.config_file_name is not None:
        fileConfig(config.config_file_name)

    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Setup logging
    config = context.config
    if config.config_file_name is not None:
        fileConfig(config.config_file_name)

    # Override the sqlalchemy.url with environment variable if available
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


def run_migrations():
    """Run migrations based on context mode."""
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()


# Only run migrations if this script is executed by alembic
if __name__ == "__main__" or hasattr(context, "config"):
    try:
        run_migrations()
    except NameError:
        # Context not available, likely being imported for testing
        pass

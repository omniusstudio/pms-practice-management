"""Environment-specific configuration loader.

This module provides utilities for loading environment-specific .env files
based on the current deployment environment.
"""

import os
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


def load_environment_config(environment: Optional[str] = None) -> None:
    """Load environment-specific .env file.

    This function loads the appropriate .env file based on the environment:
    - .env.test for test environment
    - .env.staging for staging environment
    - .env.production for production environment
    - .env for development or fallback

    Args:
        environment: The target environment. If None, uses ENVIRONMENT env var.
    """
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")

    # Get the project root directory (3 levels up from this file)
    project_root = Path(__file__).parent.parent.parent.parent

    # Determine which .env file to load
    env_files_to_try = []

    if environment == "test":
        env_files_to_try.append(project_root / ".env.test")
    elif environment == "staging":
        env_files_to_try.append(project_root / ".env.staging")
    elif environment == "production":
        env_files_to_try.append(project_root / ".env.production")

    # Always try the default .env file as fallback
    env_files_to_try.append(project_root / ".env")

    # Load the first available .env file
    loaded_file = None
    for env_file in env_files_to_try:
        if env_file.exists():
            logger.info(f"Loading environment configuration from {env_file}")
            _load_env_file(env_file)
            loaded_file = env_file
            break

    if loaded_file is None:
        logger.warning(f"No .env file found for environment '{environment}'")
    else:
        logger.info(
            f"Successfully loaded configuration for environment "
            f"'{environment}' from {loaded_file.name}"
        )


def _load_env_file(env_file_path: Path) -> None:
    """Load environment variables from a .env file.

    Args:
        env_file_path: Path to the .env file to load
    """
    try:
        with open(env_file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse key=value pairs
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]

                    # Only set if not already in environment
                    # (env vars take precedence)
                    if key not in os.environ:
                        os.environ[key] = value
                else:
                    logger.warning(
                        f"Invalid line format in {env_file_path}:" f"{line_num}: {line}"
                    )

    except Exception as e:
        logger.error(f"Error loading .env file {env_file_path}: {e}")
        raise


def get_environment_info() -> dict:
    """Get current environment information.

    Returns:
        Dictionary containing environment configuration details
    """
    return {
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug": os.getenv("DEBUG", "false").lower() == "true",
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "database_url_set": bool(os.getenv("DATABASE_URL")),
        "redis_url_set": bool(os.getenv("REDIS_URL")),
        "secret_key_set": bool(os.getenv("SECRET_KEY")),
        "jwt_secret_key_set": bool(os.getenv("JWT_SECRET_KEY")),
    }


def validate_required_env_vars() -> list:
    """Validate that required environment variables are set.

    Returns:
        List of missing required environment variables
    """
    required_vars = ["SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL", "REDIS_URL"]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    return missing_vars

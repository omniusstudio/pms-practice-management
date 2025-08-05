"""Session middleware for Auth0 OIDC authentication."""

import os

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware


def add_session_middleware(app: FastAPI) -> None:
    """Add session middleware to FastAPI app."""
    # Use a secure session key from environment or generate one
    session_key = os.getenv(
        "SESSION_SECRET_KEY", "your-secret-key-change-this-in-production"
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=session_key,
        max_age=3600,  # 1 hour
        same_site="lax",
        https_only=os.getenv("ENVIRONMENT") == "production",
    )

"""Auth0 OIDC Authentication Router for HIPAA-compliant PMS."""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.parse import quote_plus, urlencode

import jwt
import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

# Import from correct paths based on project structure
from config.auth_config import get_auth_config
from database import SessionLocal
from models.user import User

# Initialize router and config
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


class Auth0Service:
    """Service for Auth0 OIDC operations."""

    def __init__(self):
        self.config = get_auth_config()
        self.jwks_client = None
        self._jwks_cache = None
        self._jwks_cache_time = None

    def get_authorization_url(self, state: str) -> str:
        """Generate Auth0 authorization URL."""
        params = {
            "response_type": "code",
            "client_id": self.config.auth0_client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": self.config.scope,
            "state": state,
            "audience": self.config.auth0_audience,
        }

        query_string = urlencode(params, quote_via=quote_plus)
        return f"{self.config.authorization_endpoint}?{query_string}"

    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        token_data = {
            "grant_type": "authorization_code",
            "client_id": self.config.auth0_client_id,
            "client_secret": self.config.auth0_client_secret,
            "code": code,
            "redirect_uri": self.config.redirect_uri,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.post(
            self.config.token_endpoint, data=token_data, headers=headers, timeout=30
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=400, detail=f"Token exchange failed: {response.text}"
            )

        return response.json()

    async def get_jwks(self) -> Dict[str, Any]:
        """Get JWKS from Auth0 with caching."""
        now = datetime.utcnow()

        # Cache JWKS for 1 hour
        if (
            self._jwks_cache is None
            or self._jwks_cache_time is None
            or now - self._jwks_cache_time > timedelta(hours=1)
        ):
            response = requests.get(self.config.jwks_uri, timeout=30)
            response.raise_for_status()
            self._jwks_cache = response.json()
            self._jwks_cache_time = now

        return self._jwks_cache

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token using Auth0 JWKS."""
        try:
            # Get the unverified header to find the key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                raise HTTPException(status_code=401, detail="Token missing key ID")

            # Get JWKS and find the matching key
            jwks = await self.get_jwks()
            key = None

            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                    break

            if not key:
                raise HTTPException(
                    status_code=401, detail="Unable to find appropriate key"
                )

            # Verify the token
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.config.auth0_audience,
                issuer=self.config.issuer,
            )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


# Auth0 service will be instantiated when needed


# User model is imported from models.user


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/login")
async def login(request: Request):
    """Initiate Auth0 login flow."""
    # Generate state parameter for CSRF protection
    state = os.urandom(32).hex()
    request.session["oauth_state"] = state

    # Store the original URL for post-login redirect
    next_url = request.query_params.get("next", "/dashboard")
    request.session["next_url"] = next_url

    # Generate authorization URL
    auth0_service = Auth0Service()
    auth_url = auth0_service.get_authorization_url(state)

    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Handle Auth0 callback."""
    if error:
        raise HTTPException(status_code=400, detail=f"Authentication error: {error}")

    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")

    # Verify state parameter
    stored_state = request.session.get("oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    try:
        # Exchange authorization code for tokens
        auth0_service = Auth0Service()
        tokens = await auth0_service.exchange_code_for_tokens(code)
        access_token = tokens.get("access_token")
        id_token = tokens.get("id_token")

        if not access_token or not id_token:
            raise HTTPException(status_code=400, detail="Failed to obtain tokens")

        # Verify and decode the ID token
        user_info = await auth0_service.verify_token(id_token)

        # Store user session
        request.session["user"] = {
            "sub": user_info.get("sub"),
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "access_token": access_token,
            "id_token": id_token,
        }

        # Create or update user in database
        user = db.query(User).filter(User.auth0_sub == user_info.get("sub")).first()

        if not user:
            user = User(
                auth0_sub=user_info.get("sub"),
                email=user_info.get("email"),
                name=user_info.get("name"),
                is_active=True,
            )
            db.add(user)
        else:
            user.email = user_info.get("email")
            user.name = user_info.get("name")
            user.last_login = datetime.utcnow()

        db.commit()

        # Clean up session
        request.session.pop("oauth_state", None)

        # Redirect to original URL or dashboard
        next_url = request.session.pop("next_url", "/dashboard")
        return RedirectResponse(url=next_url)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.post("/logout")
async def logout(request: Request):
    """Logout user and clear session."""
    # Clear session
    request.session.clear()

    # Generate Auth0 logout URL
    config = get_auth_config()
    logout_params = {
        "client_id": config.auth0_client_id,
        "returnTo": config.logout_redirect_uri,
    }

    logout_url = (
        f"https://{config.auth0_domain}/v2/logout?" f"{urlencode(logout_params)}"
    )

    return {"logout_url": logout_url}


@router.get("/user")
async def get_current_user(request: Request):
    """Get current authenticated user."""
    user_data = request.session.get("user")

    if not user_data:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {
        "sub": user_data.get("sub"),
        "email": user_data.get("email"),
        "name": user_data.get("name"),
        "authenticated": True,
    }


async def get_current_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """FastAPI dependency to get current user from JWT token."""
    token = credentials.credentials
    auth0_service = Auth0Service()
    return await auth0_service.verify_token(token)


async def require_auth(request: Request) -> Dict[str, Any]:
    """FastAPI dependency to require authentication."""
    user_data = request.session.get("user")

    if not user_data:
        raise HTTPException(status_code=401, detail="Authentication required")

    return user_data

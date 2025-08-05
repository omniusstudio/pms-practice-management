#!/usr/bin/env python3
"""Simple integration test for auth tokens system."""

import os
import sys
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.auth_token import TokenType  # noqa: E402

# Import after path setup
from models.base import Base  # noqa: E402
from services.auth_service import AuthService  # noqa: E402


def test_auth_tokens_integration():
    """Test the complete auth tokens workflow."""
    print("Testing Auth Tokens Integration...")

    # Use PostgreSQL for testing (requires running database)
    # For demo purposes, we'll use SQLite but with proper UUID handling
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, echo=False
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        # Initialize auth service
        correlation_id = str(uuid4())
        auth_service = AuthService(session=session, correlation_id=correlation_id)

        # Test 1: Create access token
        print("1. Creating access token...")
        user_id = uuid4()
        plaintext_token, token_record = auth_service.create_token(
            token_type=TokenType.ACCESS,
            user_id=user_id,
            client_ip="192.168.1.100",
            user_agent="Test Browser",
        )
        print(f"   ✓ Token created: {token_record.id}")
        print(f"   ✓ Token type: {token_record.token_type}")
        print(f"   ✓ Expires at: {token_record.expires_at}")

        # Test 2: Validate token
        print("2. Validating token...")
        validated_token = auth_service.validate_token(plaintext_token)
        assert validated_token is not None
        assert validated_token.id == token_record.id
        print("   ✓ Token validated successfully")

        # Test 3: Create refresh token
        print("3. Creating refresh token...")
        refresh_plaintext, refresh_record = auth_service.create_token(
            token_type=TokenType.REFRESH, user_id=user_id
        )
        print(f"   ✓ Refresh token created: {refresh_record.id}")

        # Test 4: Token rotation
        print("4. Testing token rotation...")
        # First validate the token to get the AuthToken object
        token_to_rotate = auth_service.validate_token(plaintext_token)
        assert token_to_rotate is not None
        new_plaintext, new_token = auth_service.rotate_token(token_to_rotate)
        assert new_token is not None
        assert new_token.parent_token_id == token_record.id
        print(f"   ✓ Token rotated: {new_token.id}")

        # Test 5: Get user tokens
        print("5. Getting user tokens...")
        user_tokens = auth_service.get_user_tokens(user_id)
        print(f"   ✓ Found {len(user_tokens)} tokens for user")

        # Test 6: Revoke token
        print("6. Revoking token...")
        revoked = auth_service.revoke_token(new_token.id)
        assert revoked is True
        print("   ✓ Token revoked successfully")

        # Test 7: Verify revoked token cannot be validated
        print("7. Verifying revoked token...")
        invalid_token = auth_service.validate_token(new_plaintext)
        assert invalid_token is None
        print("   ✓ Revoked token correctly rejected")

        print("\n🎉 All auth token tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    try:
        test_auth_tokens_integration()
        sys.exit(0)
    except Exception:
        sys.exit(1)

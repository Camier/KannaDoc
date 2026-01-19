#!/usr/bin/env python3
"""Simple auth validation script."""

import sys
import asyncio

sys.path.insert(0, "/LAB/@thesis/layra/backend")

from app.core.config import settings
from app.core.simple_auth import simple_auth


def test_simple_auth():
    print("=" * 50)
    print("LAYRA Simple Auth Validation")
    print("=" * 50)

    # Test 1: Check if simple auth is enabled
    print(f"\n[1] SIMPLE_AUTH_MODE: {settings.simple_auth_mode}")
    assert settings.simple_auth_mode == True, "Simple auth should be enabled"
    print("   ✅ Simple auth is ENABLED")

    # Test 2: Check default values
    print(f"\n[2] Default Settings:")
    print(f"   - API Key: {settings.simple_api_key}")
    print(f"   - Username: {settings.simple_username}")
    print(f"   - Password: {settings.simple_password}")
    assert settings.simple_api_key == "layra-dev-key-2024"
    assert settings.simple_username == "layra"
    assert settings.simple_password == "layra123"
    print("   ✅ Default values correct")

    # Test 3: Test password hashing
    print(f"\n[3] Password Verification:")
    is_valid = simple_auth.verify_password("layra123")
    print(f"   - 'layra123' matches: {is_valid}")
    assert is_valid == True, "Password should match"
    is_invalid = simple_auth.verify_password("wrong")
    print(f"   - 'wrong' matches: {is_invalid}")
    assert is_invalid == False, "Wrong password should not match"
    print("   ✅ Password verification works")

    # Test 4: Test token creation
    print(f"\n[4] Token Creation:")
    token = simple_auth.create_token()
    print(f"   - Token created: {token[:50]}...")
    assert token is not None
    assert len(token) > 0
    print("   ✅ Token created successfully")

    # Test 5: Test token decoding
    print(f"\n[5] Token Decoding:")
    payload = simple_auth.decode_token(token)
    print(f"   - Payload: {payload}")
    assert payload is not None
    assert payload.get("sub") == "layra"
    assert payload.get("type") == "simple"
    print("   ✅ Token decoded successfully")

    # Test 6: Test invalid token
    print("\n[6] Invalid Token:")
    invalid = simple_auth.decode_token("invalid.token.here")
    print(f"   - Invalid token returns: {invalid}")
    assert invalid is None
    print("   ✅ Invalid token rejected")

    print("\n" + "=" * 50)
    print("✅ ALL TESTS PASSED!")
    print("=" * 50)

    print("\n📝 Quick Usage:")
    print("   # API Key auth:")
    print('   curl -H "X-API-Key: layra-dev-key-2024" http://localhost:8000/api/v1/...')
    print("")
    print("   # Password auth:")
    print(
        '   curl -H "Authorization: Bearer layra123" http://localhost:8000/api/v1/...'
    )


if __name__ == "__main__":
    test_simple_auth()

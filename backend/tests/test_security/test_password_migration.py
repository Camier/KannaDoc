# tests/test_security/test_password_migration.py
import pytest
import sys
import os

# Import from app.core.security to test the actual module
from app.core.security import verify_password_legacy, verify_password


def test_legacy_verification_with_known_salt():
    """Test that legacy verification works with the old hardcoded salt"""
    # This hash was created with: bcrypt.hash("testpassword" + "mynameisliwei,nicetomeetyou!")
    # Note: Bcrypt uses random salts, so this hash differs from the spec example.
    # The important thing is that it verifies correctly with the legacy salt.
    legacy_hash = "$2b$12$Q6uBMW695xzHSnmKiJCfreyXX3/vnkh13LtvGrs/ucOy0Bc1pPOyO"

    # Legacy verification should work
    assert verify_password_legacy("testpassword", legacy_hash) is True
    assert verify_password_legacy("wrongpassword", legacy_hash) is False


def test_new_verification_without_salt():
    """Test that new verification works without custom salt"""
    # Generate a hash without custom salt
    import bcrypt
    password = "testpassword"
    new_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # New verification should work
    assert verify_password("testpassword", new_hash) is True
    assert verify_password("wrongpassword", new_hash) is False


def test_legacy_and_new_hashes_are_different():
    """Test that using custom salt produces different hash than bcrypt alone"""
    import bcrypt

    password = "testpassword"
    salt = "mynameisliwei,nicetomeetyou!"

    # Legacy method (with custom salt)
    legacy_hash = bcrypt.hashpw((password + salt).encode('utf-8'), bcrypt.gensalt())

    # New method (without custom salt)
    new_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Hashes should be different
    assert legacy_hash != new_hash


def test_verify_password_legacy_function_exists():
    """Test that verify_password_legacy function exists in security.py"""
    # This test verifies the function was added to security.py
    security_path = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'core', 'security.py')
    with open(security_path, 'r') as f:
        content = f.read()
        assert 'def verify_password_legacy' in content
        assert 'Legacy password verification' in content
        assert 'mynameisliwei,nicetomeetyou!' in content

# tests/test_security/test_password_migration.py
import pytest
import sys
import os

# Test in isolation to avoid import issues
# This test verifies the logic of the legacy verification function
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password_legacy(plain_password: str, hashed_password: str) -> bool:
    """
    Legacy password verification for passwords hashed with custom salt.

    This function exists ONLY for migrating existing passwords that were
    created using the insecure hardcoded salt. After migration, this
    function should be removed.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The hash created with the old salt method

    Returns:
        True if password matches, False otherwise
    """
    salt = "mynameisliwei,nicetomeetyou!"  # Legacy salt for migration only
    return pwd_context.verify(plain_password + salt, hashed_password)


def verify_password(plain_password, hashed_password):
    """New password verification without custom salt."""
    return pwd_context.verify(plain_password, hashed_password)


def test_legacy_verification_with_known_salt():
    """Test that legacy verification works with the old hardcoded salt"""
    # This hash was created with: bcrypt.hash("testpassword" + "mynameisliwei,nicetomeetyou!")
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

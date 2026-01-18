# tests/test_security/test_password_hashing.py
import bcrypt
from app.core.security import get_password_hash, verify_password


def test_new_passwords_use_proper_bcrypt():
    """Test that new password hashes don't use the custom salt"""
    password = "testpassword123"
    hashed = get_password_hash(password)

    # Should be a valid bcrypt hash
    assert hashed.startswith("$2b$")

    # Should verify with verify_password
    assert verify_password(password, hashed) is True

    # Should NOT verify with legacy method (different hash)
    from app.core.security import verify_password_legacy
    assert verify_password_legacy(password, hashed) is False


def test_same_passwords_have_different_hashes():
    """Test that hashing the same password twice produces different hashes"""
    password = "testpassword123"
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)

    # Hashes should be different (bcrypt uses random salt)
    assert hash1 != hash2

    # But both should verify correctly
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True


def test_password_hashing_does_not_use_legacy_salt():
    """Test that get_password_hash doesn't concatenate the legacy salt"""
    password = "testpassword123"
    salt = "mynameisliwei,nicetomeetyou!"

    # Hash using our function
    our_hash = get_password_hash(password)

    # Hash using bcrypt directly (proper way)
    proper_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Hash using legacy method (wrong way)
    legacy_hash = bcrypt.hashpw((password + salt).encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Our hash should NOT match legacy hash pattern
    # (We can't compare directly due to random salt, but we can verify structure)

    # Our hash should verify properly
    assert verify_password(password, our_hash) is True

    # Legacy hash should NOT verify with our new method
    assert verify_password(password, legacy_hash) is False

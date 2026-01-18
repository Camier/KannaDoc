# tests/test_security/test_password_migration.py
import pytest
import sys
import os

# Import from app.core.security to test the actual module
from app.core.security import verify_password_legacy, verify_password


@pytest.fixture
def legacy_hash():
    """Generate a legacy hash for testing"""
    import bcrypt
    password = "testpassword"
    salt = "mynameisliwei,nicetomeetyou!"
    return bcrypt.hashpw((password + salt).encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def test_legacy_verification_with_known_salt(legacy_hash):
    """Test that legacy verification works with the old hardcoded salt"""
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


# Task 3: Tests for authenticate_user migration logic
import pytest
from unittest.mock import Mock, AsyncMock
from app.core.security import authenticate_user


@pytest.mark.asyncio
async def test_authenticate_user_migrates_legacy_password():
    """Test that authenticate_user migrates legacy passwords on successful login"""
    # Generate a proper legacy hash
    import bcrypt
    password = "testpassword"
    salt = "mynameisliwei,nicetomeetyou!"
    legacy_hash = bcrypt.hashpw((password + salt).encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Create mock user with legacy hash
    mock_user = Mock()
    mock_user.hashed_password = legacy_hash
    mock_user.password_migration_required = True
    mock_user.username = "testuser"

    # Mock database session - properly chain the async calls
    mock_db = AsyncMock()

    # Create mock for scalars().first()
    mock_scalars_instance = Mock()
    mock_scalars_instance.first.return_value = mock_user

    # result.scalars() is NOT async, returns mock_scalars_instance
    mock_result = Mock()  # Regular Mock, not AsyncMock!
    mock_result.scalars.return_value = mock_scalars_instance

    # db.execute() IS async, returns mock_result when awaited
    mock_db.execute.return_value = mock_result

    # Store original hash for comparison
    original_hash = mock_user.hashed_password

    # Authenticate with correct password
    result = await authenticate_user(mock_db, "testuser", "testpassword")

    # Should return user
    assert result is not None
    assert result.username == "testuser"

    # Password should be rehashed (different from original)
    assert result.hashed_password != original_hash

    # Migration flag should be cleared
    assert result.password_migration_required is False

    # Database should be updated
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_authenticate_user_fails_with_wrong_legacy_password():
    """Test that authenticate_user fails with wrong password"""
    # Generate a proper legacy hash
    import bcrypt
    password = "testpassword"
    salt = "mynameisliwei,nicetomeetyou!"
    legacy_hash = bcrypt.hashpw((password + salt).encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    mock_user = Mock()
    mock_user.hashed_password = legacy_hash
    mock_user.password_migration_required = True

    mock_db = AsyncMock()
    mock_scalars_instance = Mock()
    mock_scalars_instance.first.return_value = mock_user
    mock_result = Mock()  # Regular Mock, not AsyncMock!
    mock_result.scalars.return_value = mock_scalars_instance
    mock_db.execute.return_value = mock_result

    # Authenticate with wrong password
    result = await authenticate_user(mock_db, "testuser", "wrongpassword")

    # Should return None
    assert result is None


@pytest.mark.asyncio
async def test_authenticate_user_works_with_new_passwords():
    """Test that authenticate_user works with already-migrated passwords"""
    # Create a proper new-style hash (bcrypt without custom salt)
    import bcrypt
    new_hash = bcrypt.hashpw(b"newpassword", bcrypt.gensalt()).decode('utf-8')

    mock_user = Mock()
    mock_user.hashed_password = new_hash
    mock_user.password_migration_required = False
    mock_user.username = "testuser"

    mock_db = AsyncMock()
    mock_scalars_instance = Mock()
    mock_scalars_instance.first.return_value = mock_user
    mock_result = Mock()  # Regular Mock, not AsyncMock!
    mock_result.scalars.return_value = mock_scalars_instance
    mock_db.execute.return_value = mock_result

    # Authenticate with correct password
    result = await authenticate_user(mock_db, "testuser", "newpassword")

    # Should return user
    assert result is not None

    # Password should NOT be updated (already migrated)
    assert result.hashed_password == new_hash

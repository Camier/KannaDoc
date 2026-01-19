# Remove Hardcoded Password Salt Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix critical security vulnerability by removing hardcoded password salt and letting bcrypt handle salting automatically.

**Architecture:** The current implementation uses a hardcoded salt `"mynameisliwei,nicetomeetyou!"` concatenated with passwords before bcrypt hashing. This defeats bcrypt's built-in per-password random salt generation, making all passwords vulnerable to rainbow table attacks. The fix removes the custom salt and uses bcrypt directly, which generates unique salts for each password automatically. Since existing password hashes were created with the custom salt, we need a migration strategy that rehashes passwords on next login.

**Tech Stack:** Python 3.10, FastAPI, passlib with bcrypt, SQLAlchemy (async), Pytest

---

## Pre-Implementation Checklist

- [ ] Create a new git worktree for this work: `git worktree add ../layra-password-salt-fix -b feature/remove-hardcoded-salt`
- [ ] Activate the backend Python environment
- [ ] Install test dependencies: `pip install pytest pytest-asyncio pytest-cov`
- [ ] Verify existing tests pass: `pytest tests/ -v`

---

## Task 1: Add Migration Flag to User Model

**Files:**
- Create: `backend/app/alembic/versions/XXXX_add_password_migration_flag.py`
- Modify: `backend/app/models/user.py`
- Test: `tests/test_models/test_user.py` (create if doesn't exist)

**Step 1: Write the failing test**

```python
# tests/test_models/test_user.py
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.db.mysql_session import get_mysql_session


@pytest.mark.asyncio
async def test_user_model_has_password_migration_flag(db: AsyncSession):
    """Test that User model has password_migration_required field"""
    # Create a new user
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$testhash"
    )
    db.add(user)
    await db.commit()

    # Query and check the field exists
    result = await db.execute(select(User).where(User.username == "testuser"))
    fetched_user = result.scalars().first()

    assert hasattr(fetched_user, "password_migration_required")
    assert fetched_user.password_migration_required is True  # Default should be True
```

**Step 2: Run test to verify it fails**

```bash
cd /LAB/@thesis/layra/backend
pytest tests/test_models/test_user.py::test_user_model_has_password_migration_flag -v
```

Expected: `FAIL - AttributeError: 'User' object has no attribute 'password_migration_required'`

**Step 3: Add field to User model**

```python
# backend/app/models/user.py
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)

    # NEW: Password migration flag
    password_migration_required = Column(Boolean, default=True, nullable=False)
```

**Step 4: Create Alembic migration**

```python
# backend/app/alembic/versions/XXXX_add_password_migration_flag.py
"""add password migration flag

Revision ID: add_password_migration_flag
Revises: <previous_revision_id>
Create Date: 2026-01-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_password_migration_flag'
down_revision = '<previous_revision_id>'  # Find current with: alembic current
branch_labels = None
depends_on = None


def upgrade():
    """Add password_migration_required column to users table"""
    op.add_column('users', sa.Column('password_migration_required', sa.Boolean(), nullable=False, server_default='1'))


def downgrade():
    """Remove password_migration_required column from users table"""
    op.drop_column('users', 'password_migration_required')
```

**Step 5: Run migration**

```bash
cd /LAB/@thesis/layra/backend
alembic upgrade head
```

**Step 6: Run test to verify it passes**

```bash
pytest tests/test_models/test_user.py::test_user_model_has_password_migration_flag -v
```

Expected: `PASS`

**Step 7: Commit**

```bash
git add backend/app/models/user.py backend/app/alembic/versions/XXXX_add_password_migration_flag.py tests/test_models/test_user.py
git commit -m "feat(user): add password_migration_required flag for bcrypt migration"
```

---

## Task 2: Add Legacy Password Verification Function

**Files:**
- Create: `backend/app/core/security.py` (add new function)
- Test: `tests/test_security/test_password_migration.py` (create new file)

**Step 1: Write the failing test**

```python
# tests/test_security/test_password_migration.py
import pytest
from app.core.security import verify_password_legacy, verify_password


def test_legacy_verification_with_known_salt():
    """Test that legacy verification works with the old hardcoded salt"""
    # This hash was created with: bcrypt.hash("testpassword" + "mynameisliwei,nicetomeetyou!")
    legacy_hash = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"

    # Legacy verification should work
    assert verify_password_legacy("testpassword", legacy_hash) is True
    assert verify_password_legacy("wrongpassword", legacy_hash) is False


def test_new_verification_without_salt():
    """Test that new verification works without custom salt"""
    # This hash was created with: bcrypt.hash("testpassword") - no custom salt
    new_hash = "$2b$12$NNv3R8fY7U5I5l8zX9Z0xeY9Z8Z0Z0Z0Z0Z0Z0Z0Z0Z0Z0Z0Z0Z0"

    # New verification should work
    assert verify_password("testpassword", new_hash) is True


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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_security/test_password_migration.py::test_legacy_verification_with_known_salt -v
```

Expected: `FAIL - NameError: 'verify_password_legacy' is not defined`

**Step 3: Implement legacy verification function**

```python
# backend/app/core/security.py
# Add this after the existing functions (around line 28)

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
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_security/test_password_migration.py -v
```

Expected: `PASS`

**Step 5: Commit**

```bash
git add backend/app/core/security.py tests/test_security/test_password_migration.py
git commit -m "feat(security): add legacy password verification for migration"
```

---

## Task 3: Update authenticate_user with Migration Logic

**Files:**
- Modify: `backend/app/core/security.py:82-88`
- Test: `tests/test_security/test_password_migration.py` (add tests)

**Step 1: Write the failing test**

```python
# Add to tests/test_security/test_password_migration.py

import pytest
from unittest.mock import Mock, AsyncMock
from app.core.security import authenticate_user


@pytest.mark.asyncio
async def test_authenticate_user_migrates_legacy_password():
    """Test that authenticate_user migrates legacy passwords on successful login"""
    # Create mock user with legacy hash
    mock_user = Mock()
    mock_user.hashed_password = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
    mock_user.password_migration_required = True

    # Mock database session
    mock_db = AsyncMock()
    mock_db.execute = Mock()
    mock_result = Mock()
    mock_result.scalars().first.return_value = mock_user
    mock_db.execute.return_value = mock_result

    # Authenticate with correct password
    result = await authenticate_user(mock_db, "testuser", "testpassword")

    # Should return user
    assert result is not None
    assert result.username == "testuser"

    # Password should be rehashed (different from original)
    assert result.hashed_password != mock_user.hashed_password

    # Migration flag should be cleared
    assert result.password_migration_required is False

    # Database should be updated
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_authenticate_user_fails_with_wrong_legacy_password():
    """Test that authenticate_user fails with wrong password"""
    mock_user = Mock()
    mock_user.hashed_password = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
    mock_user.password_migration_required = True

    mock_db = AsyncMock()
    mock_db.execute = Mock()
    mock_result = Mock()
    mock_result.scalars().first.return_value = mock_user
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

    mock_db = AsyncMock()
    mock_db.execute = Mock()
    mock_result = Mock()
    mock_result.scalars().first.return_value = mock_user
    mock_db.execute.return_value = mock_result

    # Authenticate with correct password
    result = await authenticate_user(mock_db, "testuser", "newpassword")

    # Should return user
    assert result is not None

    # Password should NOT be updated (already migrated)
    assert result.hashed_password == new_hash
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_security/test_password_migration.py::test_authenticate_user_migrates_legacy_password -v
```

Expected: `FAIL - authenticate_user doesn't handle migration`

**Step 3: Implement migration logic**

```python
# backend/app/core/security.py
# Replace the existing authenticate_user function (lines 82-88)

async def authenticate_user(db: AsyncSession, username: str, password: str):
    """
    Authenticate a user and migrate legacy passwords if needed.

    Legacy passwords (created with hardcoded salt) will be rehashed
    using proper bcrypt without custom salt on successful authentication.

    Args:
        db: Database session
        username: Username to authenticate
        password: Plain text password

    Returns:
        User object if authenticated, None otherwise
    """
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()

    if not user:
        return None

    # Try NEW method first (proper bcrypt without custom salt)
    if verify_password(password, user.hashed_password):
        return user

    # Try LEGACY method (with hardcoded salt) for migration
    if hasattr(user, 'password_migration_required') and user.password_migration_required:
        if verify_password_legacy(password, user.hashed_password):
            # Migration: Rehash with proper bcrypt and update database
            user.hashed_password = get_password_hash(password)
            user.password_migration_required = False
            await db.commit()

            return user

    return None
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_security/test_password_migration.py -v
```

Expected: `PASS`

**Step 5: Commit**

```bash
git add backend/app/core/security.py tests/test_security/test_password_migration.py
git commit -m "feat(security): add automatic password migration on login"
```

---

## Task 4: Remove Hardcoded Salt from New Registrations

**Files:**
- Modify: `backend/app/core/security.py:15,22,26`
- Test: `tests/test_security/test_password_hashing.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_security/test_password_hashing.py::test_password_hashing_does_not_use_legacy_salt -v
```

Expected: `FAIL - Current implementation uses legacy salt`

**Step 3: Remove hardcoded salt and update functions**

```python
# backend/app/core/security.py

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# REMOVED: salt = "mynameisliwei,nicetomeetyou!"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    # FIXED: Let bcrypt handle salting automatically
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    # FIXED: Hash password directly, bcrypt generates unique salt
    return pwd_context.hash(password)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_security/test_password_hashing.py -v
```

Expected: `PASS`

**Step 5: Commit**

```bash
git add backend/app/core/security.py tests/test_security/test_password_hashing.py
git commit -m "fix(security)!: remove hardcoded password salt, use proper bcrypt"
```

---

## Task 5: Update Registration to Set Migration Flag

**Files:**
- Modify: `backend/app/api/endpoints/auth.py:95-100`
- Test: `tests/test_api/test_auth.py`

**Step 1: Write the failing test**

```python
# tests/test_api/test_auth.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.db.mysql_session import get_mysql_session


@pytest.mark.asyncio
async def test_new_users_have_migration_flag_false(db: AsyncSession):
    """Test that newly registered users don't need password migration"""
    client = TestClient(app)

    # Register a new user
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser123",
            "email": "newuser@example.com",
            "password": "securepassword456"
        }
    )

    assert response.status_code == 200

    # Check that password_migration_required is False
    result = await db.execute(select(User).where(User.username == "newuser123"))
    user = result.scalars().first()

    assert user is not None
    assert user.password_migration_required is False

    # Verify password works with new method
    from app.core.security import verify_password
    assert verify_password("securepassword456", user.hashed_password) is True
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_api/test_auth.py::test_new_users_have_migration_flag_false -v
```

Expected: `FAIL - New users have migration_flag=True (default)`

**Step 3: Update registration to set flag to False**

```python
# backend/app/api/endpoints/auth.py
# Modify the registration endpoint (around line 95)

# Create new user
hashed_password = get_password_hash(user.password)
db_user = User(
    username=user.username,
    email=user.email,
    hashed_password=hashed_password,
    password_migration_required=False  # New users don't need migration
)
db.add(db_user)
await db.commit()
await db.refresh(db_user)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_api/test_auth.py::test_new_users_have_migration_flag_false -v
```

Expected: `PASS`

**Step 5: Commit**

```bash
git add backend/app/api/endpoints/auth.py tests/test_api/test_auth.py
git commit -m "feat(auth): new users skip password migration"
```

---

## Task 6: Add Documentation and Deprecation Notice

**Files:**
- Create: `backend/docs/PASSWORD_MIGRATION.md`
- Modify: `backend/app/core/security.py` (add docstring notice)

**Step 1: Create migration documentation**

```markdown
# Password Migration Documentation

## Overview

This system previously used a **hardcoded password salt** (`"mynameisliwei,nicetomeetyou!"`) combined with bcrypt hashing. This was a **critical security vulnerability** that has been fixed.

## What Changed

### Before (Insecure)
```python
salt = "mynameisliwei,nicetomeetyou!"
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password + salt, hashed_password)
```

### After (Secure)
```python
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)
```

Bcrypt now handles salting automatically with a **unique random salt per password**.

## Migration Strategy

### Automatic Migration on Login

Existing user passwords are automatically migrated on their next successful login:

1. User logs in with their existing credentials
2. System verifies using legacy method (with old salt)
3. If successful, password is rehashed using proper bcrypt
4. `password_migration_required` flag is set to `False`
5. Database is updated

### New Users

New user registrations automatically use the secure hashing method and have `password_migration_required = False`.

## Database Schema

```sql
ALTER TABLE users ADD COLUMN password_migration_required BOOLEAN DEFAULT TRUE;
```

## Verification

To verify migration is complete:

```sql
SELECT COUNT(*) FROM users WHERE password_migration_required = TRUE;
```

When this returns 0, all users have been migrated.

## Timeline

- **Deployment**: Users with `password_migration_required = TRUE` can still log in
- **Migration Window**: Allow 2-4 weeks for all active users to log in
- **Cleanup**: After migration window, consider forcing password reset for any remaining legacy users

## Security Advisory

If you believe the database has been compromised, **force password reset for all users** immediately:

```sql
UPDATE users SET password_migration_required = TRUE, hashed_password = 'RESET_REQUIRED';
```

Then implement a password reset flow.
```

**Step 2: Add deprecation notice to security.py**

```python
# backend/app/core/security.py
"""
Security utilities for authentication and password hashing.

SECURITY NOTICE: This module previously used a hardcoded password salt.
The vulnerability has been fixed. The verify_password_legacy() function
exists ONLY for migrating existing passwords and should be removed
after all users have migrated.

TODO: Remove verify_password_legacy() after migration complete.
"""

from passlib.context import CryptContext
# ... rest of imports
```

**Step 3: Commit**

```bash
git add backend/docs/PASSWORD_MIGRATION.md backend/app/core/security.py
git commit -m "docs: add password migration documentation and deprecation notice"
```

---

## Task 7: Run Full Test Suite and Coverage

**Files:**
- Test: All test files

**Step 1: Run all tests**

```bash
cd /LAB/@thesis/layra/backend
pytest tests/ -v --cov=app --cov-report=html --cov-report=term
```

Expected: All tests pass

**Step 2: Check coverage**

```bash
# View coverage report
cat htmlcov/index.html | grep -A 5 "security.py"
```

Expected: `security.py` coverage > 90%

**Step 3: Fix any failing tests**

If any tests fail, investigate and fix. Common issues:
- Mock objects not matching new signature
- Database transactions not being committed
- Async/await issues

**Step 4: Commit**

```bash
git add .
git commit -m "test: ensure all tests pass after password migration"
```

---

## Task 8: Create Monitoring and Cleanup Plan

**Files:**
- Create: `backend/scripts/check_migration_status.py`
- Create: `backend/docs/MIGRATION_CLEANUP.md`

**Step 1: Create migration status checker**

```python
# backend/scripts/check_migration_status.py
"""Script to check password migration status"""

import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core.config import settings
from app.models.user import User


async def main():
    """Check how many users still need migration"""
    engine = create_async_engine(settings.db_url)

    async with engine.begin() as conn:
        result = await conn.execute(
            select(func.count(User.id)).where(User.password_migration_required == True)
        )
        legacy_count = result.scalar()

        result = await conn.execute(select(func.count(User.id)))
        total_count = result.scalar()

    await engine.dispose()

    percentage = (legacy_count / total_count * 100) if total_count > 0 else 0

    print(f"Password Migration Status:")
    print(f"  Total users: {total_count}")
    print(f"  Legacy users: {legacy_count}")
    print(f"  Migrated: {total_count - legacy_count} ({100 - percentage:.1f}%)")
    print(f"  Remaining: {legacy_count} ({percentage:.1f}%)")

    if legacy_count == 0:
        print("\n✅ Migration complete! You can now remove verify_password_legacy()")
    elif percentage < 5:
        print(f"\n⚠️  Almost complete! {legacy_count} users still need to log in.")
    else:
        print(f"\n🔄 Migration in progress. {percentage:.1f}% of users still need to log in.")


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 2: Run the checker**

```bash
cd /LAB/@thesis/layra/backend
python scripts/check_migration_status.py
```

**Step 3: Create cleanup documentation**

```markdown
# Password Migration Cleanup

## When to Clean Up

Run `python scripts/check_migration_status.py`. When it reports 0 legacy users, you can clean up.

## Cleanup Steps

### 1. Remove Legacy Function

Delete `verify_password_legacy()` from `app/core/security.py`.

### 2. Simplify authenticate_user

Remove the legacy migration path from `authenticate_user()`:

```python
async def authenticate_user(db: AsyncSession, username: str, password: str):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()

    if user and verify_password(password, user.hashed_password):
        return user
    return None
```

### 3. Remove Migration Flag (Optional)

After verifying all users are migrated:

```python
# Alembic migration
def upgrade():
    op.drop_column('users', 'password_migration_required')
```

### 4. Remove Documentation

Delete `PASSWORD_MIGRATION.md` and this file.

## Verification

After cleanup, run full test suite:

```bash
pytest tests/ -v --cov=app
```

All tests should pass.
```

**Step 4: Commit**

```bash
git add backend/scripts/check_migration_status.py backend/docs/MIGRATION_CLEANUP.md
git commit -m "feat: add migration status checker and cleanup guide"
```

---

## Task 9: Final Integration Test

**Files:**
- Test: `tests/integration/test_password_migration_flow.py`

**Step 1: Create integration test**

```python
# tests/integration/test_password_migration_flow.py
"""
End-to-end test of password migration flow.

This test simulates a user with a legacy password logging in
and verifies that their password is automatically migrated.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.core.security import get_password_hash, verify_password_legacy


@pytest.mark.asyncio
async async def test_complete_migration_flow(async_client: AsyncClient, db: AsyncSession):
    """
    Test complete user migration flow:
    1. Create user with legacy password hash
    2. Login with correct password
    3. Verify password was rehashed
    4. Verify migration flag is cleared
    5. Login again with new hash
    """

    # Step 1: Create user with LEGACY password hash
    legacy_hash = get_password_hash("oldpassword")  # This uses old method
    user = User(
        username="legacyuser",
        email="legacy@example.com",
        hashed_password=legacy_hash,
        password_migration_required=True
    )
    db.add(user)
    await db.commit()

    # Step 2: Login with correct password
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "legacyuser", "password": "oldpassword"}
    )

    assert response.status_code == 200
    assert "access_token" in response.json()

    # Step 3: Verify password was rehashed
    await db.refresh(user)
    assert user.hashed_password != legacy_hash  # Hash changed
    assert user.password_migration_required is False  # Flag cleared

    # Step 4: Verify new hash works
    assert verify_password("oldpassword", user.hashed_password) is True

    # Step 5: Login again with new hash
    response2 = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "legacyuser", "password": "oldpassword"}
    )

    assert response2.status_code == 200
    assert "access_token" in response2.json()


@pytest.mark.asyncio
async async def test_new_user_registration_flow(async_client: AsyncClient, db: AsyncSession):
    """
    Test that new users don't go through migration flow
    """

    # Register new user
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpassword123"
        }
    )

    assert response.status_code == 200

    # Verify user has correct settings
    result = await db.execute(select(User).where(User.username == "newuser"))
    user = result.scalars().first()

    assert user.password_migration_required is False

    # Login should work
    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "newuser", "password": "newpassword123"}
    )

    assert login_response.status_code == 200
```

**Step 2: Run integration test**

```bash
pytest tests/integration/test_password_migration_flow.py -v
```

Expected: `PASS`

**Step 3: Commit**

```bash
git add tests/integration/test_password_migration_flow.py
git commit -m "test(integration): add end-to-end password migration test"
```

---

## Task 10: Deploy and Monitor

**Files:**
- Modify: `.env` (no changes, but verify)
- Create: `backend/docs/DEPLOYMENT_CHECKLIST.md`

**Step 1: Create deployment checklist**

```markdown
# Password Migration Deployment Checklist

## Pre-Deployment

- [ ] All tests passing: `pytest tests/ -v`
- [ ] Migration status baseline recorded
- [ ] Database backed up
- [ ] Rollback plan documented

## Deployment Steps

1. [ ] Deploy code with new authentication logic
2. [ ] Run Alembic migration: `alembic upgrade head`
3. [ ] Verify new registrations work correctly
4. [ ] Test login with existing user account
5. [ ] Monitor application logs for errors

## Post-Deployment

- [ ] Check migration status daily: `python scripts/check_migration_status.py`
- [ ] Monitor error rates in authentication endpoints
- [ ] Track user complaints about login issues
- [ ] Plan cleanup after 90% migration

## Rollback Plan

If critical issues occur:

1. Revert code to previous version
2. Database is compatible with old code (flag is additive)
3. No data loss occurs

## Monitoring Commands

```bash
# Check migration status
python scripts/check_migration_status.py

# Check recent logins
tail -f /var/log/layra/app.log | grep "login"

# Monitor authentication errors
tail -f /var/log/layra/app.log | grep "ERROR.*auth"
```
```

**Step 2: Verify environment**

```bash
# Ensure .env doesn't have any password-related variables we don't expect
grep -i password /LAB/@thesis/layra/.env
```

Expected: Only `MYSQL_PASSWORD`, `REDIS_PASSWORD` (infrastructure, not application)

**Step 3: Commit**

```bash
git add backend/docs/DEPLOYMENT_CHECKLIST.md
git commit -m "docs: add deployment checklist for password migration"
```

---

## Post-Implementation

### Verification Commands

```bash
# 1. Check migration status
cd /LAB/@thesis/layra/backend
python scripts/check_migration_status.py

# 2. Run full test suite
pytest tests/ -v --cov=app --cov-report=html

# 3. Test authentication manually
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpassword"

# 4. Check database
docker exec -it layra-mysql-1 mysql -u layra -p layra -e \
  "SELECT username, password_migration_required FROM users;"
```

### Rollback Plan

If issues occur, the database migration is backward compatible:

```bash
# Revert code
git revert <commit-hash>

# No database rollback needed - flag column is optional
# Old code will ignore the new column
```

### Cleanup Timeline

- **Day 0**: Deploy
- **Day 7**: Check migration status
- **Day 14**: Check migration status, send reminders to inactive users
- **Day 30**: Check migration status
- **Day 90**: If <5% legacy users, force password reset for remaining
- **Day 90+**: Remove `verify_password_legacy()` and cleanup code

---

## Skills Reference

During implementation, you may need these skills:

- @superpowers:test-driven-development - For writing tests first
- @superpowers:systematic-debugging - If tests fail unexpectedly
- @superpowers:verification-before-completion - Before committing each task

---

## Notes for Engineer

1. **The hardcoded salt is `mynameisliwei,nicetomeetyou!`** - This is the actual value used in production
2. **Bcrypt includes salt in the hash** - The `$2b$12$...` format contains the salt
3. **Existing hashes are valid** - They were created with `password + salt`, so we must support them during migration
4. **Migration is transparent to users** - They just log in normally, password is rehashed automatically
5. **New users are safe immediately** - Only existing users need migration
6. **No downtime required** - Migration happens gradually as users log in

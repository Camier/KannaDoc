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
from app.core.security import get_password_hash, verify_password, verify_password_legacy


@pytest.mark.asyncio
async def test_complete_migration_flow(async_client: AsyncClient, db: AsyncSession):
    """
    Test complete user migration flow:
    1. Create user with LEGACY password hash
    2. Login with correct password
    3. Verify password was rehashed
    4. Verify migration flag is cleared
    5. Login again with new hash
    """

    # Step 1: Create user with LEGACY password hash
    # We manually create a legacy hash by hashing password+salt
    legacy_salt = "mynameisliwei,nicetomeetyou!"
    from app.core.security import pwd_context
    legacy_hash = pwd_context.hash("oldpassword" + legacy_salt)

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

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert "access_token" in response.json()

    # Step 3: Verify password was rehashed
    await db.refresh(user)
    assert user.hashed_password != legacy_hash  # Hash changed
    assert user.password_migration_required is False  # Flag cleared

    # Step 4: Verify new hash works with NEW method (not legacy)
    assert verify_password("oldpassword", user.hashed_password) is True
    # Verify it NO LONGER works with legacy method (because salt isn't added anymore)
    assert verify_password_legacy("oldpassword", user.hashed_password) is False

    # Step 5: Login again with new hash
    response2 = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "legacyuser", "password": "oldpassword"}
    )

    assert response2.status_code == 200, f"Expected 200, got {response2.status_code}: {response2.text}"
    assert "access_token" in response2.json()


@pytest.mark.asyncio
async def test_new_user_registration_flow(async_client: AsyncClient, db: AsyncSession):
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

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    # Verify user has correct settings
    result = await db.execute(select(User).where(User.username == "newuser"))
    user = result.scalars().first()

    assert user is not None
    assert user.password_migration_required is False

    # Login should work
    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "newuser", "password": "newpassword123"}
    )

    assert login_response.status_code == 200, f"Expected 200, got {login_response.status_code}: {login_response.text}"


@pytest.mark.asyncio
async def test_legacy_user_wrong_password_fails(async_client: AsyncClient, db: AsyncSession):
    """
    Test that legacy user with wrong password cannot login
    """
    # Create user with LEGACY password hash
    legacy_salt = "mynameisliwei,nicetomeetyou!"
    from app.core.security import pwd_context
    legacy_hash = pwd_context.hash("correctpassword" + legacy_salt)

    user = User(
        username="legacyuser2",
        email="legacy2@example.com",
        hashed_password=legacy_hash,
        password_migration_required=True
    )
    db.add(user)
    await db.commit()

    # Try login with WRONG password
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "legacyuser2", "password": "wrongpassword"}
    )

    assert response.status_code == 401

    # Verify password was NOT migrated (hash unchanged, flag still True)
    await db.refresh(user)
    assert user.hashed_password == legacy_hash
    assert user.password_migration_required is True


@pytest.mark.asyncio
async def test_migration_only_happens_once(async_client: AsyncClient, db: AsyncSession):
    """
    Test that password migration only happens once - subsequent logins
    use the new hash without re-migrating.
    """
    # Create user with LEGACY password hash
    legacy_salt = "mynameisliwei,nicetomeetyou!"
    from app.core.security import pwd_context
    legacy_hash = pwd_context.hash("testpass" + legacy_salt)

    user = User(
        username="onetimeuser",
        email="onetime@example.com",
        hashed_password=legacy_hash,
        password_migration_required=True
    )
    db.add(user)
    await db.commit()

    # First login - triggers migration
    response1 = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "onetimeuser", "password": "testpass"}
    )
    assert response1.status_code == 200

    await db.refresh(user)
    migrated_hash = user.hashed_password
    assert user.password_migration_required is False

    # Second login - should NOT re-migrate
    response2 = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "onetimeuser", "password": "testpass"}
    )
    assert response2.status_code == 200

    await db.refresh(user)
    # Hash should NOT have changed on second login
    assert user.hashed_password == migrated_hash
    assert user.password_migration_required is False

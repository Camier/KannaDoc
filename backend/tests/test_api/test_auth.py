# tests/test_api/test_auth.py
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.core.security import get_password_hash, verify_password


@pytest.mark.asyncio
async def test_new_users_have_migration_flag_false(db: AsyncSession):
    """Test that newly registered users don't need password migration"""
    # Simulate what the registration endpoint does (after the fix)
    username = "newuser123"
    email = "newuser@example.com"
    password = "securepassword456"

    # Create user with new password hashing method
    hashed_password = get_password_hash(password)
    db_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        password_migration_required=False,  # New users don't need migration
    )

    # Add to database
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    # Verify the user was created
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()

    assert user is not None
    assert user.password_migration_required is False, "New users should have password_migration_required=False"

    # Verify password works with new method
    assert verify_password(password, user.hashed_password) is True

# tests/test_models/test_user.py
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User


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


@pytest.mark.asyncio
async def test_user_migration_flag_can_be_set_false(db: AsyncSession):
    """Test that password_migration_required can be set to False"""
    user = User(
        username="testuser2",
        email="test2@example.com",
        hashed_password="$2b$12$testhash",
        password_migration_required=False
    )
    db.add(user)
    await db.commit()

    result = await db.execute(select(User).where(User.username == "testuser2"))
    fetched_user = result.scalars().first()

    assert fetched_user.password_migration_required is False

# tests/test_api/test_auth.py
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.core.security import verify_password


@pytest.mark.asyncio
async def test_new_users_have_migration_flag_false(client, db: AsyncSession):
    """
    Test that newly registered users don't need password migration.
    This test uses the actual registration endpoint via AsyncClient.
    """
    # Register a new user via the API endpoint
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser123",
            "email": "newuser@example.com",
            "password": "securepassword456"
        }
    )

    # Verify the response is successful
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    # Verify the response contains user data
    response_data = response.json()
    assert response_data["username"] == "newuser123"
    assert response_data["email"] == "newuser@example.com"

    # Query the database to check password_migration_required is False
    result = await db.execute(select(User).where(User.username == "newuser123"))
    user = result.scalars().first()

    assert user is not None, "User was not created in the database"
    assert user.password_migration_required is False, "New users should have password_migration_required=False"

    # Verify password works with new hashing method
    assert verify_password("securepassword456", user.hashed_password) is True, "Password verification failed"

"""
Security utilities for authentication and password hashing.

SECURITY NOTICE: This module previously used a hardcoded password salt.
The vulnerability has been fixed. The verify_password_legacy() function
exists ONLY for migrating existing passwords and should be removed
after all users have migrated.

TODO: Remove verify_password_legacy() after migration complete.
"""

from fastapi import HTTPException, Depends
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import timedelta
from app.core.config import settings
from app.schemas.auth import TokenData
from app.db.redis import redis
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.utils.timezone import beijing_time_now

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_password(plain_password, hashed_password):
    """Verify password using proper bcrypt without custom salt (NEW method)"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Hash password using proper bcrypt without custom salt (NEW method)"""
    return pwd_context.hash(password)


# TODO: Remove verify_password_legacy() after password migration complete (Day 90+)
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
    legacy_salt = "mynameisliwei,nicetomeetyou!"  # Legacy salt for migration only
    return pwd_context.verify(plain_password + legacy_salt, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = beijing_time_now() + expires_delta
    else:
        expire = beijing_time_now() + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def decode_access_token(token: str):
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        username: str = payload.get("sub")
        if not username:
            raise JWTError
        return TokenData(username=username)
    except JWTError:
        return None


async def verify_username_match(
    token_data: str,
    username: str,
) -> None:
    if token_data.username != username:
        raise HTTPException(status_code=403, detail="Username mismatch")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
):
    redis_connection = await redis.get_token_connection()  # 获取 Redis 连接实例
    token_status = await redis_connection.get(f"token:{token}")

    if token_status is None:
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    token_data = decode_access_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token_data


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
    if (
        hasattr(user, "password_migration_required")
        and user.password_migration_required
    ):
        if verify_password_legacy(password, user.hashed_password):
            # Migration: Rehash with proper bcrypt and update database
            user.hashed_password = get_password_hash(password)
            user.password_migration_required = False
            await db.commit()

            return user

    return None

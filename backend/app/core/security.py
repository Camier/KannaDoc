"""
Security utilities for authentication and password hashing.

This module provides centralized authentication and authorization functionality.

MIGRATION NOTICE: The verify_password_legacy() function exists for migrating
existing passwords from the old hardcoded salt to proper bcrypt. After all users
have migrated (password_migration_required=False), this function should be removed.

DEADLINE: 2026-02-23 - Remove verify_password_legacy() after password migration complete.
"""

from fastapi import HTTPException, Depends, status
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import timedelta
from typing import Optional

from app.core.config import settings
from app.schemas.auth import TokenData
from app.db.redis import redis
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.utils.timezone import beijing_time_now


# =============================================================================
# PASSWORD HASHING
# =============================================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using proper bcrypt (NEW method)."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password using proper bcrypt (NEW method)."""
    return pwd_context.hash(password)


# DEADLINE: 2026-02-23 - Remove after password migration complete
def verify_password_legacy(plain_password: str, hashed_password: str) -> bool:
    """
    Legacy password verification for passwords hashed with custom salt.

    SECURITY WARNING: This function contains a hardcoded salt for migration ONLY.
    After all users have migrated to proper bcrypt, this function MUST be removed.
    """
    legacy_salt = "mynameisliwei,nicetomeetyou!"  # Legacy salt for migration only
    return pwd_context.verify(plain_password + legacy_salt, hashed_password)


# =============================================================================
# JWT TOKEN MANAGEMENT
# =============================================================================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = beijing_time_now() + expires_delta
    else:
        expire = beijing_time_now() + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def _decode_jwt(token: str) -> Optional[TokenData]:
    """Internal: Decode JWT and return TokenData or None on error."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if not username:
            return None
        return TokenData(username=username)
    except JWTError:
        return None


# =============================================================================
# AUTHENTICATION (Token Validation)
# =============================================================================

class AuthErrors:
    """Centralized authentication error messages and status codes."""
    INVALID_TOKEN = (
        status.HTTP_401_UNAUTHORIZED,
        "Invalid or expired token"
    )
    TOKEN_NOT_FOUND = (
        status.HTTP_401_UNAUTHORIZED,
        "Token not found or expired"
    )
    USERNAME_MISMATCH = (
        status.HTTP_403_FORBIDDEN,
        "Access denied: username mismatch"
    )
    INVALID_CREDENTIALS = (
        status.HTTP_401_UNAUTHORIZED,
        "Incorrect username or password"
    )


async def validate_token(token: str) -> TokenData:
    """
    Unified token validation: checks Redis then decodes JWT.

    Raises:
        HTTPException: 401 if token is invalid/expired

    Returns:
        TokenData: The validated token data
    """
    redis_connection = await redis.get_token_connection()
    token_exists = await redis_connection.get(f"token:{token}")

    if token_exists is None:
        raise HTTPException(
            status_code=AuthErrors.TOKEN_NOT_FOUND[0],
            detail=AuthErrors.TOKEN_NOT_FOUND[1],
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = _decode_jwt(token)
    if not token_data:
        # Clean up invalid token from Redis
        await redis_connection.delete(f"token:{token}")
        raise HTTPException(
            status_code=AuthErrors.INVALID_TOKEN[0],
            detail=AuthErrors.INVALID_TOKEN[1],
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_data


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """
    FastAPI dependency to get the current authenticated user from token.

    Raises:
        HTTPException: 401 if token is invalid/expired

    Returns:
        TokenData: The authenticated user's token data
    """
    return await validate_token(token)


# =============================================================================
# AUTHORIZATION (Username Verification)
# =============================================================================

async def verify_username_match(
    token_data: TokenData,
    username: str,
) -> None:
    """
    Verify that the authenticated user matches the requested username.

    In single-tenant mode, all users can access all resources.
    In multi-tenant mode, users can only access their own resources.

    Raises:
        HTTPException: 403 if username doesn't match

    Args:
        token_data: The validated token data
        username: The username being accessed
    """
    if settings.single_tenant_mode:
        return

    if token_data.username != username:
        raise HTTPException(
            status_code=AuthErrors.USERNAME_MISMATCH[0],
            detail=AuthErrors.USERNAME_MISMATCH[1],
        )


def require_username(username_param: str = "username"):
    """
    Dependency factory for endpoint-level username verification.

    Usage:
        @router.get("/users/{username}/data")
        async def get_user_data(
            username: str,
            current_user: TokenData = Depends(get_current_user),
            _auth: None = Depends(require_username()),
        ):
            # Endpoint logic here

    Args:
        username_param: The path parameter name containing the username

    Returns:
        A dependency function that verifies username match
    """
    async def _verify(
        current_user: TokenData = Depends(get_current_user),
        **kwargs
    ):
        requested_username = kwargs.get(username_param)
        if requested_username:
            await verify_username_match(current_user, requested_username)
        return None

    return _verify


# =============================================================================
# USER AUTHENTICATION (Password Verification)
# =============================================================================

async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str
) -> Optional[User]:
    """
    Authenticate a user and migrate legacy passwords if needed.

    Legacy passwords (created with hardcoded salt) will be automatically
    rehashed using proper bcrypt on successful authentication.

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

    # Try NEW method first (proper bcrypt)
    if verify_password(password, user.hashed_password):
        return user

    # Try LEGACY method (hardcoded salt) for migration
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


# =============================================================================
# TOKEN STORAGE (Redis Integration)
# =============================================================================

async def store_token(token: str, username: str, expires_in_seconds: int) -> None:
    """
    Store a token in Redis for validation and revocation.

    Args:
        token: The JWT token
        username: The username associated with the token
        expires_in_seconds: Token expiration time in seconds
    """
    redis_connection = await redis.get_token_connection()
    await redis_connection.set(
        f"token:{token}",
        username,
        ex=expires_in_seconds,
    )
    # Also store reverse lookup for user management
    await redis_connection.set(
        f"user:{username}",
        token,
        ex=expires_in_seconds,
    )


async def revoke_token(token: str) -> None:
    """
    Revoke a token by removing it from Redis.

    Args:
        token: The JWT token to revoke
    """
    redis_connection = await redis.get_token_connection()
    username = await redis_connection.get(f"token:{token}")
    if username:
        await redis_connection.delete(f"token:{token}")
        await redis_connection.delete(f"user:{username}")


async def revoke_user_tokens(username: str) -> None:
    """
    Revoke all tokens for a specific user.

    Args:
        username: The username whose tokens should be revoked
    """
    redis_connection = await redis.get_token_connection()
    token = await redis_connection.get(f"user:{username}")
    if token:
        await redis_connection.delete(f"token:{token}")
        await redis_connection.delete(f"user:{username}")

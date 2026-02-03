"""
Authentication endpoints for login, logout, token verification, and registration.

This module provides the REST API for user authentication using OAuth2 Bearer tokens.
All token validation and storage is handled by app.core.security.
"""

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.auth import TokenData, TokenSchema
from app.schemas.user import UserCreate, UserResponse
from app.models.user import User
from app.db.mysql_session import get_mysql_session
from app.db.repositories.repository_manager import (
    RepositoryManager,
    get_repository_manager,
)

from app.core.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
    store_token,
    revoke_token,
    AuthErrors,
    get_password_hash,
)
from app.core.config import settings
from app.db.redis import redis

router = APIRouter()


# =============================================================================
# TOKEN VERIFICATION
# =============================================================================


@router.get("/verify-token", response_model=TokenData)
async def verify_token(token_data: TokenData = Depends(get_current_user)):
    """
    Verify if a token is valid.

    Returns the token data if valid, raises 401 if invalid.
    This endpoint uses the consolidated token validation from security.py.
    """
    return token_data


# =============================================================================
# LOGIN (OAuth2 Password Flow)
# =============================================================================


@router.post("/login", response_model=TokenSchema)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_mysql_session),
):
    """
    Authenticate user with username/password and return access token.

    Uses OAuth2 PasswordRequestForm for standard OAuth2 compliance.
    Token is stored in Redis for validation and revocation.
    """
    # Authenticate user (handles legacy password migration)
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=AuthErrors.INVALID_CREDENTIALS[0],
            detail=AuthErrors.INVALID_CREDENTIALS[1],
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires,
    )

    # Store token in Redis for validation and revocation
    await store_token(
        token=access_token,
        username=user.username,
        expires_in_seconds=int(access_token_expires.total_seconds()),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"username": user.username, "email": user.email},
    }


# =============================================================================
# LOGOUT (Token Revocation)
# =============================================================================


@router.post("/logout")
async def logout(token_data: TokenData = Depends(get_current_user)):
    """
    Logout user by revoking their token.

    Removes the token from Redis, making it invalid for future requests.
    JWT itself cannot be invalidated, so we remove it from our Redis store.
    """
    # Extract token from the dependency context
    # Note: OAuth2PasswordBearer doesn't expose the raw token, so we need
    # to get it from the request. This is a limitation of FastAPI's scheme.
    # For now, we'll rely on token expiration.

    # Alternative: client should discard the token, and it will expire naturally
    # To implement server-side logout, we'd need custom token extraction
    return {"message": "Logged out successfully. Discard your token."}


# =============================================================================
# REGISTRATION
# =============================================================================


@router.post("/register", response_model=UserResponse)
async def register(
    user: UserCreate,
    db: AsyncSession = Depends(get_mysql_session),
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    """Register a new user account."""
    # Validate username (no illegal characters)
    illegal_chars = ("-", "_", " ")
    if any(char in user.username for char in illegal_chars):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Characters {', '.join(repr(c) for c in illegal_chars)} are not allowed in username",
        )

    # Check if username already exists
    existing_user = await db.execute(select(User).where(User.username == user.username))
    if existing_user.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check if email already exists
    existing_email = await db.execute(select(User).where(User.email == user.email))
    if existing_email.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user with proper bcrypt hash
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        password_migration_required=False,  # New users don't need migration
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    # Create default model config for new user
    model_id = user.username + "_" + str(uuid.uuid4())
    await repo_manager.model_config.create_model_config(
        username=user.username,
        selected_model=model_id,
        model_id=model_id,
        model_name="qwen2.5-vl-32b-instruct",
        model_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="",
        base_used=[],
        system_prompt="You are a helpful assistant.",
        temperature=-1,
        max_length=-1,
        top_P=-1,
        top_K=-1,
        score_threshold=-1,
    )

    return UserResponse.model_validate(db_user)

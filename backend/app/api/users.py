"""User management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.user_settings import UserSettings
from app.services.encryption import EncryptionService

router = APIRouter(prefix="/users", tags=["users"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class UserCreate(BaseModel):
    """Schema for creating a new user (called after Auth.js login)."""
    email: EmailStr
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    github_id: Optional[str] = None


class UserResponse(BaseModel):
    """Public user information (safe to return in API responses)."""
    id: str  # UUID as string
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    github_id: Optional[str]

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    """Schema for updating user settings (API keys)."""
    fly_api_token: Optional[str] = None
    openrouter_api_key: Optional[str] = None


class UserSettingsResponse(BaseModel):
    """Public user settings (NEVER returns actual API keys)."""
    has_fly_api_token: bool
    has_openrouter_api_key: bool

    model_config = {"from_attributes": True}


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Create or update user after Auth.js login.

    Called by frontend after successful GitHub OAuth:
    1. Frontend gets JWT from Auth.js
    2. Frontend calls this endpoint with user info
    3. Backend creates/updates user in database
    4. Backend returns user data

    If user already exists (by email), updates their info.
    If user doesn't exist, creates new user + empty settings.

    Args:
        user_data: User information from Auth.js
        db: Database session

    Returns:
        UserResponse: Created or updated user
    """
    # Check if user exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    user = result.scalar_one_or_none()

    if user:
        # Update existing user
        user.name = user_data.name
        user.avatar_url = user_data.avatar_url
        user.github_id = user_data.github_id
    else:
        # Create new user
        user = User(
            email=user_data.email,
            name=user_data.name,
            avatar_url=user_data.avatar_url,
            github_id=user_data.github_id
        )
        db.add(user)

        # Flush to get user.id for settings
        await db.flush()

        # Create empty settings for new user
        settings = UserSettings(user_id=user.id)
        db.add(settings)

    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Get current authenticated user's information.

    Requires: Authorization header with valid JWT token.

    Returns:
        UserResponse: Current user's public info
    """
    return UserResponse.model_validate(user)


@router.get("/me/settings", response_model=UserSettingsResponse)
async def get_user_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserSettingsResponse:
    """
    Get current user's settings (shows which API keys are configured).

    NEVER returns actual API key values (security).
    Only returns boolean flags indicating if keys are set.

    Requires: Authorization header with valid JWT token.

    Returns:
        UserSettingsResponse: Which API keys are configured
    """
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        # Create empty settings if missing
        settings = UserSettings(user_id=user.id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return UserSettingsResponse(
        has_fly_api_token=bool(settings.encrypted_fly_api_token),
        has_openrouter_api_key=bool(settings.encrypted_openrouter_api_key)
    )


@router.put("/me/settings", response_model=UserSettingsResponse)
async def update_user_settings(
    settings_data: UserSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserSettingsResponse:
    """
    Update current user's API keys.

    API keys are encrypted with Fernet before storage.
    Only updates keys that are provided (null values are ignored).

    Requires: Authorization header with valid JWT token.

    Args:
        settings_data: New API keys to store
        user: Current authenticated user
        db: Database session

    Returns:
        UserSettingsResponse: Updated settings status
    """
    # Get or create settings
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        settings = UserSettings(user_id=user.id)
        db.add(settings)

    # Encrypt and update API keys (only if provided)
    encryption = EncryptionService()

    if settings_data.fly_api_token is not None:
        if settings_data.fly_api_token.strip():
            settings.encrypted_fly_api_token = encryption.encrypt(
                settings_data.fly_api_token
            )
        else:
            # Empty string = delete key
            settings.encrypted_fly_api_token = None

    if settings_data.openrouter_api_key is not None:
        if settings_data.openrouter_api_key.strip():
            settings.encrypted_openrouter_api_key = encryption.encrypt(
                settings_data.openrouter_api_key
            )
        else:
            # Empty string = delete key
            settings.encrypted_openrouter_api_key = None

    await db.commit()
    await db.refresh(settings)

    return UserSettingsResponse(
        has_fly_api_token=bool(settings.encrypted_fly_api_token),
        has_openrouter_api_key=bool(settings.encrypted_openrouter_api_key)
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete current user's account.

    WARNING: This is permanent! Deletes:
    - User record
    - User settings (API keys)
    - All deployments (cascade delete)
    - All credentials (cascade delete)

    Requires: Authorization header with valid JWT token.
    """
    await db.delete(user)
    await db.commit()
    return None

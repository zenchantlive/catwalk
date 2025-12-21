"""User settings API endpoints for managing API keys."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.user_settings import UserSettings
from app.middleware.auth import get_current_user
from app.services.encryption import EncryptionService

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsRequest(BaseModel):
    """Request model for updating user settings."""
    fly_api_token: str | None = None
    openrouter_api_key: str | None = None


class SettingsResponse(BaseModel):
    """Response model for user settings (decrypted)."""
    fly_api_token: str | None
    openrouter_api_key: str | None
    has_fly_token: bool
    has_openrouter_key: bool
    updated_at: datetime


@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user's settings with decrypted API keys.

    Requires authentication via JWT token.

    Returns:
        SettingsResponse: User's API keys (decrypted)
    """
    # Fetch user settings
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        # Return empty settings if user hasn't saved any yet
        return SettingsResponse(
            fly_api_token=None,
            openrouter_api_key=None,
            has_fly_token=False,
            has_openrouter_key=False,
            updated_at=datetime.utcnow(),
        )

    # Decrypt API keys
    encryption_service = EncryptionService()

    fly_token = None
    if settings.encrypted_fly_api_token:
        try:
            fly_token = encryption_service.decrypt(settings.encrypted_fly_api_token)
        except Exception:
            # If decryption fails, treat as None
            pass

    openrouter_key = None
    if settings.encrypted_openrouter_api_key:
        try:
            openrouter_key = encryption_service.decrypt(settings.encrypted_openrouter_api_key)
        except Exception:
            # If decryption fails, treat as None
            pass

    return SettingsResponse(
        fly_api_token=fly_token,
        openrouter_api_key=openrouter_key,
        has_fly_token=bool(settings.encrypted_fly_api_token),
        has_openrouter_key=bool(settings.encrypted_openrouter_api_key),
        updated_at=settings.updated_at,
    )


@router.post("", response_model=SettingsResponse)
async def update_settings(
    settings_data: SettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update user's API keys (encrypted before storage).

    Requires authentication via JWT token.

    Args:
        settings_data: API keys to save
        current_user: Authenticated user
        db: Database session

    Returns:
        SettingsResponse: Updated settings (with decrypted keys)
    """
    # Fetch existing settings or create new
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    encryption_service = EncryptionService()

    if not settings:
        # Create new settings
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)

    # Update API keys (encrypt before storage)
    if settings_data.fly_api_token is not None:
        if settings_data.fly_api_token.strip():
            settings.encrypted_fly_api_token = encryption_service.encrypt(
                settings_data.fly_api_token.strip()
            )
        else:
            # Empty string means remove the key
            settings.encrypted_fly_api_token = None

    if settings_data.openrouter_api_key is not None:
        if settings_data.openrouter_api_key.strip():
            settings.encrypted_openrouter_api_key = encryption_service.encrypt(
                settings_data.openrouter_api_key.strip()
            )
        else:
            # Empty string means remove the key
            settings.encrypted_openrouter_api_key = None

    settings.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(settings)

    # Return decrypted settings
    return SettingsResponse(
        fly_api_token=settings_data.fly_api_token,
        openrouter_api_key=settings_data.openrouter_api_key,
        has_fly_token=bool(settings.encrypted_fly_api_token),
        has_openrouter_key=bool(settings.encrypted_openrouter_api_key),
        updated_at=settings.updated_at,
    )


@router.delete("")
async def delete_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete all user settings (remove all API keys).

    Requires authentication via JWT token.

    Returns:
        dict: Success message
    """
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    if settings:
        await db.delete(settings)
        await db.commit()

    return {"message": "Settings deleted successfully"}

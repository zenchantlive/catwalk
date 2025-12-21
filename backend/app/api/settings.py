"""User settings API endpoints for managing API keys."""
from datetime import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.user_settings import UserSettings
from app.core.auth import get_current_user
from app.services.encryption import EncryptionService, get_encryption_service

router = APIRouter(prefix="/settings", tags=["settings"])
logger = logging.getLogger(__name__)


class SettingsRequest(BaseModel):
    """Request model for updating user settings."""
    fly_api_token: str | None = None
    openrouter_api_key: str | None = None


class SettingsResponse(BaseModel):
    """Response model for user settings (secrets are masked)."""
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
        from datetime import timezone
        return SettingsResponse(
            fly_api_token=None,
            openrouter_api_key=None,
            has_fly_token=False,
            has_openrouter_key=False,
            updated_at=datetime.now(timezone.utc),
        )

    # Decrypt API keys (for internal use if needed, but we won't return them)
    # We only return flags indicating if they exist
    
    return SettingsResponse(
        fly_api_token=None,  # NEVER return decrypted secrets
        openrouter_api_key=None,
        has_fly_token=bool(settings.encrypted_fly_api_token),
        has_openrouter_key=bool(settings.encrypted_openrouter_api_key),
        updated_at=settings.updated_at,
    )


@router.post("", response_model=SettingsResponse)
async def update_settings(
    settings_data: SettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    encryption_service: EncryptionService = Depends(get_encryption_service),
):
    """
    Update user's API keys (encrypted before storage).

    Requires authentication via JWT token.

    Args:
        settings_data: API keys to save
        current_user: Authenticated user
        db: Database session

    Returns:
        SettingsResponse: Updated settings status (secrets masked)
    """
    # Fetch existing settings or create new
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

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

    # updated_at is automatically handled by database onupdate=func.now()
    logger.info("[AUDIT] settings_update user_id=%s", current_user.id)

    await db.commit()
    await db.refresh(settings)

    # Return masked settings
    return SettingsResponse(
        fly_api_token=None,
        openrouter_api_key=None,
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

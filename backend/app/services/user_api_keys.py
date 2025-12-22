"""Helper service for fetching and decrypting user API keys."""
import logging
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.models.user_settings import UserSettings
from app.services.encryption import EncryptionService, get_encryption_service
from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_user_api_keys(
    user_id: uuid.UUID,
    db: AsyncSession,
    encryption_service: EncryptionService | None = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch and decrypt user's API keys from UserSettings.
    
    Args:
        user_id: The user's UUID
        db: Database session
        encryption_service: Optional encryption service (will create if not provided)
    
    Returns:
        Tuple of (fly_api_token, openrouter_api_key)
        Returns (None, None) if user has no settings
    
    Raises:
        Exception: If decryption fails
    """
    if encryption_service is None:
        encryption_service = get_encryption_service()
    
    # Fetch user settings
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    user_settings = result.scalar_one_or_none()
    
    if not user_settings:
        logger.debug(f"No UserSettings found for user {user_id}")
        return None, None
    
    # Decrypt API keys if they exist
    fly_token = None
    openrouter_key = None
    
    try:
        if user_settings.encrypted_fly_api_token:
            fly_token = encryption_service.decrypt(user_settings.encrypted_fly_api_token)
            logger.debug(f"Decrypted Fly.io token for user {user_id}")
        
        if user_settings.encrypted_openrouter_api_key:
            openrouter_key = encryption_service.decrypt(user_settings.encrypted_openrouter_api_key)
            logger.debug(f"Decrypted OpenRouter key for user {user_id}")
    
    except Exception as e:
        logger.error(f"Failed to decrypt API keys for user {user_id}: {str(e)}")
        raise Exception("Failed to decrypt user API keys. Please re-save your settings.")
    
    return fly_token, openrouter_key


async def get_effective_api_keys(
    user_id: uuid.UUID,
    db: AsyncSession,
    encryption_service: EncryptionService | None = None,
    require_user_keys: bool = False
) -> Tuple[Optional[str], Optional[str]]:
    """
    Get effective API keys with fallback to system-level settings.
    
    Priority:
    1. User's keys from UserSettings (if set)
    2. System-level keys from environment variables (fallback)
    
    Args:
        user_id: The user's UUID
        db: Database session
        encryption_service: Optional encryption service
        require_user_keys: If True, don't fallback to system keys (raise error instead)
    
    Returns:
        Tuple of (fly_api_token, openrouter_api_key)
    
    Raises:
        ValueError: If require_user_keys=True and user hasn't provided keys
    """
    # Try to get user-specific keys
    user_fly_token, user_openrouter_key = await get_user_api_keys(
        user_id=user_id,
        db=db,
        encryption_service=encryption_service
    )
    
    # Determine effective keys with fallback
    effective_fly_token = user_fly_token or settings.FLY_API_TOKEN
    effective_openrouter_key = user_openrouter_key or settings.OPENROUTER_API_KEY
    
    # If requiring user keys, validate they provided them
    if require_user_keys:
        missing_keys = []
        if not user_fly_token:
            missing_keys.append("Fly.io API Token")
        if not user_openrouter_key:
            missing_keys.append("OpenRouter API Key")
        
        if missing_keys:
            raise ValueError(
                f"Missing required API keys in your settings: {', '.join(missing_keys)}. "
                f"Please add them at /settings before creating deployments."
            )
    
    # Log which keys are being used
    fly_source = "user" if user_fly_token else "system"
    openrouter_source = "user" if user_openrouter_key else "system"
    logger.info(
        f"Using API keys for user {user_id}: "
        f"Fly.io={fly_source}, OpenRouter={openrouter_source}"
    )
    
    return effective_fly_token, effective_openrouter_key

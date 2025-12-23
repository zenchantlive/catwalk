import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.user_api_keys import get_user_api_keys, get_effective_api_keys
from app.models.user_settings import UserSettings
from app.core.config import settings

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def user_id():
    return uuid.uuid4()

@pytest.fixture
def mock_encryption_service():
    service = MagicMock()
    service.decrypt.side_effect = lambda x: x.replace("encrypted-", "")
    return service

@pytest.mark.asyncio
async def test_get_user_api_keys_success(mock_db, user_id, mock_encryption_service):
    """Test successful retrieval and decryption of user API keys."""
    mock_settings = UserSettings(
        user_id=user_id,
        encrypted_fly_api_token="encrypted-fly-token",
        encrypted_openrouter_api_key="encrypted-or-key"
    )
    
    # Mock database result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_settings
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    fly_token, or_key = await get_user_api_keys(
        user_id=user_id,
        db=mock_db,
        encryption_service=mock_encryption_service
    )
    
    assert fly_token == "fly-token"
    assert or_key == "or-key"
    mock_encryption_service.decrypt.assert_any_call("encrypted-fly-token")
    mock_encryption_service.decrypt.assert_any_call("encrypted-or-key")

@pytest.mark.asyncio
async def test_get_user_api_keys_none(mock_db, user_id, mock_encryption_service):
    """Test return (None, None) when no settings exist."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    fly_token, or_key = await get_user_api_keys(
        user_id=user_id, 
        db=mock_db,
        encryption_service=mock_encryption_service
    )
    
    assert fly_token is None
    assert or_key is None

@pytest.mark.asyncio
async def test_get_user_api_keys_decryption_failure(mock_db, user_id, mock_encryption_service):
    """Test exception when decryption fails."""
    mock_settings = UserSettings(
        user_id=user_id,
        encrypted_fly_api_token="bad-token"
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_settings
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    mock_encryption_service.decrypt.side_effect = Exception("Decryption failed")
    
    with pytest.raises(Exception, match="Failed to decrypt user API keys"):
        await get_user_api_keys(
            user_id=user_id,
            db=mock_db,
            encryption_service=mock_encryption_service
        )

@pytest.mark.asyncio
async def test_get_effective_api_keys_user_priority(mock_db, user_id, mock_encryption_service):
    """Test that user keys take precedence over system keys."""
    # Mock get_user_api_keys to return user-specific keys
    with patch("app.services.user_api_keys.get_user_api_keys", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = ("user-fly-token", "user-or-key")
        
        # System keys in settings (should be ignored)
        with patch.object(settings, "FLY_API_TOKEN", "system-fly"):
            with patch.object(settings, "OPENROUTER_API_KEY", "system-or"):
                fly_token, or_key = await get_effective_api_keys(
                    user_id=user_id,
                    db=mock_db,
                    encryption_service=mock_encryption_service
                )
                
                assert fly_token == "user-fly-token"
                assert or_key == "user-or-key"

@pytest.mark.asyncio
async def test_get_effective_api_keys_system_fallback(mock_db, user_id):
    """Test fallback to system keys when user keys are missing."""
    with patch("app.services.user_api_keys.get_user_api_keys", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = (None, None)
        
        with patch.object(settings, "FLY_API_TOKEN", "system-fly"):
            with patch.object(settings, "OPENROUTER_API_KEY", "system-or"):
                fly_token, or_key = await get_effective_api_keys(user_id=user_id, db=mock_db)
                
                assert fly_token == "system-fly"
                assert or_key == "system-or"

@pytest.mark.asyncio
async def test_get_effective_api_keys_required_fail(mock_db, user_id):
    """Test validation failure when user keys are required but missing."""
    with patch("app.services.user_api_keys.get_user_api_keys", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = (None, None)
        
        with pytest.raises(ValueError, match="Missing required API keys in your settings"):
            await get_effective_api_keys(
                user_id=user_id,
                db=mock_db,
                require_user_keys=True
            )

@pytest.mark.asyncio
async def test_get_user_api_keys_default_encryption(mock_db, user_id):
    """Test that it tries to get the default encryption service if none provided."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    with patch("app.services.user_api_keys.get_encryption_service") as mock_get_encryption:
        mock_service = MagicMock()
        mock_get_encryption.return_value = mock_service
        
        await get_user_api_keys(user_id=user_id, db=mock_db)
        mock_get_encryption.assert_called_once()

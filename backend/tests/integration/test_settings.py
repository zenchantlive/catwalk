import pytest
from httpx import AsyncClient
from app.models.user import User

@pytest.mark.asyncio
async def test_get_settings_empty(client: AsyncClient, auth_headers: dict, mock_user: User):
    """Test getting settings when none exist yet."""
    response = await client.get("/api/settings", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["has_fly_token"] is False
    assert data["has_openrouter_key"] is False

@pytest.mark.asyncio
async def test_update_settings(client: AsyncClient, auth_headers: dict, mock_user: User):
    """Test updating user settings with API keys."""
    settings_data = {
        "fly_api_token": "fly-test-token",
        "openrouter_api_key": "openrouter-test-key"
    }
    
    response = await client.post(
        "/api/settings",
        json=settings_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["has_fly_token"] is True
    assert data["has_openrouter_key"] is True
    # Secrets should NEVER be returned
    assert data["fly_api_token"] is None
    assert data["openrouter_api_key"] is None

@pytest.mark.asyncio
async def test_delete_settings(client: AsyncClient, auth_headers: dict, mock_user: User):
    """Test deleting user settings."""
    # First create them
    await client.post(
        "/api/settings",
        json={"fly_api_token": "test"},
        headers=auth_headers
    )
    
    # Then delete
    response = await client.delete("/api/settings", headers=auth_headers)
    assert response.status_code == 200
    
    # Verify they are gone
    get_response = await client.get("/api/settings", headers=auth_headers)
    assert get_response.json()["has_fly_token"] is False

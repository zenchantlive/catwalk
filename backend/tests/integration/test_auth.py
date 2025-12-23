import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User

@pytest.mark.asyncio
async def test_sync_user_new(client: AsyncClient, api_secret_header: dict):
    """Test creating a new user via sync-user endpoint."""
    user_data = {
        "email": "newuser@example.com",
        "name": "New User",
        "avatar_url": "https://example.com/avatar.png",
        "github_id": "999888"
    }
    
    response = await client.post(
        "/api/auth/sync-user",
        json=user_data,
        headers=api_secret_header
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["name"] == user_data["name"]
    assert "id" in data

@pytest.mark.asyncio
async def test_sync_user_update(client: AsyncClient, api_secret_header: dict, mock_user: User):
    """Test updating an existing user via sync-user endpoint."""
    user_data = {
        "email": mock_user.email,
        "name": "Updated Name",
        "avatar_url": mock_user.avatar_url,
        "github_id": mock_user.github_id
    }
    
    response = await client.post(
        "/api/auth/sync-user",
        json=user_data,
        headers=api_secret_header
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["id"] == str(mock_user.id)

@pytest.mark.asyncio
async def test_sync_user_invalid_secret(client: AsyncClient):
    """Test sync-user failure with invalid secret."""
    user_data = {"email": "test@example.com", "name": "Test"}
    response = await client.post(
        "/api/auth/sync-user",
        json=user_data,
        headers={"X-Auth-Secret": "wrong-secret"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient, auth_headers: dict, mock_user: User):
    """Test /auth/me for an authenticated user."""
    response = await client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == mock_user.email
    assert data["id"] == str(mock_user.id)

@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    """Test /auth/me failure for unauthenticated user."""
    # Note: In conftest we clear overrides, so by default it stays unauthenticated 
    # IF the middleware isn't mocked.
    response = await client.get("/api/auth/me")
    assert response.status_code == 401

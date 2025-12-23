import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from app.models.user import User

@pytest.mark.asyncio
async def test_registry_search(client: AsyncClient):
    """Test searching the Glama registry."""
    mock_servers = [
        {
            "id": "s1", 
            "name": "Server 1", 
            "namespace": "ai", 
            "description": "d1", 
            "version": "1.0.0",
            "capabilities": {"deployable": True, "connectable": True},
            "trust": {"is_official": True, "last_updated": "2023-01-01"}
        },
        {
            "id": "s2", 
            "name": "Server 2", 
            "namespace": "ai", 
            "description": "d2", 
            "version": "1.0.0",
            "capabilities": {"deployable": True, "connectable": True},
            "trust": {"is_official": False, "last_updated": "2023-01-01"}
        }
    ]
    
    with patch("app.api.registry.RegistryService.get_instance") as mock_get_instance:
        mock_service = AsyncMock()
        mock_get_instance.return_value = mock_service
        mock_service.search_servers.return_value = mock_servers
        
        response = await client.get("/api/registry/search?q=test")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "s1"

@pytest.mark.asyncio
async def test_registry_get_server(client: AsyncClient):
    """Test getting a specific server from registry."""
    mock_server = {
        "id": "s1", 
        "name": "Server 1", 
        "namespace": "ai", 
        "description": "d1", 
        "version": "1.0.0",
        "capabilities": {"deployable": True, "connectable": True},
        "trust": {"is_official": True, "last_updated": "2023-01-01"}
    }
    
    with patch("app.api.registry.RegistryService.get_instance") as mock_get_instance:
        mock_service = AsyncMock()
        mock_get_instance.return_value = mock_service
        mock_service.get_server.return_value = mock_server
        
        response = await client.get("/api/registry/s1")
        
        assert response.status_code == 200
        assert response.json()["id"] == "s1"

@pytest.mark.asyncio
async def test_registry_get_server_not_found(client: AsyncClient):
    """Test registry get server failure when not found."""
    with patch("app.api.registry.RegistryService.get_instance") as mock_get_instance:
        mock_service = AsyncMock()
        mock_get_instance.return_value = mock_service
        mock_service.get_server.return_value = None
        
        response = await client.get("/api/registry/nonexistent")
        
        assert response.status_code == 404

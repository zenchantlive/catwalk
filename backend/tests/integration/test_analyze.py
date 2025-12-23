import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from app.models.user import User
from app.services.analysis import AnalysisService

@pytest.mark.asyncio
async def test_analyze_repository_success(client: AsyncClient, auth_headers: dict, mock_user: User):
    """Test successful repository analysis with mocked service."""
    mock_result = {
        "name": "test-repo",
        "description": "A test repository",
        "env_vars": ["API_KEY"]
    }
    
    # Patch the AnalysisService.analyze_repo method
    with patch("app.api.analyze.AnalysisService.analyze_repo", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = mock_result
        
        response = await client.post(
            "/api/analyze",
            json={"repo_url": "https://github.com/test/test-repo"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"] == mock_result

@pytest.mark.asyncio
async def test_analyze_repository_cache_hit(client: AsyncClient, auth_headers: dict, mock_user: User):
    """Test that analysis uses cache on subsequent calls."""
    mock_result = {"name": "cached-repo"}
    
    with patch("app.api.analyze.AnalysisService.analyze_repo", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = mock_result
        
        # 1. First call - should hit the service
        await client.post(
            "/api/analyze",
            json={"repo_url": "https://github.com/test/cached-repo"},
            headers=auth_headers
        )
        assert mock_analyze.call_count == 1
        
        # 2. Second call - should hit cache
        response = await client.post(
            "/api/analyze",
            json={"repo_url": "https://github.com/test/cached-repo"},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert mock_analyze.call_count == 1 # Still 1
        assert response.json()["status"] == "cached"

@pytest.mark.asyncio
async def test_analyze_repository_force(client: AsyncClient, auth_headers: dict, mock_user: User):
    """Test that force=True bypasses cache."""
    mock_result = {"name": "force-repo"}
    
    with patch("app.api.analyze.AnalysisService.analyze_repo", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = mock_result
        
        # 1. First call
        await client.post(
            "/api/analyze",
            json={"repo_url": "https://github.com/test/force-repo"},
            headers=auth_headers
        )
        
        # 2. Second call with force=True
        response = await client.post(
            "/api/analyze",
            json={"repo_url": "https://github.com/test/force-repo", "force": True},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert mock_analyze.call_count == 2
        assert response.json()["status"] == "success"

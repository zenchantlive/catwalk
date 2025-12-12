from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.analyze import get_analysis_service, get_cache_service

client = TestClient(app)

@pytest.mark.asyncio
async def test_analyze_endpoint_success_no_cache():
    # Mock services
    mock_analysis_service = AsyncMock()
    mock_analysis_service.analyze_repo.return_value = {"status": "success", "raw_analysis": "{}"}
    
    mock_cache_service = AsyncMock()
    mock_cache_service.get_analysis.return_value = None # No cache
    mock_cache_service.set_analysis.return_value = None

    # Override dependencies
    app.dependency_overrides[get_analysis_service] = lambda: mock_analysis_service
    app.dependency_overrides[get_cache_service] = lambda: mock_cache_service

    # Make request
    response = client.post("/api/analyze", json={"repo_url": "https://github.com/test/repo"})
    
    # Verify
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"] == {"status": "success", "raw_analysis": "{}"}
    
    # Verify logic
    mock_cache_service.get_analysis.assert_awaited_once()
    mock_analysis_service.analyze_repo.assert_awaited_once()
    mock_cache_service.set_analysis.assert_awaited_once()

    # Clean up
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_analyze_endpoint_success_cached():
    # Mock services
    mock_analysis_service = AsyncMock()
    
    mock_cache_service = AsyncMock()
    mock_cache_service.get_analysis.return_value = {"cached": "data"}

    # Override dependencies
    app.dependency_overrides[get_analysis_service] = lambda: mock_analysis_service
    app.dependency_overrides[get_cache_service] = lambda: mock_cache_service

    # Make request
    response = client.post("/api/analyze", json={"repo_url": "https://github.com/test/repo"})
    
    # Verify
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cached"
    assert data["data"] == {"cached": "data"}
    
    # Verify analysis NOT called
    mock_analysis_service.analyze_repo.assert_not_called()

    # Clean up
    app.dependency_overrides = {}

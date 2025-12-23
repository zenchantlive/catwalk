import pytest
from httpx import AsyncClient
from unittest.mock import patch
from app.models.user import User

@pytest.mark.asyncio
async def test_create_deployment_success(client: AsyncClient, auth_headers: dict, mock_user: User):
    """Test successful deployment creation."""
    deployment_data = {
        "name": "Test Deployment",
        "schedule_config": {
            "mcp_config": {
                "package": "test-mcp-server"
            }
        },
        "credentials": {
            "env_API_KEY": "secret-value"
        }
    }
    
    # Mock background tasks to avoid real initialization
    with patch("app.api.deployments.BackgroundTasks.add_task") as mock_add_task:
        response = await client.post(
            "/api/deployments",
            json=deployment_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Deployment"
        assert data["status"] == "pending"
        assert "connection_url" in data
        
        # Verify background task was enqueued
        assert mock_add_task.called
        # Check that the first argument to add_task is our background processing function
        # (It's enqueued via background_tasks.add_task(_process_deployment_initialization, ...))
        from app.api.deployments import _process_deployment_initialization
        assert mock_add_task.call_args[0][0] == _process_deployment_initialization

@pytest.mark.asyncio
async def test_create_deployment_missing_package(client: AsyncClient, auth_headers: dict, mock_user: User):
    """Test deployment creation fails if package is missing."""
    deployment_data = {
        "name": "Failing Deployment",
        "schedule_config": {},
        "credentials": {}
    }
    
    response = await client.post(
        "/api/deployments",
        json=deployment_data,
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "package_missing" in response.json()["detail"]["error"]

@pytest.mark.asyncio
async def test_list_deployments(client: AsyncClient, auth_headers: dict, mock_user: User):
    """Test listing deployments for a user."""
    # 1. Create one deployment manually via endpoint
    with patch("app.api.deployments.BackgroundTasks.add_task"):
        await client.post(
            "/api/deployments",
            json={
                "name": "D1",
                "schedule_config": {"mcp_config": {"package": "p1"}},
                "credentials": {}
            },
            headers=auth_headers
        )
    
    # 2. List deployments
    response = await client.get("/api/deployments", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(d["name"] == "D1" for d in data)

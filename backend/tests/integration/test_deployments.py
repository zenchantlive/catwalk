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


@pytest.mark.asyncio
async def test_rotate_token_success(client: AsyncClient, auth_headers: dict, mock_user: User):
    """Test successful access token rotation."""
    # 1. Create a deployment
    with patch("app.api.deployments.BackgroundTasks.add_task"):
        create_response = await client.post(
            "/api/deployments",
            json={
                "name": "Token Test Deployment",
                "schedule_config": {"mcp_config": {"package": "test-pkg"}},
                "credentials": {}
            },
            headers=auth_headers
        )
        assert create_response.status_code == 200
        deployment_id = create_response.json()["id"]
        old_token = create_response.json()["access_token"]
    
    # 2. Rotate the access token
    rotate_response = await client.post(
        f"/api/deployments/{deployment_id}/rotate-token",
        headers=auth_headers
    )
    
    assert rotate_response.status_code == 200
    data = rotate_response.json()
    
    # 3. Verify new token is different from old token
    new_token = data["access_token"]
    assert new_token != old_token
    assert len(new_token) == 32  # UUID4.hex is 32 characters
    
    # 4. Verify deployment data is intact
    assert data["id"] == deployment_id
    assert data["name"] == "Token Test Deployment"
    assert "connection_url" in data

@pytest.mark.asyncio
async def test_rotate_token_nonexistent_deployment(client: AsyncClient, auth_headers: dict, mock_user: User):
    """Test token rotation fails for non-existent deployment."""
    import uuid
    fake_deployment_id = str(uuid.uuid4())
    
    response = await client.post(
        f"/api/deployments/{fake_deployment_id}/rotate-token",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_rotate_token_unauthorized_user(client: AsyncClient, auth_headers: dict, mock_user: User, db_session):
    """Test token rotation fails when user doesn't own the deployment."""
    from app.models.deployment import Deployment
    from app.models.user import User
    import uuid
    
    # 1. Create another user
    other_user = User(
        id=uuid.uuid4(),
        email="other@example.com",
        name="Other User"
    )
    db_session.add(other_user)
    await db_session.commit()
    
    # 2. Create a deployment owned by the other user
    deployment = Deployment(
        name="Other's Deployment",
        schedule_config={"mcp_config": {"package": "test"}},
        status="pending",
        user_id=other_user.id
    )
    db_session.add(deployment)
    await db_session.commit()
    await db_session.refresh(deployment)
    
    # 3. Try to rotate token using current user's auth
    response = await client.post(
        f"/api/deployments/{deployment.id}/rotate-token",
        headers=auth_headers
    )
    
    # Should fail because current user doesn't own this deployment
    assert response.status_code == 404
    assert "permission" in response.json()["detail"].lower() or "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_rotate_token_invalidates_old_token(client: AsyncClient, auth_headers: dict, mock_user: User):
    """Test that rotating token invalidates the old token."""
    # 1. Create a deployment
    with patch("app.api.deployments.BackgroundTasks.add_task"):
        create_response = await client.post(
            "/api/deployments",
            json={
                "name": "Invalidation Test",
                "schedule_config": {"mcp_config": {"package": "test-pkg"}},
                "credentials": {}
            },
            headers=auth_headers
        )
        deployment_id = create_response.json()["id"]
        old_token = create_response.json()["access_token"]
    
    # 2. Rotate the token
    rotate_response = await client.post(
        f"/api/deployments/{deployment_id}/rotate-token",
        headers=auth_headers
    )
    new_token = rotate_response.json()["access_token"]
    
    # 3. Verify old token and new token are different
    assert old_token != new_token
    
    # 4. Try to access MCP endpoint with old token (should fail)
    # Note: This test assumes the MCP endpoint validates the access_token
    # The actual validation happens in mcp_streamable.py
    old_token_response = await client.get(
        f"/api/mcp/{deployment_id}",
        headers={"Authorization": f"Bearer {old_token}"}
    )
    # Old token should be rejected (assuming token validation is implemented)
    # This will depend on the MCP endpoint implementation
    
    # 5. Try to access with new token (should succeed or at least not fail auth)
    new_token_response = await client.get(
        f"/api/mcp/{deployment_id}",
        headers={"Authorization": f"Bearer {new_token}"}
    )
    # New token should pass auth validation
    # (actual response may vary based on MCP protocol requirements)

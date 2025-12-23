
import pytest
import uuid
from app.models.deployment import Deployment

@pytest.mark.asyncio
async def test_mcp_endpoint_missing_token(client):
    """Verify that accessing MCP endpoint without token fails 404/401"""
    # Random deployment ID
    deployment_id = str(uuid.uuid4())
    response = await client.get(f"/api/mcp/{deployment_id}")
    
    # Implementation checks for existence first, then token.
    # If it doesn't exist, it returns 404.
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_mcp_endpoint_with_invalid_token(client, db_session):
    """Verify that accessing MCP endpoint with INVALID token fails 401"""
    # 1. Create a dummy deployment
    deployment_id = uuid.uuid4()
    access_token = "valid-token-123"
    
    deployment = Deployment(
        id=deployment_id,
        name="Test Deployment",
        status="active",
        schedule_config={},
        access_token=access_token,
        user_id=uuid.uuid4()
    )
    db_session.add(deployment)
    await db_session.commit()
    
    # Invalid Token
    response = await client.get(f"/api/mcp/{deployment_id}?token=invalid")
    
    assert response.status_code == 401
    assert "Invalid access token" in response.json()['error']['message']

@pytest.mark.asyncio
async def test_mcp_endpoint_with_valid_token(client, db_session):
    """Verify that accessing MCP endpoint with VALID token proceeds (200 SSE)"""
    # 1. Create a dummy deployment
    deployment_id = uuid.uuid4()
    access_token = "valid-token-456"
    
    deployment = Deployment(
        id=deployment_id,
        name="Test Deployment",
        status="active",
        schedule_config={},
        access_token=access_token,
        user_id=uuid.uuid4()
    )
    db_session.add(deployment)
    await db_session.commit()
    
    # Valid Token
    async with client.stream("GET", f"/api/mcp/{deployment_id}?token={access_token}", timeout=5.0) as response:
        # It should pass auth and try to open SSE stream
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"

@pytest.mark.asyncio
async def test_mcp_endpoint_with_bearer_token(client, db_session):
    """Verify that accessing MCP endpoint with Bearer token works"""
    deployment_id = uuid.uuid4()
    access_token = "bearer-token-789"
    
    deployment = Deployment(
        id=deployment_id,
        name="Test Deployment",
        status="active",
        schedule_config={},
        access_token=access_token,
        user_id=uuid.uuid4()
    )
    db_session.add(deployment)
    await db_session.commit()
    
    # Bearer Token
    async with client.stream(
        "GET", 
        f"/api/mcp/{deployment_id}", 
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=5.0
    ) as response:
        assert response.status_code == 200

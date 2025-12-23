import pytest
from httpx import AsyncClient
from app.models.user import User
import uuid

@pytest.fixture
async def active_deployment(client: AsyncClient, auth_headers: dict, mock_user: User):
    """Create an active deployment for MCP testing."""
    response = await client.post(
        "/api/deployments",
        json={
            "name": "MCP Test",
            "schedule_config": {
                "mcp_config": {
                    "package": "test-pkg",
                    "tools": [{"name": "echo", "description": "Echoes"}]
                }
            },
            "credentials": {}
        },
        headers=auth_headers
    )
    return response.json()

@pytest.mark.asyncio
async def test_mcp_streamable_initialize(client: AsyncClient, active_deployment: dict):
    """Test MCP Streamable HTTP initialize request."""
    deployment_id = active_deployment["id"]
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "TestClient", "version": "1.0.0"}
        }
    }
    
    response = await client.post(
        f"/api/mcp/{deployment_id}",
        json=payload,
        headers={"MCP-Protocol-Version": "2025-06-18"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert "result" in data
    assert "capabilities" in data["result"]

@pytest.mark.asyncio
async def test_mcp_streamable_tools_list(client: AsyncClient, active_deployment: dict):
    """Test MCP Streamable HTTP tools/list request."""
    deployment_id = active_deployment["id"]
    
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    response = await client.post(
        f"/api/mcp/{deployment_id}",
        json=payload,
        headers={"MCP-Protocol-Version": "2025-06-18"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data["result"]
    assert any(t["name"] == "echo" for t in data["result"]["tools"])

@pytest.mark.asyncio
async def test_mcp_legacy_sse_endpoint(client: AsyncClient, active_deployment: dict):
    """Test legacy MCP SSE transport endpoint response."""
    deployment_id = active_deployment["id"]
    
    async with client.stream("GET", f"/api/mcp/{deployment_id}/sse") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        
        # Read just the first chunk/line to verify 'endpoint' event
        async for line in response.aiter_lines():
            if line.startswith("event: endpoint"):
                assert True
                break
            if line.startswith("data:"):
                assert f"/api/mcp/{deployment_id}/messages" in line
                break
        # Connection closed automatically on exit of context manager

@pytest.mark.asyncio
async def test_mcp_legacy_messages(client: AsyncClient, active_deployment: dict):
    """Test legacy MCP JSON-RPC messages endpoint."""
    deployment_id = active_deployment["id"]
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    
    response = await client.post(
        f"/api/mcp/{deployment_id}/messages",
        json=payload
    )
    
    assert response.status_code == 200
    assert response.json()["id"] == 1

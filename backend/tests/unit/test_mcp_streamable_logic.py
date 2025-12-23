import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.api.mcp_streamable import (
    process_jsonrpc_request,
    _get_deployment,
    _jsonrpc_error
)
from app.models.deployment import Deployment

@pytest.fixture
def mock_deployment():
    d = MagicMock(spec=Deployment)
    d.schedule_config = {"mcp_config": {"tools": [{"name": "test-tool"}]}}
    d.machine_id = None
    return d

@pytest.mark.asyncio
async def test_process_initialize(mock_deployment):
    """Test the 'initialize' handshake message."""
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    
    response = await process_jsonrpc_request(
        mock_deployment, 
        "dep-123", 
        message, 
        session_id=None, 
        protocol_version="2025-06-18"
    )
    
    assert response["id"] == 1
    assert "capabilities" in response["result"]
    assert response["result"]["protocolVersion"] == "2025-06-18"
    assert "_meta" in response["result"]

@pytest.mark.asyncio
async def test_process_tools_list(mock_deployment):
    """Test listing tools from deployment config."""
    message = {
        "jsonrpc": "2.0",
        "id": "list-1",
        "method": "tools/list"
    }
    
    response = await process_jsonrpc_request(
        mock_deployment,
        "dep-123",
        message,
        None,
        "2025-06-18"
    )
    
    assert response["id"] == "list-1"
    assert len(response["result"]["tools"]) == 1
    assert response["result"]["tools"][0]["name"] == "test-tool"

@pytest.mark.asyncio
async def test_process_tools_call_local_success(mock_deployment):
    """Test tool call forwarding to local subprocess server."""
    message = {
        "jsonrpc": "2.0",
        "id": "call-1",
        "method": "tools/call",
        "params": {"name": "test-tool", "arguments": {}}
    }
    
    mock_server = AsyncMock()
    mock_server.call_tool.return_value = {"jsonrpc": "2.0", "id": "call-1", "result": "ok"}
    
    with patch("app.api.mcp_streamable.get_server", new_callable=AsyncMock) as mock_get_server:
        mock_get_server.return_value = mock_server
        
        response = await process_jsonrpc_request(
            mock_deployment,
            "dep-123",
            message,
            None,
            "2025-06-18"
        )
        
        assert response["result"] == "ok"
        mock_server.call_tool.assert_called_once()

@pytest.mark.asyncio
async def test_process_unknown_method(mock_deployment):
    """Test error response for unknown methods."""
    message = {
        "jsonrpc": "2.0",
        "id": "bad-1",
        "method": "unknown/method"
    }
    
    response = await process_jsonrpc_request(
        mock_deployment,
        "dep-123",
        message,
        None,
        "2025-06-18"
    )
    
    assert "error" in response
    assert response["error"]["code"] == -32601

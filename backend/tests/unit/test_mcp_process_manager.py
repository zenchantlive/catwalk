import asyncio
import json
import pytest
import subprocess
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.mcp_process_manager import (
    ServerProcess, 
    start_server, 
    stop_server, 
    stop_all_servers, 
    _running_servers,
    IS_WINDOWS
)

@pytest.fixture(autouse=True)
async def cleanup_servers():
    """Ensure _running_servers is cleared before and after each test."""
    _running_servers.clear()
    yield
    await stop_all_servers()

@pytest.fixture
def mock_env():
    return {"API_KEY": "test-key"}

@pytest.mark.asyncio
async def test_start_server_npm_success(mock_env):
    """Test starting an NPM-based MCP server."""
    deployment_id = "test-dep-npm"
    package = "test-package"
    
    with patch("app.services.mcp_process_manager.subprocess.Popen" if IS_WINDOWS else "asyncio.create_subprocess_exec") as mock_popen:
        mock_proc = MagicMock() if IS_WINDOWS else AsyncMock()
        mock_proc.pid = 1234
        if IS_WINDOWS:
            mock_popen.return_value = mock_proc
        else:
            mock_popen.return_value = mock_proc
            
        success = await start_server(deployment_id, package, mock_env, runtime="npm")
        
        assert success is True
        assert deployment_id in _running_servers
        assert _running_servers[deployment_id].package == package
        
        if IS_WINDOWS:
            mock_popen.assert_called_once()
            args, kwargs = mock_popen.call_args
            assert args[0] == ["npx", "-y", package]
        else:
            mock_popen.assert_called_once()
            args = mock_popen.call_args.args
            assert args == ("npx", "-y", package)

@pytest.mark.asyncio
async def test_start_server_already_running(mock_env):
    """Test that starting an already running server returns success early."""
    deployment_id = "test-dep-dup"
    _running_servers[deployment_id] = AsyncMock(spec=ServerProcess)
    
    success = await start_server(deployment_id, "some-pkg", mock_env)
    assert success is True
    # Verify no new server was created (mock not replaced)
    assert isinstance(_running_servers[deployment_id], AsyncMock)


@pytest.mark.asyncio
async def test_call_tool_success(mock_env):
    """Test successful JSON-RPC tool call."""
    deployment_id = "test-dep-call"
    server = ServerProcess(deployment_id, "pkg", mock_env)
    
    mock_proc = MagicMock()
    mock_proc.stdin = MagicMock()
    mock_proc.stdout = MagicMock()
    server.process = mock_proc
    
    expected_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"content": "hello"}
    }
    
    # Mocking stdout.readline
    if IS_WINDOWS:
        mock_proc.stdout.readline.return_value = (json.dumps(expected_response) + "\n").encode()
    else:
        # For Unix, _call_tool_unix uses await self.process.stdout.readline()
        # but our mock is complicated by the threading logic on Windows.
        # We'll patch the specific call method to simplify.
        pass

    with patch.object(ServerProcess, "_call_tool_windows" if IS_WINDOWS else "_call_tool_unix", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = expected_response
        
        response = await server.call_tool("tools/call", {"name": "echo"}, msg_id=1)
        
        assert response == expected_response
        mock_call.assert_called_once()

@pytest.mark.asyncio
async def test_call_tool_failure_exception(mock_env):
    """Test tool call handling an exception during communication."""
    deployment_id = "test-dep-fail"
    server = ServerProcess(deployment_id, "pkg", mock_env)
    server.process = MagicMock()
    server.process.stdin = MagicMock()
    
    with patch.object(ServerProcess, "_call_tool_windows" if IS_WINDOWS else "_call_tool_unix", side_effect=Exception("Link broke")):
        response = await server.call_tool("tools/call", {}, msg_id="abc")
        
        assert "error" in response
        assert response["error"]["message"] == "Internal error: Link broke"
        assert response["id"] == "abc"

@pytest.mark.asyncio
async def test_stop_server_lifecycle(mock_env):
    """Test stopping a specific server."""
    deployment_id = "test-dep-stop"
    mock_server = AsyncMock(spec=ServerProcess)
    _running_servers[deployment_id] = mock_server
    
    await stop_server(deployment_id)
    
    mock_server.stop.assert_called_once()
    assert deployment_id not in _running_servers

@pytest.mark.asyncio
async def test_stop_all_servers(mock_env):
    """Test stopping all servers."""
    _running_servers["dep-1"] = AsyncMock(spec=ServerProcess)
    _running_servers["dep-2"] = AsyncMock(spec=ServerProcess)
    
    await stop_all_servers()
    
    assert len(_running_servers) == 0

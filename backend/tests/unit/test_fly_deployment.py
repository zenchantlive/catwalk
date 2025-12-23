import uuid
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.fly_deployment_service import FlyDeploymentService

@pytest.fixture
def fly_service():
    with patch("app.services.fly_deployment_service.settings") as mock_settings:
        mock_settings.FLY_MCP_APP_NAME = "test-app"
        mock_settings.FLY_MCP_IMAGE = "test-image"
        yield FlyDeploymentService()

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def user_id():
    return uuid.uuid4()

@pytest.fixture
def mcp_config():
    return {"package": "test-package"}

@pytest.fixture
def credentials():
    return {"API_KEY": "secret"}

@pytest.mark.asyncio
async def test_create_machine_success(fly_service, mock_db, user_id, mcp_config, credentials):
    """Test successful Fly machine creation."""
    deployment_id = "dep-123"
    expected_machine_id = "mac-456"
    
    with patch("app.services.fly_deployment_service.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = ("fake-fly-token", None)
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"id": expected_machine_id}
            mock_post.return_value = mock_response
            
            machine_id = await fly_service.create_machine(
                deployment_id=deployment_id,
                mcp_config=mcp_config,
                credentials=credentials,
                user_id=user_id,
                db=mock_db
            )
            
            assert machine_id == expected_machine_id
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["json"]["config"]["env"]["MCP_PACKAGE"] == "test-package"
            assert call_kwargs["headers"]["Authorization"] == "Bearer fake-fly-token"

@pytest.mark.asyncio
async def test_create_machine_missing_key(fly_service, mock_db, user_id, mcp_config, credentials):
    """Test failure when no API key is provided."""
    with patch("app.services.fly_deployment_service.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = (None, None)
        
        with pytest.raises(ValueError, match="No Fly.io API token available"):
            await fly_service.create_machine("id", mcp_config, credentials, user_id, mock_db)

@pytest.mark.asyncio
async def test_create_machine_api_error(fly_service, mock_db, user_id, mcp_config, credentials):
    """Test handling of Fly API error response."""
    with patch("app.services.fly_deployment_service.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = ("token", None)
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = "Bad Request"
            mock_post.return_value = mock_response
            
            with pytest.raises(Exception, match="Fly.io API Error"):
                await fly_service.create_machine("id", mcp_config, credentials, user_id, mock_db)

@pytest.mark.asyncio
async def test_get_machine_success(fly_service, mock_db, user_id):
    """Test successful retrieval of machine details."""
    machine_id = "mac-123"
    with patch("app.services.fly_deployment_service.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = ("token", None)
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": machine_id, "state": "started"}
            mock_get.return_value = mock_response
            
            result = await fly_service.get_machine(machine_id, user_id, mock_db)
            assert result["id"] == machine_id

@pytest.mark.asyncio
async def test_delete_machine_success(fly_service, mock_db, user_id):
    """Test successful machine deletion."""
    machine_id = "mac-123"
    with patch("app.services.fly_deployment_service.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = ("token", None)
        
        with patch("httpx.AsyncClient.delete", new_callable=AsyncMock) as mock_delete:
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_delete.return_value = mock_response
            
            result = await fly_service.delete_machine(machine_id, user_id, mock_db)
            assert result is True

@pytest.mark.asyncio
async def test_create_machine_missing_image(fly_service, mock_db, user_id, mcp_config, credentials):
    """Test failure when FLY_MCP_IMAGE is not set."""
    fly_service.image = None
    with patch("app.services.fly_deployment_service.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = ("token", None)
        with pytest.raises(ValueError, match="FLY_MCP_IMAGE is not configured"):
            await fly_service.create_machine("id", mcp_config, credentials, user_id, mock_db)

@pytest.mark.asyncio
async def test_create_machine_missing_package(fly_service, mock_db, user_id, credentials):
    """Test failure when package is missing from config."""
    with patch("app.services.fly_deployment_service.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = ("token", None)
        with pytest.raises(ValueError, match="No 'package' specified"):
            await fly_service.create_machine("id", {}, credentials, user_id, mock_db)

@pytest.mark.asyncio
async def test_delete_machine_no_token(fly_service, mock_db, user_id):
    """Test delete failure when no token available."""
    with patch("app.services.fly_deployment_service.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = (None, None)
        with pytest.raises(ValueError, match="No Fly.io API token available"):
            await fly_service.delete_machine("mac", user_id, mock_db)

@pytest.mark.asyncio
async def test_get_machine_api_failure(fly_service, mock_db, user_id):
    """Test handling of API exception in get_machine."""
    with patch("app.services.fly_deployment_service.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = ("token", None)
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("error")
            result = await fly_service.get_machine("mac", user_id, mock_db)
            assert result is None

@pytest.mark.asyncio
async def test_get_machine_no_token(fly_service, mock_db, user_id):
    """Test get failure when no token available."""
    with patch("app.services.fly_deployment_service.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = (None, None)
        with pytest.raises(ValueError, match="No Fly.io API token available"):
            await fly_service.get_machine("mac", user_id, mock_db)

@pytest.mark.asyncio
async def test_delete_machine_api_failure(fly_service, mock_db, user_id):
    """Test handling of API exception in delete_machine."""
    with patch("app.services.fly_deployment_service.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = ("token", None)
        with patch("httpx.AsyncClient.delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.side_effect = Exception("error")
            result = await fly_service.delete_machine("mac", user_id, mock_db)
            assert result is False

def test_get_headers_empty_token(fly_service):
    """Test warning log when token is empty."""
    with patch("app.services.fly_deployment_service.logger") as mock_logger:
        headers = fly_service._get_headers("")
        assert headers["Authorization"] == "Bearer "
        mock_logger.warning.assert_called_once_with("FLY_API_TOKEN is not set. Fly.io deployment will fail.")

@pytest.mark.asyncio
async def test_get_machine_not_found(fly_service, mock_db, user_id):
    """Test get_machine returning None for non-200 status."""
    with patch("app.services.fly_deployment_service.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = ("token", None)
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            result = await fly_service.get_machine("mac", user_id, mock_db)
            assert result is None

@pytest.mark.asyncio
async def test_delete_machine_api_error_response(fly_service, mock_db, user_id):
    """Test delete_machine returning False for non-200/202 status."""
    with patch("app.services.fly_deployment_service.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = ("token", None)
        with patch("httpx.AsyncClient.delete", new_callable=AsyncMock) as mock_delete:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal error"
            mock_delete.return_value = mock_response
            result = await fly_service.delete_machine("mac", user_id, mock_db)
            assert result is False

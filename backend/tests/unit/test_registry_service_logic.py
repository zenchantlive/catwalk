import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from app.services.registry_service import RegistryService
from app.schemas.registry import RegistrySearchParams, RegistryServer, RegistryServerCapabilities, RegistryServerTrust

@pytest.fixture
def mock_capabilities():
    return RegistryServerCapabilities(deployable=True, connectable=True)

@pytest.fixture
def mock_trust():
    return RegistryServerTrust(is_official=False, last_updated="")

@pytest.fixture
def service():
    # Reset singleton/instance state for tests
    RegistryService._instance = None
    return RegistryService.get_instance()

@pytest.mark.asyncio
async def test_registry_cache_logic(service):
    """Test that cache is used when valid."""
    service._last_updated = datetime.now()
    service._cache = {"test/server": MagicMock(spec=RegistryServer)}
    
    with patch.object(service, "_fetch_and_cache_registry", new_callable=AsyncMock) as mock_fetch:
        servers = await service.get_servers()
        assert len(servers) == 1
        mock_fetch.assert_not_called()

@pytest.mark.asyncio
async def test_search_servers_direct_id(service, mock_capabilities, mock_trust):
    """Test searching with a direct @namespace/slug ID."""
    params = RegistrySearchParams(query="@test/slug", limit=10, offset=0)
    
    mock_server = RegistryServer(
        id="test/slug",
        name="Test Slug",
        namespace="test",
        description="",
        version="1.0",
        capabilities=mock_capabilities,
        trust=mock_trust,
        install_ref=""
    )
    
    with patch.object(service, "get_server", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_server
        results = await service.search_servers(params)
        
        assert len(results) == 1
        assert results[0].id == "test/slug"
        mock_get.assert_called_with("test/slug")

def test_extract_form_data(service, mock_capabilities, mock_trust):
    """Test extracting form schema from raw Glama JSON schema."""
    mock_server = RegistryServer(
        id="test/form",
        name="Test Form",
        namespace="test",
        description="Desc",
        version="1.0",
        capabilities=mock_capabilities,
        trust=mock_trust,
        install_ref=""
    )
    
    raw_data = {
        "environmentVariablesJsonSchema": {
            "required": ["API_KEY"],
            "properties": {
                "API_KEY": {
                    "type": "string",
                    "description": "Your API key",
                    "format": "password"
                },
                "DEBUG": {
                    "type": "boolean",
                    "default": False
                }
            }
        }
    }
    service._raw_cache["test/form"] = raw_data
    
    form_data = service.extract_form_data(mock_server)
    
    assert form_data["name"] == "Test Form"
    assert len(form_data["env_vars"]) == 2
    
    api_key_field = next(f for f in form_data["env_vars"] if f["name"] == "API_KEY")
    assert api_key_field["required"] is True
    assert api_key_field["secret"] is True
    
    debug_field = next(f for f in form_data["env_vars"] if f["name"] == "DEBUG")
    assert debug_field["required"] is False
    assert debug_field["format"] == "boolean"

def test_disambiguate_display_names(service, mock_capabilities, mock_trust):
    """Test that duplicate names within a namespace are disambiguated."""
    s1 = RegistryServer(
        id="ns1/server-cli", name="My Server", namespace="ns1", 
        description="", version="1.0", 
        capabilities=mock_capabilities, trust=mock_trust, install_ref=""
    )
    s2 = RegistryServer(
        id="ns1/server-gui", name="My Server", namespace="ns1", 
        description="", version="1.0", 
        capabilities=mock_capabilities, trust=mock_trust, install_ref=""
    )
    
    results = service._disambiguate_display_names([s1, s2])
    
    assert len(results) == 2
    assert any(" (server-cli)" in s.name for s in results)
    assert any(" (server-gui)" in s.name for s in results)


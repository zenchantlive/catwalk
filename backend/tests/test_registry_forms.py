from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from app.api.forms import get_registry_form_schema
from app.schemas.dynamic_form import FormSchema
from app.schemas.registry import (
    RegistryServer,
    RegistryServerCapabilities,
    RegistryServerTrust,
)
from app.services.registry_service import RegistryService


@pytest.fixture
def mock_registry_service():
    """Create a mock RegistryService for testing."""
    service = Mock(spec=RegistryService)
    return service


@pytest.fixture
def sample_deployable_server():
    """Create a sample deployable registry server."""
    return RegistryServer(
        id="ai.test/test-server",
        name="Test MCP Server",
        namespace="ai.test",
        description="A test MCP server",
        version="1.0.0",
        homepage=None,
        repository_url="https://github.com/test/test-server",
        capabilities=RegistryServerCapabilities(
            deployable=True,
            connectable=False
        ),
        trust=RegistryServerTrust(
            is_official=False,
            last_updated=""
        ),
        install_ref="https://github.com/test/test-server"
    )


@pytest.fixture
def sample_glama_raw_server():
    """Sample raw Glama server response."""
    return {
        "id": "test123",
        "name": "Test MCP Server",
        "namespace": "ai.test",
        "slug": "test-server",
        "description": "A test MCP server",
        "repository": {
            "url": "https://github.com/test/test-server"
        },
        "attributes": ["hosting:remote-capable"],
        "environmentVariablesJsonSchema": {
            "type": "object",
            "properties": {
                "API_KEY": {
                    "type": "string",
                    "description": "API key for authentication"
                },
                "DEBUG_MODE": {
                    "type": "boolean",
                    "description": "Enable debug logging"
                }
            },
            "required": ["API_KEY"]
        },
        "tools": [
            {"name": "search", "description": "Search tool"}
        ],
        "resources": [],
        "prompts": [],
        "spdxLicense": {
            "name": "MIT License",
            "url": "https://spdx.org/licenses/MIT.json"
        },
        "url": "https://glama.ai/mcp/servers/test123"
    }


@pytest.fixture
def sample_form_data():
    """Sample form data extracted from Glama server."""
    return {
        "name": "Test MCP Server",
        "description": "A test MCP server",
        "package": "@test/mcp-server",
        "version": "1.0.0",
        "env_vars": [
            {
                "name": "API_KEY",
                "description": "API key for authentication",
                "required": True,
                "secret": True,
                "format": "string"
            },
            {
                "name": "DEBUG_MODE",
                "description": "Enable debug logging",
                "required": False,
                "secret": False,
                "format": "boolean"
            }
        ]
    }


@pytest.mark.asyncio
async def test_get_registry_form_schema_success(
    mock_registry_service,
    sample_deployable_server,
    sample_form_data,
    sample_glama_raw_server
):
    """Test successful form generation from registry data."""
    # Arrange: Setup mocks
    mock_registry_service.get_server = AsyncMock(return_value=sample_deployable_server)
    mock_registry_service.extract_form_data = Mock(return_value=sample_form_data)
    mock_registry_service.get_raw_server = Mock(return_value=sample_glama_raw_server)

    # Act: Call the endpoint
    result = await get_registry_form_schema(
        registry_id="ai.test/test-server",
        registry_service=mock_registry_service
    )

    # Assert: Verify the result
    assert isinstance(result, FormSchema)
    assert result.title == "Configure Test MCP Server"
    assert result.description == "A test MCP server"

    # Verify fields
    assert len(result.fields) == 3  # name + 2 env vars
    assert result.fields[0].name == "name"
    assert result.fields[0].type == "text"
    assert result.fields[0].required

    # Verify API_KEY field (should be password type because secret=True)
    api_key_field = next(f for f in result.fields if f.name == "env_API_KEY")
    assert api_key_field.type == "password"
    assert api_key_field.required
    assert "API key" in api_key_field.description

    # Verify DEBUG_MODE field (boolean should map to checkbox)
    debug_field = next(f for f in result.fields if f.name == "env_DEBUG_MODE")
    assert debug_field.type == "checkbox"
    assert not debug_field.required

    # Verify mcp_config
    assert result.mcp_config is not None
    assert result.mcp_config["package"] == "@test/mcp-server"
    assert result.mcp_config["tools"] == sample_glama_raw_server["tools"]
    assert result.mcp_config["resources"] == []
    assert result.mcp_config["prompts"] == []
    assert result.mcp_config["server_info"]["source"] == "glama"
    assert result.mcp_config["server_info"]["registry_id"] == "ai.test/test-server"
    assert not result.mcp_config["server_info"]["is_official"]


@pytest.mark.asyncio
async def test_get_registry_form_schema_server_not_found(mock_registry_service):
    """Test error when registry server is not found."""
    # Arrange: Server doesn't exist
    mock_registry_service.get_server = AsyncMock(return_value=None)

    # Act & Assert: Should raise 404
    with pytest.raises(HTTPException) as exc_info:
        await get_registry_form_schema(
            registry_id="ai.test/nonexistent",
            registry_service=mock_registry_service
    )

    assert exc_info.value.status_code == 404
    assert "not found in glama registry" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_get_registry_form_schema_local_only_server(
    mock_registry_service,
    sample_deployable_server
):
    """Test that local-only servers return 400 error."""
    sample_deployable_server.capabilities.deployable = False
    mock_registry_service.get_server = AsyncMock(return_value=sample_deployable_server)

    # Act & Assert: Should raise 400
    with pytest.raises(HTTPException) as exc_info:
        await get_registry_form_schema(
            registry_id="ai.test/test-server",
            registry_service=mock_registry_service
        )

    assert exc_info.value.status_code == 400
    assert "local-only" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_get_registry_form_schema_extract_error(
    mock_registry_service,
    sample_deployable_server
):
    """Test errors raised by extract_form_data are returned as 400."""
    mock_registry_service.get_server = AsyncMock(return_value=sample_deployable_server)
    mock_registry_service.extract_form_data = Mock(
        side_effect=ValueError("Raw data not found for server ai.test/test-server")
    )

    # Act & Assert: Should raise 400
    with pytest.raises(HTTPException) as exc_info:
        await get_registry_form_schema(
            registry_id="ai.test/test-server",
            registry_service=mock_registry_service
        )

    assert exc_info.value.status_code == 400
    assert "raw data not found" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_get_registry_form_schema_empty_env_vars(
    mock_registry_service,
    sample_deployable_server
):
    """Test form generation with no environment variables (valid case)."""
    # Arrange: Server with no env vars
    form_data = {
        "name": "Test MCP Server",
        "description": "A test MCP server",
        "package": "@test/mcp-server",
        "version": "1.0.0",
        "env_vars": []  # No environment variables
    }
    mock_registry_service.get_server = AsyncMock(return_value=sample_deployable_server)
    mock_registry_service.extract_form_data = Mock(return_value=form_data)
    mock_registry_service.get_raw_server = Mock(return_value={})

    # Act: Call the endpoint
    result = await get_registry_form_schema(
        registry_id="ai.test/test-server",
        registry_service=mock_registry_service
    )

    # Assert: Should succeed with only name field
    assert isinstance(result, FormSchema)
    assert len(result.fields) == 1  # Only "name" field
    assert result.fields[0].name == "name"
    assert result.mcp_config["package"] == "@test/mcp-server"


@pytest.mark.asyncio
async def test_get_registry_form_schema_unexpected_error(
    mock_registry_service,
    sample_deployable_server
):
    """Test handling of unexpected errors."""
    # Arrange: Unexpected exception
    mock_registry_service.get_server = AsyncMock(return_value=sample_deployable_server)
    mock_registry_service.extract_form_data = Mock(
        side_effect=Exception("Unexpected error")
    )
    mock_registry_service.get_raw_server = Mock(return_value={})

    # Act & Assert: Should raise 500
    with pytest.raises(HTTPException) as exc_info:
        await get_registry_form_schema(
            registry_id="ai.test/test-server",
            registry_service=mock_registry_service
        )

    assert exc_info.value.status_code == 500
    assert "Failed to generate form schema" in str(exc_info.value.detail)


def test_registry_service_extract_form_data():
    """Test RegistryService.extract_form_data() method."""
    # Create a real RegistryService instance
    service = RegistryService()

    # Create sample raw data
    raw_data = {
        "name": "Test MCP Server",
        "namespace": "ai.test",
        "slug": "test-server",
        "repository": {"url": "https://github.com/test/test-server"},
        "attributes": ["hosting:remote-capable"],
        "environmentVariablesJsonSchema": {
            "type": "object",
            "properties": {
                "API_KEY": {
                    "type": "string",
                    "description": "API key for authentication"
                }
            },
            "required": ["API_KEY"]
        }
    }

    # Create a RegistryServer
    server = RegistryServer(
        id="ai.test/test-server",
        name="Test MCP Server",
        namespace="ai.test",
        description="A test MCP server",
        version="1.0.0",
        homepage=None,
        repository_url="https://github.com/test/test-server",
        capabilities=RegistryServerCapabilities(deployable=True, connectable=False),
        trust=RegistryServerTrust(is_official=False, last_updated=""),
        install_ref="https://github.com/test/test-server"
    )

    # Manually inject raw data into cache
    service._raw_cache["ai.test/test-server"] = raw_data

    # Act: Extract form data
    result = service.extract_form_data(server)

    # Assert: Verify extraction
    assert result["name"] == "Test MCP Server"
    assert result["package"] == "https://github.com/test/test-server"
    assert len(result["env_vars"]) == 1
    assert result["env_vars"][0]["name"] == "API_KEY"
    assert result["env_vars"][0]["secret"]


def test_registry_service_extract_form_data_no_env_schema():
    """Test extract_form_data with server that has no environment variable schema."""
    service = RegistryService()

    # Raw data with no env schema
    raw_data = {
        "name": "Test MCP Server",
        "namespace": "ai.test",
        "slug": "test-server",
        "repository": {"url": "https://github.com/test/test-server"},
        "attributes": ["hosting:remote-capable"],
    }

    server = RegistryServer(
        id="ai.test/test-server",
        name="Test MCP Server",
        namespace="ai.test",
        description="A test MCP server",
        version="1.0.0",
        homepage=None,
        repository_url="https://github.com/test/test-server",
        capabilities=RegistryServerCapabilities(deployable=True, connectable=False),
        trust=RegistryServerTrust(is_official=False, last_updated=""),
        install_ref="https://github.com/test/test-server"
    )

    service._raw_cache["ai.test/test-server"] = raw_data

    # Act: Should return empty env vars
    result = service.extract_form_data(server)
    assert result["package"] == "https://github.com/test/test-server"
    assert result["env_vars"] == []

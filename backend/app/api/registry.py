from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.registry import RegistrySearchParams, RegistryServer
from app.services.registry_service import RegistryService

router = APIRouter()

def get_registry_service():
    return RegistryService.get_instance()

@router.get("/search", response_model=List[RegistryServer])
async def search_registry(
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    service: RegistryService = Depends(get_registry_service)
):
    """Search for MCP servers in the Glama MCP registry."""
    params = RegistrySearchParams(query=q, limit=limit, offset=offset)
    return await service.search_servers(params)

@router.get("/{server_id:path}", response_model=RegistryServer)
async def get_server(
    server_id: str,
    service: RegistryService = Depends(get_registry_service)
):
    """Get details for a specific MCP server by ID (e.g. 'ai.exa/exa')."""
    server = await service.get_server(server_id)
    if not server:
        raise HTTPException(
            status_code=404,
            detail=f"Server '{server_id}' not found in Glama registry",
        )
    return server

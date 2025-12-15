import asyncio
import sys
import os

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

from app.services.registry_service import RegistryService
from app.schemas.registry import RegistrySearchParams

async def main():
    service = RegistryService()
    print("Fetching servers...")
    try:
        servers = await service.get_servers()
        print(f"Total servers found: {len(servers)}")
        
        if servers:
            print(f"First server: {servers[0].id} - {servers[0].name}")
            
        print("\nSearching for 'stripe'...")
        results = await service.search_servers(RegistrySearchParams(query="stripe"))
        print(f"Found {len(results)} matches for 'stripe'")
        for r in results:
            print(f" - {r.id}: {r.description[:50]}...")
            
        print("\nFetching specific server 'ai.exa/exa'...")
        server = await service.get_server("ai.exa/exa")
        if server:
            print(f"Found server: {server.name}")
            print(f"Capabilities: {server.capabilities}")
            print(f"Deployable: {server.capabilities.deployable} (Install: {server.install_ref})")
        else:
            print("Server 'ai.exa/exa' not found")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())

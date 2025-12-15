import asyncio
import sys
import os

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

from app.services.registry_service import RegistryService
from app.schemas.registry import RegistrySearchParams

async def main():
    service = RegistryService.get_instance()
    print("Fetching servers...")
    try:
        servers = await service.get_servers()
        print(f"Total servers found: {len(servers)}")
        
        if servers:
            print(f"First server: {servers[0].id} - {servers[0].name}")
            print(f"Trust: Official={servers[0].trust.is_official}, Updated={servers[0].trust.last_updated}")
            
        print("\nSearching for 'stripe'...")
        results = await service.search_servers(RegistrySearchParams(query="stripe"))
        print(f"Found {len(results)} matches for 'stripe'")
        for r in results:
            print(f" - {r.id}: {r.description[:50]}...")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())

import logging
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from app.schemas.registry import RegistryServer, RegistrySearchParams, RegistryServerCapabilities, RegistryServerTrust

logger = logging.getLogger(__name__)

REGISTRY_API_URL = "https://registry.modelcontextprotocol.io/v0/servers"

class RegistryService:
    _instance = None
    _lock = asyncio.Lock()
    
    # Instance level cache
    def __init__(self):
        self._cache: Dict[str, RegistryServer] = {}
        self._last_updated: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=1)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_servers(self, force_refresh: bool = False) -> List[RegistryServer]:
        """Get all servers from the registry, using cache if valid."""
        if not force_refresh and self._is_cache_valid():
            return list(self._cache.values())
        
        await self._fetch_and_cache_registry()
        return list(self._cache.values())

    async def search_servers(self, params: RegistrySearchParams) -> List[RegistryServer]:
        """Search servers with simple text matching."""
        servers = await self.get_servers()
        
        # Simple local search (scalability concern noted: move to DB in future)
        filtered = servers
        if params.query:
            q = params.query.lower()
            filtered = [
                s for s in servers 
                if q in s.name.lower() or 
                   q in s.description.lower() or 
                   q in s.namespace.lower() or
                   (s.install_ref and q in s.install_ref.lower())
            ]
            
        # Pagination
        start = params.offset
        end = params.offset + params.limit
        return filtered[start:end]

    async def get_server(self, server_id: str) -> Optional[RegistryServer]:
        """Get a single server by its ID."""
        if self._is_cache_valid() and server_id in self._cache:
            return self._cache[server_id]
        
        await self._fetch_and_cache_registry()
        return self._cache.get(server_id)

    def _is_cache_valid(self) -> bool:
        if not self._last_updated:
            return False
        return datetime.now() - self._last_updated < self._cache_ttl

    async def _fetch_and_cache_registry(self):
        """Fetches from official registry with lock to prevent race conditions."""
        async with self._lock:
            # Double check inside lock
            if self._is_cache_valid():
                return

            logger.info("Fetching registry data from official API...")
            try:
                async with httpx.AsyncClient() as client:
                    all_raw_servers = []
                    cursor = None
                    
                    for _ in range(10): 
                        params = {"limit": 100}
                        if cursor:
                            params["cursor"] = cursor
                            
                        response = await client.get(REGISTRY_API_URL, params=params)
                        response.raise_for_status()
                        data = response.json()
                        
                        if "servers" in data:
                            all_raw_servers.extend(data["servers"])
                        
                        cursor = data.get("metadata", {}).get("nextCursor")
                        if not cursor:
                            break
                    
                    new_cache = {}
                    for raw in all_raw_servers:
                        try:
                            normalized = self._normalize_server(raw)
                            if normalized:
                                new_cache[normalized.id] = normalized
                        except Exception as e:
                            logger.warning(f"Failed to normalize server entry: {e}")
                            continue
                    
                    self._cache = new_cache
                    self._last_updated = datetime.now()
                    logger.info(f"Registry cache updated with {len(new_cache)} servers.")
                    
            except Exception as e:
                logger.error(f"Error fetching registry data: {e}", exc_info=True)

    def _normalize_server(self, raw: Dict) -> Optional[RegistryServer]:
        inner = raw.get("server", {})
        meta = raw.get("_meta", {})
        
        full_name = inner.get("name")
        if not full_name: 
            return None
            
        namespace, name_only = full_name.split("/", 1) if "/" in full_name else ("unknown", full_name)
        
        packages = inner.get("packages", [])
        remotes = inner.get("remotes", [])
        
        is_deployable = len(packages) > 0
        is_connectable = len(remotes) > 0
        
        install_ref = None
        if is_deployable:
            for pkg in packages:
                if pkg.get("registryType") == "oci":
                    install_ref = pkg.get("identifier")
                    break
        
        official_meta = meta.get("io.modelcontextprotocol.registry/official", {})
        is_official = official_meta.get("status") == "active"
        
        return RegistryServer(
            id=full_name,
            name=name_only,
            namespace=namespace,
            description=inner.get("description", "") or "",
            version=inner.get("version", "0.0.0"),
            homepage=None,
            repository_url=inner.get("repository", {}).get("url"),
            
            capabilities=RegistryServerCapabilities(
                deployable=is_deployable,
                connectable=is_connectable
            ),
            trust=RegistryServerTrust(
                is_official=is_official,
                last_updated=official_meta.get("updatedAt", "")
            ),
            install_ref=install_ref
        )

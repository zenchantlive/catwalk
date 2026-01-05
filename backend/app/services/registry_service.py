import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree

import httpx

from app.schemas.registry import (
    RegistrySearchParams,
    RegistryServer,
    RegistryServerCapabilities,
    RegistryServerTrust,
)
from app.services.github_service import get_github_service

logger = logging.getLogger(__name__)

GLAMA_API_URL = "https://glama.ai/api/mcp/v1/servers"
GLAMA_SERVERS_SITEMAP_URL = "https://glama.ai/sitemaps/mcp-servers.xml"

# Service Constants
DEFAULT_TIMEOUT_SECONDS = 10.0
MAX_PAGES_TO_FETCH = 25
BATCH_SIZE = 20
GLAMA_ITEMS_PER_PAGE = 100
MAX_SEARCH_LIMIT = 101
CACHE_TTL_HOURS = 1
SITEMAP_TTL_HOURS = 12

_SITEMAP_XMLNS = "http://www.sitemaps.org/schemas/sitemap/0.9"
_SITEMAP_LOC_TAG = f"{{{_SITEMAP_XMLNS}}}loc"
_SITEMAP_SERVER_RE = re.compile(
    r"^https?://glama\.ai/mcp/servers/@(?P<namespace>[^/]+)/(?P<slug>[^/?#]+)$"
)

class RegistryService:
    _instance = None
    _lock = asyncio.Lock()

    # Instance level cache
    def __init__(self):
        self._cache: Dict[str, RegistryServer] = {}
        self._raw_cache: Dict[str, Dict] = {}  # Store raw registry API data
        self._last_updated: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=CACHE_TTL_HOURS)

        # Full directory index (12k+) via Glama sitemap for reliable lookup.
        self._sitemap_ids: List[str] = []
        self._sitemap_last_updated: Optional[datetime] = None
        self._sitemap_ttl = timedelta(hours=SITEMAP_TTL_HOURS)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_servers(self, force_refresh: bool = False) -> List[RegistryServer]:
        """Get all servers from the registry, using cache if valid."""
        if not force_refresh and self._is_cache_valid():
            # Read from cache with lock? dict reads are atomic in python,
            # but for consistency we can trust the atomic swap pattern used below.
            servers = list(self._cache.values())
            # Enrich with GitHub star data progressively
            await self._enrich_servers_with_github_data(servers)
            return servers
        
        await self._fetch_and_cache_registry()
        servers = list(self._cache.values())
        # Enrich with GitHub star data progressively
        await self._enrich_servers_with_github_data(servers)
        return servers

    async def search_servers(
        self,
        params: RegistrySearchParams,
    ) -> List[RegistryServer]:
        """
        Search Glama servers.

        Important: Glama's `GET /v1/servers` "browse" response is not a complete
        listing of the full directory; the `query` parameter must be used to
        search across the broader catalog.
        """
        query = (params.query or "").strip()

        # For the default "browse" feed, use our cached list (fast path).
        if not query:
            servers = await self.get_servers()
            deployable = [s for s in servers if s.capabilities.deployable]
            deployable = self._disambiguate_display_names(deployable)
            # GitHub data is already enriched in get_servers()
            return deployable[params.offset : params.offset + params.limit]

        # If the user enters a direct ID like "namespace/slug" (or "@namespace/slug"),
        # short-circuit to a detail lookup so we can find servers outside the
        # limited search result window.
        direct_id = self._parse_direct_server_id(query)
        if direct_id:
            server = await self.get_server(direct_id)
            if server and server.capabilities.deployable:
                return self._disambiguate_display_names([server])
            return []

        target_count = max(0, params.offset) + max(0, params.limit)
        if target_count == 0:
            return []

        collected: List[RegistryServer] = []
        seen_ids: set[str] = set()

        # 1) High-precision: match against the full directory of namespace/slug
        # via the public sitemap, then hydrate via the detail endpoint.
        sitemap_results = await self._search_via_sitemap_ids(
            query=query,
            seen_ids=seen_ids,
            needed=target_count,
        )
        collected.extend(sitemap_results)

        # 2) Fuzzy: supplement with Glama API search (can match name/description),
        # but filter out obvious non-matches to avoid returning irrelevant results
        # (the API often returns generic "mcp" hits).
        if len(collected) < target_count:
            glama_results = await self._search_glama(
                query=query,
                offset=0,
                limit=min(MAX_SEARCH_LIMIT, target_count * 2),
            )
            q_lower = query.lower()
            for server in glama_results:
                if server.id in seen_ids:
                    continue
                if not self._server_matches_query(server, q_lower):
                    continue
                seen_ids.add(server.id)
                collected.append(server)
                if len(collected) >= target_count:
                    break

        sliced = collected[params.offset : target_count]
        # Enrich with GitHub star data progressively
        await self._enrich_servers_with_github_data(sliced)
        return self._disambiguate_display_names(sliced)

    async def get_server(self, server_id: str) -> Optional[RegistryServer]:
        """Get a single server by its ID."""
        if server_id in self._cache:
            return self._cache[server_id]
        
        # Avoid forcing a full list refresh for a single server lookup.
        try:
            raw = await self._fetch_glama_server_detail(server_id)
        except Exception as e:
            logger.warning(f"Failed to fetch server detail for {server_id}: {e}")
            raw = None

        if raw:
            normalized = self._normalize_glama_server(raw)
            if normalized:
                async with self._lock:
                    self._cache[normalized.id] = normalized
                    self._raw_cache[normalized.id] = raw
                # Enrich with GitHub star data
                await self._enrich_servers_with_github_data([normalized])
                return normalized

        await self._fetch_and_cache_registry()
        server = self._cache.get(server_id)
        if server:
            # Enrich with GitHub star data
            await self._enrich_servers_with_github_data([server])
        return server

    def _is_cache_valid(self) -> bool:
        if not self._last_updated:
            return False
        return datetime.now() - self._last_updated < self._cache_ttl

    async def _fetch_and_cache_registry(self):
        """Fetches from Glama API with lock to prevent race conditions."""
        async with self._lock:
            # Double check inside lock
            if self._is_cache_valid():
                return

            logger.info("Fetching deployable registry data from Glama API...")
            try:
                timeout = httpx.Timeout(DEFAULT_TIMEOUT_SECONDS)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    all_raw_servers: List[Dict[str, Any]] = []
                    for query in ("hosting:remote-capable", "hosting:hybrid"):
                        all_raw_servers.extend(
                            await self._fetch_glama_list(
                                client=client,
                                query=query,
                            )
                        )
                    
                    new_cache = {}
                    new_raw_cache = {}  # Store raw data for form generation
                    for raw in all_raw_servers:
                        try:
                            normalized = self._normalize_glama_server(raw)
                            if normalized:
                                if not normalized.capabilities.deployable:
                                    continue
                                new_cache[normalized.id] = normalized
                                new_raw_cache[normalized.id] = raw  # Store raw data
                        except Exception as e:
                            logger.warning(
                                f"Failed to normalize Glama server entry: {e}"
                            )
                            continue

                    self._cache = new_cache
                    self._raw_cache = new_raw_cache  # Update raw cache
                    self._last_updated = datetime.now()
                    logger.info(
                        "Registry cache updated with "
                        f"{len(new_cache)} servers from Glama."
                    )

                    # Disambiguate duplicate display names within a namespace.
                    self._cache = {
                        s.id: s
                        for s in self._disambiguate_display_names(
                            list(self._cache.values())
                        )
                    }
                    
            except Exception as e:
                logger.error(f"Error fetching Glama registry data: {e}", exc_info=True)

    async def _fetch_glama_list(
        self,
        client: httpx.AsyncClient,
        query: str,
    ) -> List[Dict[str, Any]]:
        """
        Fetch a Glama server list for a specific query.

        Glama's API currently caps list/search results to ~100 items, so this
        helper is mainly to retrieve a reasonably sized "deployable feed".
        """
        all_raw_servers: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        for _ in range(MAX_PAGES_TO_FETCH):
            params: Dict[str, Any] = {"first": GLAMA_ITEMS_PER_PAGE, "query": query}
            if cursor:
                params["after"] = cursor

            response = await client.get(GLAMA_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            payload = data.get("data", data)

            servers = payload.get("servers", [])
            if isinstance(servers, list):
                all_raw_servers.extend([s for s in servers if isinstance(s, dict)])

            page_info = payload.get("pageInfo", {}) or {}
            if not page_info.get("hasNextPage", False):
                break

            cursor = page_info.get("endCursor")
            if not cursor:
                break

        return all_raw_servers

    async def _search_glama(
        self,
        query: str,
        offset: int,
        limit: int,
    ) -> List[RegistryServer]:
        """
        Search Glama via the API.

        We only fetch enough pages to satisfy offset+limit, since Glama paginates
        via cursors and has a max `first` of 100.
        """
        target_count = max(0, offset) + max(0, limit)
        if target_count == 0:
            return []

        collected: List[RegistryServer] = []
        seen_ids: set[str] = set()
        cursor: Optional[str] = None

        timeout = httpx.Timeout(DEFAULT_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            for _ in range(MAX_PAGES_TO_FETCH):
                params: Dict[str, Any] = {"first": GLAMA_ITEMS_PER_PAGE, "query": query}
                if cursor:
                    params["after"] = cursor

                response = await client.get(GLAMA_API_URL, params=params)
                response.raise_for_status()
                data = response.json()
                payload = data.get("data", data)

                servers = payload.get("servers", [])
                if isinstance(servers, list):
                    for raw in servers:
                        normalized = self._normalize_glama_server(raw)
                        if not normalized:
                            continue
                        if not normalized.capabilities.deployable:
                            continue
                        if normalized.id in seen_ids:
                            continue
                        seen_ids.add(normalized.id)
                        collected.append(normalized)
                        
                        # Cache raw/normalized for later detail/form generation.
                        async with self._lock:
                            self._cache[normalized.id] = normalized
                            self._raw_cache[normalized.id] = raw

                        if len(collected) >= target_count:
                            return collected[offset:target_count]

                page_info = payload.get("pageInfo", {}) or {}
                if not page_info.get("hasNextPage", False):
                    break

                cursor = page_info.get("endCursor")
                if not cursor:
                    break

        return collected[offset:target_count]

    def _parse_direct_server_id(self, query: str) -> Optional[str]:
        """
        Accept direct lookups like:
        - "namespace/slug"
        - "@namespace/slug"
        - "https://glama.ai/mcp/servers/@namespace/slug"
        """
        q = query.strip()
        if not q:
            return None

        match = _SITEMAP_SERVER_RE.match(q)
        if match:
            return f"{match.group('namespace')}/{match.group('slug')}"

        if q.startswith("@"):
            q = q[1:]

        parts = q.split("/", 1)
        if len(parts) != 2:
            return None
        namespace, slug = parts
        if not namespace or not slug:
            return None
        if " " in namespace or " " in slug:
            return None
        return f"{namespace}/{slug}"

    def _server_matches_query(self, server: RegistryServer, query_lower: str) -> bool:
        if not query_lower:
            return True
        if query_lower in server.id.lower():
            return True
        if query_lower in server.name.lower():
            return True
        if query_lower in server.namespace.lower():
            return True
        if query_lower in (server.description or "").lower():
            return True
        if server.repository_url and query_lower in server.repository_url.lower():
            return True
        if server.install_ref and query_lower in server.install_ref.lower():
            return True
        return False

    def _is_sitemap_valid(self) -> bool:
        if not self._sitemap_last_updated:
            return False
        return datetime.now() - self._sitemap_last_updated < self._sitemap_ttl

    async def _ensure_sitemap_index(self) -> None:
        if self._is_sitemap_valid() and self._sitemap_ids:
            return

        async with self._lock:
            if self._is_sitemap_valid() and self._sitemap_ids:
                return

            logger.info("Fetching Glama MCP servers sitemap...")
            timeout = httpx.Timeout(DEFAULT_TIMEOUT_SECONDS)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(GLAMA_SERVERS_SITEMAP_URL)
                resp.raise_for_status()
                xml_text = resp.text

            root = ElementTree.fromstring(xml_text)
            ids: List[str] = []
            for loc_el in root.iter(_SITEMAP_LOC_TAG):
                if loc_el.text is None:
                    continue
                url = loc_el.text.strip()
                match = _SITEMAP_SERVER_RE.match(url)
                if not match:
                    continue
                namespace = match.group("namespace")
                slug = match.group("slug")
                ids.append(f"{namespace}/{slug}")

            # Deterministic ordering for pagination.
            ids = sorted(set(ids))
            self._sitemap_ids = ids
            self._sitemap_last_updated = datetime.now()
            logger.info(f"Sitemap index updated with {len(ids)} server IDs.")

    async def _search_via_sitemap_ids(
        self,
        query: str,
        seen_ids: set[str],
        needed: int,
    ) -> List[RegistryServer]:
        """
        Fallback search: match the user's query against namespace/slug from the
        public sitemap, then hydrate via the Glama detail endpoint.
        """
        if needed <= 0:
            return []

        await self._ensure_sitemap_index()
        q = query.lower()

        # Find candidate IDs by substring match on "namespace/slug".
        candidates: List[str] = []
        for server_id in self._sitemap_ids:
            if server_id in seen_ids:
                continue
            if q in server_id.lower():
                candidates.append(server_id)

        # Rank: earlier match position, then shorter IDs, then lexicographic.
        candidates.sort(
            key=lambda sid: (
                sid.lower().find(q),
                len(sid),
                sid.lower(),
            )
        )

        collected: List[RegistryServer] = []
        target_count = needed

        timeout = httpx.Timeout(DEFAULT_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            for i in range(0, len(candidates), BATCH_SIZE):
                if len(collected) >= target_count:
                    break

                batch = candidates[i : i + BATCH_SIZE]
                raws = await asyncio.gather(
                    *[
                        self._fetch_glama_server_detail_with_client(
                            client=client,
                            server_id=server_id,
                        )
                        for server_id in batch
                    ],
                    return_exceptions=True,
                )
                for raw in raws:
                    if isinstance(raw, Exception) or not raw:
                        continue

                    normalized = self._normalize_glama_server(raw)
                    if not normalized:
                        continue
                    if not normalized.capabilities.deployable:
                        continue
                    if normalized.id in seen_ids:
                        continue

                    seen_ids.add(normalized.id)
                    collected.append(normalized)
                    
                    async with self._lock:
                        self._cache[normalized.id] = normalized
                        self._raw_cache[normalized.id] = raw

                    if len(collected) >= target_count:
                        break

        return collected

    async def _fetch_glama_server_detail(
        self,
        server_id: str,
    ) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            return await self._fetch_glama_server_detail_with_client(
                client=client,
                server_id=server_id,
            )

    async def _fetch_glama_server_detail_with_client(
        self,
        client: httpx.AsyncClient,
        server_id: str,
    ) -> Optional[Dict[str, Any]]:
        parts = server_id.split("/", 1)
        if len(parts) != 2:
            return None
        namespace, slug = parts
        url = f"{GLAMA_API_URL}/{namespace}/{slug}"

        response = await client.get(url)
        if response.status_code == 404 and slug.lower() != slug:
            # Some sitemap slugs include uppercase; try a lowercase fallback.
            fallback_url = f"{GLAMA_API_URL}/{namespace}/{slug.lower()}"
            response = await client.get(fallback_url)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def _disambiguate_display_names(
        self,
        servers: List[RegistryServer],
    ) -> List[RegistryServer]:
        """
        If Glama returns multiple servers with the same display name within the
        same namespace, append the slug to make cards/search results readable.
        """
        name_groups: Dict[tuple[str, str], List[RegistryServer]] = {}
        for server in servers:
            name_groups.setdefault((server.namespace, server.name), []).append(server)

        result_servers: List[RegistryServer] = []
        processed_ids: set[str] = set()

        for server in servers:
            if server.id in processed_ids:
                continue

            group = name_groups.get((server.namespace, server.name), [])
            if len(group) > 1:
                # If there are duplicates, disambiguate all of them
                for s in group:
                    slug = s.id.split("/", 1)[1] if "/" in s.id else s.id
                    # Create a new object instead of modifying in-place
                    new_server = s.model_copy()
                    new_server.name = f"{s.name} ({slug})"
                    result_servers.append(new_server)
                    processed_ids.add(s.id)
            else:
                result_servers.append(server)
                processed_ids.add(server.id)

        return result_servers

    async def _enrich_servers_with_github_data(self, servers: List[RegistryServer]) -> None:
        """
        Enrich servers with GitHub star count data progressively.
        
        This method fetches GitHub star counts for servers that have repository URLs,
        but does not block if GitHub API is unavailable. It updates the server objects
        in-place with star count information.
        
        Args:
            servers: List of RegistryServer objects to enrich
        """
        if not servers:
            return
            
        github_service = get_github_service()
        
        # Process servers concurrently but with reasonable limits
        semaphore = asyncio.Semaphore(10)  # Limit concurrent GitHub API calls
        
        async def enrich_single_server(server: RegistryServer) -> None:
            async with semaphore:
                if not server.repository_url:
                    return
                    
                try:
                    # Check if we need to fetch (no data or data is old)
                    should_fetch = (
                        server.star_count is None or 
                        server.last_star_fetch is None or
                        datetime.now() - server.last_star_fetch > timedelta(hours=1)
                    )
                    
                    if should_fetch:
                        star_count = await github_service.get_star_count(server.repository_url)
                        if star_count is not None:
                            server.star_count = star_count
                            server.star_count_formatted = github_service.format_star_count(star_count)
                            server.last_star_fetch = datetime.now()
                            
                            # Update cache
                            async with self._lock:
                                if server.id in self._cache:
                                    self._cache[server.id] = server
                                    
                except Exception as e:
                    # Log but don't fail - GitHub data is optional
                    logger.debug(f"Failed to fetch GitHub data for {server.id}: {e}")
        
        # Execute all enrichment tasks concurrently
        tasks = [enrich_single_server(server) for server in servers]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_raw_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Return the raw Glama server payload (used for schema/tool metadata)."""
        return self._raw_cache.get(server_id)

    def extract_form_data(self, server: RegistryServer) -> Dict:
        """
        Extract form generation data from Glama server's environmentVariablesJsonSchema.

        Args:
            server: Normalized RegistryServer object

        Returns:
            Dict with structure:
            {
                "name": str,
                "description": str,
                "package": str,  # OCI identifier
                "version": str,
                "env_vars": [
                    {
                        "name": str,
                        "description": str,
                        "required": bool,
                        "secret": bool,
                        "format": str
                    }
                ]
            }

        """
        # Get raw Glama data for this server
        raw_server = self._raw_cache.get(server.id)
        if not raw_server:
            raise ValueError(f"Raw data not found for server {server.id}")

        env_schema = raw_server.get("environmentVariablesJsonSchema") or {}
        properties = env_schema.get("properties") or {}
        required_fields = set(env_schema.get("required") or [])

        # Parse JSON Schema properties into simple form field descriptors.
        env_vars = []
        if isinstance(properties, dict):
            for var_name, var_schema in properties.items():
                if not var_name or not isinstance(var_schema, dict):
                    continue

                schema_type = var_schema.get("type", "string")
                if isinstance(schema_type, list):
                    schema_type = next(
                        (t for t in schema_type if t != "null"),
                        "string",
                    )

                options = var_schema.get("enum")
                is_secret = (
                    var_schema.get("format") == "password"
                    or bool(var_schema.get("writeOnly"))
                    or any(
                        token in var_name.lower()
                        for token in ("secret", "token", "key", "password")
                    )
                )

                env_vars.append({
                    "name": var_name,
                    "description": var_schema.get("description", "") or "",
                    "required": var_name in required_fields,
                    "secret": is_secret,
                    "format": schema_type,
                    "options": options if isinstance(options, list) else None,
                    "default": var_schema.get("default"),
                })

        return {
            "name": server.name,
            "description": server.description,
            "package": self._extract_package(raw_server, server),
            "version": server.version,
            "env_vars": env_vars
        }

    def _extract_package(
        self,
        raw_server: Dict[str, Any],
        server: RegistryServer,
    ) -> Optional[str]:
        package = (
            raw_server.get("package")
            or raw_server.get("npmPackage")
            or raw_server.get("npm_package")
            or raw_server.get("packageName")
        )
        if isinstance(package, str) and package.strip():
            return package.strip()

        repo_url = raw_server.get("repository", {}).get("url")
        if isinstance(repo_url, str) and repo_url.strip():
            return repo_url.strip()

        return server.repository_url or server.install_ref

    def _clean_server_name(self, raw_name: str, description: str = "") -> str:
        """
        Clean up generic server names to be more descriptive.
        
        Examples:
        - "Remote MCP Server (Authless)" → "Authless Server"
        - "Remote MCP Server on Cloudflare" → "Cloudflare Server"
        - "Python MCP Weather Server with OAuth 2.1 Authentication" → "Weather Server with OAuth 2.1"
        """
        if not raw_name:
            return raw_name
            
        name = raw_name.strip()
        
        # Remove common prefixes that don't add value
        prefixes_to_remove = [
            "Remote MCP Server",
            "MCP Server", 
            "Python MCP",
            "Node MCP",
            "JavaScript MCP"
        ]
        
        for prefix in prefixes_to_remove:
            if name.startswith(prefix):
                # Extract the meaningful part after the prefix
                remainder = name[len(prefix):].strip()
                
                # Handle different patterns
                if remainder.startswith("(") and remainder.endswith(")"):
                    # "Remote MCP Server (Authless)" → "Authless Server"
                    content = remainder[1:-1].strip()
                    if content:
                        return f"{content} Server"
                elif remainder.startswith("on "):
                    # "Remote MCP Server on Cloudflare" → "Cloudflare Server"
                    platform = remainder[3:].strip()
                    if platform.startswith("(") and platform.endswith(")"):
                        # "on Cloudflare (Without Auth)" → "Cloudflare (Without Auth) Server"
                        return f"{platform[1:-1]} Server"
                    elif platform:
                        return f"{platform} Server"
                elif remainder.startswith("for "):
                    # "MCP Server for Weather" → "Weather Server"
                    purpose = remainder[4:].strip()
                    if purpose:
                        return f"{purpose} Server"
                elif remainder.startswith("with "):
                    # Extract the key feature, but try to keep it concise
                    feature = remainder[5:].strip()
                    if feature:
                        # Try to extract the main purpose from description first
                        desc_lower = description.lower()
                        if "weather" in desc_lower:
                            # Shorten long authentication descriptions
                            if "oauth" in feature.lower():
                                return "Weather Server with OAuth"
                            return f"Weather Server with {feature}"
                        elif "image" in desc_lower or "vision" in desc_lower or "moondream" in desc_lower:
                            return "Vision Analysis Server"
                        else:
                            # Keep authentication info concise
                            if "oauth" in feature.lower():
                                return "Server with OAuth"
                            return f"Server with {feature}"
                elif remainder:
                    # "Python MCP Weather Server" → "Weather Server"
                    # Remove "Server" suffix if it exists to avoid "Weather Server Server"
                    clean_remainder = remainder.replace(" Server", "").strip()
                    return f"{clean_remainder} Server" if clean_remainder else remainder
                else:
                    # Just the prefix, try to infer from description
                    break
        
        # If we couldn't clean the prefix, try to infer purpose from description
        if any(prefix in name for prefix in prefixes_to_remove):
            desc_lower = description.lower()
            
            # Common patterns in descriptions
            purpose_keywords = {
                "weather": "Weather Server",
                "image analysis": "Vision Analysis Server", 
                "vision": "Vision Analysis Server",
                "moondream": "Vision Analysis Server",
                "database": "Database Server",
                "file": "File Management Server",
                "browser": "Web Browser Server",
                "stripe": "Stripe Payments Server",
                "github": "GitHub Integration Server",
                "slack": "Slack Integration Server",
                "email": "Email Server",
                "calendar": "Calendar Server",
                "todo": "Task Management Server",
                "note": "Note Taking Server"
            }
            
            for keyword, purpose in purpose_keywords.items():
                if keyword in desc_lower:
                    return purpose
        
        return name

    def _normalize_glama_server(self, raw: Dict[str, Any]) -> Optional[RegistryServer]:
        namespace = raw.get("namespace")
        slug = raw.get("slug")
        if not namespace or not slug:
            return None

        full_id = f"{namespace}/{slug}"

        attributes = raw.get("attributes", [])
        if not isinstance(attributes, list):
            attributes = []

        is_remote_capable = "hosting:remote-capable" in attributes
        is_local_only = "hosting:local-only" in attributes
        is_hybrid = "hosting:hybrid" in attributes

        repo_url = raw.get("repository", {}).get("url")
        if not isinstance(repo_url, str):
            repo_url = None

        raw_name = raw.get("name") or slug
        description = raw.get("description", "") or ""
        cleaned_name = self._clean_server_name(raw_name, description)

        return RegistryServer(
            id=full_id,
            name=cleaned_name,
            namespace=namespace,
            description=description,
            version=raw.get("version") or "1.0.0",
            homepage=None,
            repository_url=repo_url,
            
            # GitHub star count data (will be populated later)
            star_count=None,
            star_count_formatted=None,
            last_star_fetch=None,
            
            capabilities=RegistryServerCapabilities(
                deployable=(is_remote_capable or is_hybrid) and not is_local_only,
                connectable=is_local_only or is_hybrid
            ),
            trust=RegistryServerTrust(
                is_official=False,
                last_updated=""
            ),
            install_ref=repo_url
        )

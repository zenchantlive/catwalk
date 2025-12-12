from typing import Optional, Dict, Any

# Global dictionary for in-memory caching to persist across requests (since CacheService is transient)
# In production, use Redis or a Database.
GLOBAL_MEMORY_CACHE: Dict[str, Any] = {}

# Service responsible for caching analysis results to improve performance and reduce costs
class CacheService:
    # Initialize the cache service
    def __init__(self) -> None:
        # Placeholder for DB or Redis connection
        # Use the global dictionary for development persistence
        self._memory_cache = GLOBAL_MEMORY_CACHE

    # Retrieve a cached analysis result by repository URL
    async def get_analysis(self, repo_url: str) -> Optional[Dict[str, Any]]:
        # Look up the URL in the memory cache
        # In the future, this will query the database or Redis
        return self._memory_cache.get(repo_url)

    # Save an analysis result to the cache
    async def set_analysis(self, repo_url: str, data: Dict[str, Any]) -> None:
        # Store the data in the memory cache
        # In the future, this will write to the database or Redis
        self._memory_cache[repo_url] = data

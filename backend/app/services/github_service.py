import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# GitHub API constants
GITHUB_API_BASE = "https://api.github.com"
DEFAULT_TIMEOUT_SECONDS = 10.0
MAX_RETRIES = 3
BACKOFF_FACTOR = 2

# GitHub URL patterns
GITHUB_URL_PATTERNS = [
    re.compile(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$"),
    re.compile(r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$"),
    re.compile(r"^https?://www\.github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$"),
]


class GitHubService:
    """
    Service for interacting with GitHub API to fetch repository information.
    
    Features:
    - URL parsing for various GitHub URL formats
    - Star count fetching without caching (simplified)
    - Rate limiting and error handling
    - Exponential backoff for retries
    """
    
    def __init__(self):
        pass  # No Redis client needed

    def parse_github_url(self, url: str) -> Optional[Tuple[str, str]]:
        """
        Parse GitHub repository URL to extract owner and repository name.
        
        Supports various GitHub URL formats:
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - git@github.com:owner/repo.git
        - https://www.github.com/owner/repo
        
        Args:
            url: GitHub repository URL
            
        Returns:
            Tuple of (owner, repo) if valid GitHub URL, None otherwise
        """
        if not url or not isinstance(url, str):
            return None
            
        url = url.strip()
        if not url:
            return None
            
        for pattern in GITHUB_URL_PATTERNS:
            match = pattern.match(url)
            if match:
                owner, repo = match.groups()
                # Clean up repository name (remove .git suffix if present)
                if repo.endswith('.git'):
                    repo = repo[:-4]
                return owner, repo
                
        return None

    def format_star_count(self, count: int) -> str:
        """
        Format star count for display with appropriate suffixes.
        
        Examples:
        - 42 -> "42"
        - 1234 -> "1.2k"
        - 5678901 -> "5.7M"
        
        Args:
            count: Raw star count
            
        Returns:
            Formatted string representation
        """
        if count < 1000:
            return str(count)
        elif count < 1000000:
            return f"{count / 1000:.1f}k"
        else:
            return f"{count / 1000000:.1f}M"

    async def get_star_count(self, repo_url: str) -> Optional[int]:
        """
        Get star count for a GitHub repository with caching.
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            Star count if successful, None if failed or not a GitHub repo
        """
        parsed = self.parse_github_url(repo_url)
        if not parsed:
            logger.debug(f"Not a valid GitHub URL: {repo_url}")
            return None
            
        owner, repo = parsed
        return await self.get_repository_star_count(owner, repo)

    async def get_repository_star_count(self, owner: str, repo: str) -> Optional[int]:
        """
        Get star count for a specific GitHub repository.
        
        Args:
            owner: Repository owner/organization
            repo: Repository name
            
        Returns:
            Star count if successful, None if failed
        """
        # Fetch directly from GitHub API (no caching)
        return await self._fetch_star_count_from_api(owner, repo)

    async def _fetch_star_count_from_api(self, owner: str, repo: str) -> Optional[int]:
        """
        Fetch star count from GitHub API with retry logic.
        
        Args:
            owner: Repository owner/organization
            repo: Repository name
            
        Returns:
            Star count if successful, None if failed
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Catwalk-Live/1.0"
        }
        
        # Add authentication if token is available
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"
            
        timeout = httpx.Timeout(DEFAULT_TIMEOUT_SECONDS)
        
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(url, headers=headers)
                    
                    # Handle rate limiting
                    if response.status_code == 403:
                        rate_limit_remaining = response.headers.get("X-RateLimit-Remaining", "0")
                        if rate_limit_remaining == "0":
                            reset_time = response.headers.get("X-RateLimit-Reset")
                            if reset_time:
                                reset_datetime = datetime.fromtimestamp(int(reset_time))
                                logger.warning(
                                    f"GitHub API rate limit exceeded. Resets at {reset_datetime}"
                                )
                            else:
                                logger.warning("GitHub API rate limit exceeded")
                            return None
                    
                    # Handle not found
                    if response.status_code == 404:
                        logger.info(f"Repository {owner}/{repo} not found or private")
                        return None
                        
                    # Raise for other HTTP errors
                    response.raise_for_status()
                    
                    data = response.json()
                    star_count = data.get("stargazers_count", 0)
                    
                    logger.debug(f"Fetched star count for {owner}/{repo}: {star_count}")
                    return star_count
                    
            except httpx.TimeoutException:
                logger.warning(f"Timeout fetching {owner}/{repo} (attempt {attempt + 1})")
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (403, 404):
                    # Don't retry for these errors
                    return None
                logger.warning(f"HTTP error fetching {owner}/{repo}: {e} (attempt {attempt + 1})")
            except Exception as e:
                logger.warning(f"Error fetching {owner}/{repo}: {e} (attempt {attempt + 1})")
                
            # Exponential backoff for retries
            if attempt < MAX_RETRIES - 1:
                wait_time = BACKOFF_FACTOR ** attempt
                logger.debug(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                
        logger.error(f"Failed to fetch star count for {owner}/{repo} after {MAX_RETRIES} attempts")
        return None

    async def get_repository_info(self, owner: str, repo: str) -> Optional[Dict]:
        """
        Get comprehensive repository information from GitHub API.
        
        Args:
            owner: Repository owner/organization
            repo: Repository name
            
        Returns:
            Repository info dict if successful, None if failed
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Catwalk-Live/1.0"
        }
        
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"
            
        timeout = httpx.Timeout(DEFAULT_TIMEOUT_SECONDS)
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 404:
                    logger.info(f"Repository {owner}/{repo} not found or private")
                    return None
                    
                response.raise_for_status()
                data = response.json()
                
                return {
                    "owner": data.get("owner", {}).get("login"),
                    "repo": data.get("name"),
                    "full_name": data.get("full_name"),
                    "description": data.get("description"),
                    "star_count": data.get("stargazers_count", 0),
                    "fork_count": data.get("forks_count", 0),
                    "language": data.get("language"),
                    "updated_at": data.get("updated_at"),
                    "created_at": data.get("created_at"),
                    "homepage": data.get("homepage"),
                    "topics": data.get("topics", []),
                }
                
        except Exception as e:
            logger.error(f"Error fetching repository info for {owner}/{repo}: {e}")
            return None

    async def close(self):
        """Close any connections if needed."""
        # No Redis connection to close
        pass


# Global service instance
_github_service: Optional[GitHubService] = None


def get_github_service() -> GitHubService:
    """Get the global GitHub service instance."""
    global _github_service
    if _github_service is None:
        _github_service = GitHubService()
    return _github_service
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.github_service import GitHubService


class TestGitHubService:
    """Test cases for GitHub service functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = GitHubService()

    def test_parse_github_url_valid_https(self):
        """Test parsing valid HTTPS GitHub URLs."""
        test_cases = [
            ("https://github.com/owner/repo", ("owner", "repo")),
            ("https://github.com/owner/repo.git", ("owner", "repo")),
            ("https://github.com/owner/repo/", ("owner", "repo")),
            ("https://www.github.com/owner/repo", ("owner", "repo")),
        ]
        
        for url, expected in test_cases:
            result = self.service.parse_github_url(url)
            assert result == expected, f"Failed for URL: {url}"

    def test_parse_github_url_valid_ssh(self):
        """Test parsing valid SSH GitHub URLs."""
        result = self.service.parse_github_url("git@github.com:owner/repo.git")
        assert result == ("owner", "repo")

    def test_parse_github_url_invalid(self):
        """Test parsing invalid URLs returns None."""
        invalid_urls = [
            "",
            None,
            "https://gitlab.com/owner/repo",
            "https://github.com/owner",
            "not-a-url",
            "https://github.com/",
        ]
        
        for url in invalid_urls:
            result = self.service.parse_github_url(url)
            assert result is None, f"Should return None for: {url}"

    def test_format_star_count(self):
        """Test star count formatting."""
        test_cases = [
            (0, "0"),
            (42, "42"),
            (999, "999"),
            (1000, "1.0k"),
            (1234, "1.2k"),
            (1999, "2.0k"),
            (1000000, "1.0M"),
            (5678901, "5.7M"),
        ]
        
        for count, expected in test_cases:
            result = self.service.format_star_count(count)
            assert result == expected, f"Failed for count: {count}"

    @pytest.mark.asyncio
    async def test_get_star_count_invalid_url(self):
        """Test get_star_count with invalid URL returns None."""
        result = await self.service.get_star_count("https://gitlab.com/owner/repo")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_star_count_valid_url(self):
        """Test get_star_count with valid URL calls repository method."""
        with patch.object(self.service, 'get_repository_star_count', return_value=123) as mock_method:
            result = await self.service.get_star_count("https://github.com/owner/repo")
            assert result == 123
            mock_method.assert_called_once_with("owner", "repo")

    @pytest.mark.asyncio
    async def test_get_repository_star_count_cache_hit(self):
        """Test repository star count with cache hit."""
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "456"
        
        with patch.object(self.service, '_get_redis_client', return_value=mock_redis):
            result = await self.service.get_repository_star_count("owner", "repo")
            
        assert result == 456
        mock_redis.get.assert_called_once_with("github:stars:owner/repo")

    @pytest.mark.asyncio
    async def test_get_repository_star_count_api_fetch(self):
        """Test repository star count with API fetch."""
        # Mock Redis client (cache miss)
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        
        with patch.object(self.service, '_get_redis_client', return_value=mock_redis), \
             patch.object(self.service, '_fetch_star_count_from_api', return_value=789) as mock_fetch:
            
            result = await self.service.get_repository_star_count("owner", "repo")
            
        assert result == 789
        mock_fetch.assert_called_once_with("owner", "repo")
        mock_redis.setex.assert_called_once_with("github:stars:owner/repo", 3600, 789)

    @pytest.mark.asyncio
    async def test_get_repository_star_count_no_redis(self):
        """Test repository star count without Redis."""
        with patch.object(self.service, '_get_redis_client', return_value=None), \
             patch.object(self.service, '_fetch_star_count_from_api', return_value=321) as mock_fetch:
            
            result = await self.service.get_repository_star_count("owner", "repo")
            
        assert result == 321
        mock_fetch.assert_called_once_with("owner", "repo")
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx
from app.services.github_service import get_github_service


class TestGitHubIntegration:
    """Integration tests for GitHub service."""
    
    @pytest.mark.asyncio
    async def test_github_service_end_to_end_mock(self):
        """Test complete GitHub service flow with mocked HTTP response."""
        service = get_github_service()
        
        # Create a proper mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "stargazers_count": 1234,
            "name": "test-repo",
            "full_name": "test-owner/test-repo"
        }
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.AsyncClient.get', return_value=mock_response):
            # Test URL parsing and star count fetching
            star_count = await service.get_star_count("https://github.com/test-owner/test-repo")
            assert star_count == 1234
            
            # Test star count formatting
            formatted = service.format_star_count(star_count)
            assert formatted == "1.2k"

    @pytest.mark.asyncio
    async def test_github_service_with_redis_unavailable(self):
        """Test GitHub service when Redis is unavailable."""
        service = get_github_service()
        
        # Mock Redis to be unavailable
        with patch.object(service, '_get_redis_client', return_value=None):
            # Create a proper mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"stargazers_count": 567}
            mock_response.raise_for_status.return_value = None
            
            with patch('httpx.AsyncClient.get', return_value=mock_response):
                star_count = await service.get_star_count("https://github.com/owner/repo")
                assert star_count == 567

    @pytest.mark.asyncio
    async def test_github_service_rate_limit_handling(self):
        """Test GitHub service handles rate limiting gracefully."""
        service = get_github_service()
        
        # Create a proper mock response for rate limiting
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1640995200"
        }
        
        with patch('httpx.AsyncClient.get', return_value=mock_response):
            star_count = await service.get_star_count("https://github.com/owner/repo")
            assert star_count is None

    @pytest.mark.asyncio
    async def test_github_service_not_found_handling(self):
        """Test GitHub service handles 404 responses gracefully."""
        service = get_github_service()
        
        # Create a proper mock response for 404
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        with patch('httpx.AsyncClient.get', return_value=mock_response):
            star_count = await service.get_star_count("https://github.com/owner/nonexistent-repo")
            assert star_count is None

    @pytest.mark.asyncio
    async def test_github_service_repository_info(self):
        """Test fetching comprehensive repository information."""
        service = get_github_service()
        
        # Create a proper mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "owner": {"login": "test-owner"},
            "name": "test-repo",
            "full_name": "test-owner/test-repo",
            "description": "A test repository",
            "stargazers_count": 42,
            "forks_count": 7,
            "language": "Python",
            "updated_at": "2025-01-04T10:00:00Z",
            "created_at": "2024-01-01T00:00:00Z",
            "homepage": "https://example.com",
            "topics": ["test", "example"]
        }
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.AsyncClient.get', return_value=mock_response):
            info = await service.get_repository_info("test-owner", "test-repo")
            
            assert info is not None
            assert info["owner"] == "test-owner"
            assert info["repo"] == "test-repo"
            assert info["star_count"] == 42
            assert info["language"] == "Python"
            assert info["topics"] == ["test", "example"]
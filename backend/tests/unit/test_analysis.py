from unittest.mock import AsyncMock, patch
import pytest
from app.services.analysis import AnalysisService

@pytest.mark.asyncio
async def test_analyze_repo_success():
    # Mock the AsyncOpenAI client
    with patch("app.services.analysis.AsyncOpenAI") as MockClient:
        # Check if we can instantiate service without API key (it warns but proceeds)
        # OR set env var for test
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "fake-key"}):
            service = AnalysisService()
            
            # Mock the chat.completions.create response
            mock_response = AsyncMock()
            mock_message = AsyncMock()
            mock_message.content = '{"package_name": "test-pkg"}'
            mock_response.choices = [AsyncMock(message=mock_message)]
            
            service.client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            # Run analysis
            result = await service.analyze_repo("https://github.com/test/repo")
            
            # Verify
            assert result["raw_analysis"] == '{"package_name": "test-pkg"}'
            
            # Verify tool was passed
            call_args = service.client.chat.completions.create.call_args
            assert call_args is not None
            assert "tools" in call_args.kwargs
            assert call_args.kwargs["tools"][0]["type"] == "web_search_20250305"

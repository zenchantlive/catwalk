import json
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.analysis import AnalysisService

@pytest.fixture
def analysis_service():
    return AnalysisService()

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def user_id():
    return uuid.uuid4()

@pytest.mark.asyncio
async def test_analyze_repo_success(analysis_service, mock_db, user_id):
    """Test successful repository analysis."""
    repo_url = "https://github.com/test/repo"
    expected_data = {"package_name": "test-pkg", "env_vars": []}
    
    # Mock API keys fetch
    with patch("app.services.analysis.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = (None, "fake-openrouter-key")
        
        # Mock AsyncOpenAI client
        with patch("app.services.analysis.AsyncOpenAI") as MockOpenAI:
            mock_client = MockOpenAI.return_value
            mock_response = MagicMock()
            mock_message = MagicMock()
            mock_message.content = json.dumps(expected_data)
            mock_response.choices = [MagicMock(message=mock_message)]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            result = await analysis_service.analyze_repo(repo_url, user_id, mock_db)
            
            assert result == expected_data
            mock_get_keys.assert_called_once_with(
                user_id=user_id,
                db=mock_db,
                require_user_keys=False
            )
            
            # Verify OpenAI call
            call_args = mock_client.chat.completions.create.call_args
            assert call_args is not None
            kwargs = call_args.kwargs
            assert kwargs["model"] == analysis_service.model
            assert any("system" in m["role"] for m in kwargs["messages"])
            assert repo_url in kwargs["messages"][1]["content"]
            assert "plugins" in kwargs
            assert kwargs["plugins"][0]["id"] == "web"
            assert kwargs["plugins"][0]["max_results"] == 2

@pytest.mark.asyncio
async def test_analyze_repo_missing_api_key(analysis_service, mock_db, user_id):
    """Test failure when no API key is available."""
    with patch("app.services.analysis.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = (None, None)
        
        with pytest.raises(ValueError, match="No OpenRouter API key available"):
            await analysis_service.analyze_repo("https://github.com/test/repo", user_id, mock_db)

@pytest.mark.asyncio
async def test_analyze_repo_json_extraction_markdown(analysis_service, mock_db, user_id):
    """Test extracting JSON from a markdown block."""
    repo_url = "https://github.com/test/repo"
    expected_data = {"package_name": "markdown-pkg"}
    llm_response = f"Here is the config:\n\n```json\n{json.dumps(expected_data)}\n```"
    
    with patch("app.services.analysis.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = (None, "key")
        with patch("app.services.analysis.AsyncOpenAI") as MockOpenAI:
            mock_client = MockOpenAI.return_value
            mock_message = MagicMock()
            mock_message.content = llm_response
            mock_response = MagicMock(choices=[MagicMock(message=mock_message)])
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            result = await analysis_service.analyze_repo(repo_url, user_id, mock_db)
            assert result == expected_data

@pytest.mark.asyncio
async def test_analyze_repo_json_extraction_fallback(analysis_service, mock_db, user_id):
    """Test extracting JSON from text when no markdown block is present."""
    repo_url = "https://github.com/test/repo"
    expected_data = {"package_name": "fallback-pkg"}
    llm_response = f"The config is {json.dumps(expected_data)} hope this helps."
    
    with patch("app.services.analysis.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = (None, "key")
        with patch("app.services.analysis.AsyncOpenAI") as MockOpenAI:
            mock_client = MockOpenAI.return_value
            mock_message = MagicMock()
            mock_message.content = llm_response
            mock_response = MagicMock(choices=[MagicMock(message=mock_message)])
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            result = await analysis_service.analyze_repo(repo_url, user_id, mock_db)
            assert result == expected_data

@pytest.mark.asyncio
async def test_analyze_repo_malformed_json(analysis_service, mock_db, user_id):
    """Test handling of malformed JSON from LLM."""
    llm_response = "This is not JSON at all."
    
    with patch("app.services.analysis.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = (None, "key")
        with patch("app.services.analysis.AsyncOpenAI") as MockOpenAI:
            mock_client = MockOpenAI.return_value
            mock_message = MagicMock()
            mock_message.content = llm_response
            mock_response = MagicMock(choices=[MagicMock(message=mock_message)])
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            result = await analysis_service.analyze_repo("url", user_id, mock_db)
            assert "error" in result
            assert "Failed to parse analysis results" in result["error"]

@pytest.mark.asyncio
async def test_analyze_repo_api_error(analysis_service, mock_db, user_id):
    """Test handling of OpenRouter API exceptions."""
    with patch("app.services.analysis.get_effective_api_keys", new_callable=AsyncMock) as mock_get_keys:
        mock_get_keys.return_value = (None, "key")
        with patch("app.services.analysis.AsyncOpenAI") as MockOpenAI:
            mock_client = MockOpenAI.return_value
            mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API connection failed"))
            
            result = await analysis_service.analyze_repo("url", user_id, mock_db)
            assert "error" in result
            assert "API connection failed" in result["error"]

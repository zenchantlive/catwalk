import json
import logging
import os
import re
import uuid
from typing import Optional, Dict, Any
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.user_api_keys import get_effective_api_keys

logger = logging.getLogger(__name__)

# Service responsible for analyzing GitHub repositories using Claude via OpenRouter
class AnalysisService:
    # Initialize the service with the OpenRouter client
    def __init__(self) -> None:
        """Initialize the service. Client will be created per-request with user's API key."""
        # Define the model to use (Claude Haiku 4.5)
        self.model: str = "anthropic/claude-haiku-4.5"
        ### USER RULE : NEVER EVER CHANGE THE MODEL FROM CLAUDE HAIKU 4.5 UNLESS SPECIFICALLY INSTRUCTED TO DO SO
    ### USER RULE : NEVER EVER CHANGE THE MODEL FROM CLAUDE HAIKU 4.5 UNLESS SPECIFICALLY INSTRUCTED TO DO SO
    # Analyze a GitHub repository to extract MCP configuration
    async def analyze_repo(
        self, 
        repo_url: str, 
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Analyzes a GitHub repository to extract MCP configuration using Claude Haiku 4.5.
        
        Args:
            repo_url: The URL of the GitHub repository to analyze.
            user_id: The user's UUID (for fetching their OpenRouter API key)
            db: Database session
            
        Returns:
            A dictionary containing the extracted configuration (package name, env vars, etc.).
            
        Raises:
            Exception: If the analysis fails or returns invalid data.
        """
        from app.prompts.analysis_prompt import ANALYSIS_SYSTEM_PROMPT
        
        # Get user's OpenRouter API key (with fallback to system key)
        _, openrouter_key = await get_effective_api_keys(
            user_id=user_id,
            db=db,
            require_user_keys=False  # Allow fallback to system key
        )
        
        if not openrouter_key:
            raise ValueError(
                "No OpenRouter API key available. Please add your OpenRouter API key "
                "in Settings (/settings) to analyze GitHub repositories."
            )
        
        # Create client with user's API key
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key
        )
        
        try:
            # Call the OpenRouter API with LIMITED web search to avoid context overflow
            # Limit to 2 results to stay within 200k token limit (error showed 235k tokens)
            response = await client.chat.completions.create(
                model=self.model,  # Use base model, not :online suffix
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this MCP server repository: {repo_url}"}
                ],
                # Enable web search with strict limit on results
                plugins=[{
                    "id": "web",
                    "max_results": 2  # Limit to 2 results to avoid context overflow
                }],
            )
            
            # Extract the content from the response
            content = response.choices[0].message.content
            
            # Clean and parse the JSON content
            cleaned_content = content.strip()
            # More robustly find the JSON block
            json_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned_content, re.DOTALL)
            if json_match:
                cleaned_content = json_match.group(1)
            else:
                # Fallback to finding the first and last curly brace
                start_brace = cleaned_content.find('{')
                end_brace = cleaned_content.rfind('}')
                if start_brace != -1 and end_brace > start_brace:
                    cleaned_content = cleaned_content[start_brace : end_brace + 1]
            
            try:
                parsed_data = json.loads(cleaned_content)
                return parsed_data
            except json.JSONDecodeError:
                # Fallback or error if parsing fails
                logger.error("Failed to parse JSON analysis: %s", cleaned_content)
                return {"error": "Failed to parse analysis results", "raw": content}
            
        except Exception as e:
            # Log the error (in a real app) and re-raise or return error status
            logger.error(f"Error analyzing repo {repo_url}: {str(e)}")
            return {"error": str(e), "status": "failed"}

import os
from typing import Optional, Dict, Any
from openai import AsyncOpenAI

from app.core.config import settings

# Service responsible for analyzing GitHub repositories using Claude via OpenRouter
class AnalysisService:
    # Initialize the service with the OpenRouter client
    def __init__(self) -> None:
        # Get the API key from environment variables
        api_key: Optional[str] = settings.OPENROUTER_API_KEY
        if not api_key:
            # Handle missing API key case (could raise error or log warning)
            print("Warning: OPENROUTER_API_KEY not found in environment variables.")
        
        # Initialize the AsyncOpenAI client pointing to OpenRouter
        self.client: AsyncOpenAI = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        
        # Define the model to use (Claude Haiku 4.5)
        self.model: str = "anthropic/claude-haiku-4.5"
### USER RULE : NEVER EVER CHANGE THE MODEL FROM CLAUDE HAIKU 4.5 UNLESS SPECIFICALLY INSTRUCTED TO DO SO
    # Analyze a GitHub repository to extract MCP configuration
    async def analyze_repo(self, repo_url: str) -> Dict[str, Any]:
        """
        Analyzes a GitHub repository to extract MCP configuration using Claude Haiku 4.5.
        
        Args:
            repo_url: The URL of the GitHub repository to analyze.
            
        Returns:
            A dictionary containing the extracted configuration (package name, env vars, etc.).
            
        Raises:
            Exception: If the analysis fails or returns invalid data.
        """
        from app.prompts.analysis_prompt import ANALYSIS_SYSTEM_PROMPT
        
        try:
            # Construct the tools list with the web search tool
            tools = [
                {
                    "type": "web_search_20250305",
                    "name": "web_search"
                }
            ]
            
            # Call the OpenRouter API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this MCP server repository: {repo_url}"}
                ],
                tools=tools,
                # Enforce JSON output for cleaner parsing (if supported by model/provider)
                # otherwise rely on instructions. Haiku 4.5 usually follows instructions well.
                # response_format={"type": "json_object"} 
            )
            
            # Extract the content from the response
            content = response.choices[0].message.content
            
            # Clean and parse the JSON content
            import json
            import re
            
            cleaned_content = content.strip()
            # Remove markdown code blocks if present
            if "```" in cleaned_content:
                cleaned_content = re.sub(r"^```json\s*", "", cleaned_content, flags=re.MULTILINE)
                cleaned_content = re.sub(r"^```\s*", "", cleaned_content, flags=re.MULTILINE)
                cleaned_content = re.sub(r"```$", "", cleaned_content, flags=re.MULTILINE).strip()
            
            try:
                parsed_data = json.loads(cleaned_content)
                return parsed_data
            except json.JSONDecodeError:
                # Fallback or error if parsing fails
                print(f"Failed to parse JSON analysis: {cleaned_content}")
                return {"error": "Failed to parse analysis results", "raw": content}
            
        except Exception as e:
            # Log the error (in a real app) and re-raise or return error status
            print(f"Error analyzing repo {repo_url}: {str(e)}")
            return {"error": str(e), "status": "failed"}

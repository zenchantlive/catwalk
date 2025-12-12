from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Literal, Optional
from app.schemas.dynamic_form import FormSchema, FormField
from app.core.form_schemas import FORM_SCHEMAS
from app.services.cache import CacheService
import json

# Create a new APIRouter instance for form-related endpoints
router = APIRouter()

from app.services.analysis import AnalysisService

def get_cache_service():
    return CacheService()

def get_analysis_service():
    return AnalysisService()

@router.get("/generate/{service_type}", response_model=FormSchema)
async def get_form_schema(
    service_type: str,
    repo_url: Optional[str] = Query(None),
    cache_service: CacheService = Depends(get_cache_service),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Generate a dynamic form schema for a specific service type.
    """
    
    # 1. Handle "custom" dynamic generation if repo_url is provided
    if service_type == "custom" and repo_url:
        analysis = await cache_service.get_analysis(repo_url)
        
        if not analysis:
            # Fallback: Run analysis on the fly if cache is missing
            print(f"Cache miss for {repo_url}. Running analysis on the fly...")
            analysis = await analysis_service.analyze_repo(repo_url)
            
            # Use 'error' check from analyze_repo return format
            if "error" in analysis:
                return FormSchema(
                    title="Analysis Failed",
                    description=f"Could not analyze repository: {analysis['error']}",
                    fields=[]
                )
             
            # Cache the new result
            await cache_service.set_analysis(repo_url, analysis)
            
        # Parse analysis, assuming it has a structure.
            
        # Parse analysis, assuming it has a structure. 
        # For now, let's wrap the logic in a try-catch to be safe
        try:
            # The analysis might be a raw string JSON or a dict
            if isinstance(analysis, dict) and "raw_analysis" in analysis:
                # Try to parse the inner JSON if the prompt returned it as a string
                raw_content = analysis["raw_analysis"]
                # Heuristic: find the first { and last }
                start = raw_content.find("{")
                end = raw_content.rfind("}") + 1
                if start != -1 and end != -1:
                   json_str = raw_content[start:end]
                   try:
                       data = json.loads(json_str)
                   except json.JSONDecodeError as e:
                       if e.msg.startswith("Extra data"):
                           # Try to parse just the valid part up to the error
                           try:
                               data = json.loads(json_str[:e.pos])
                           except Exception:
                               print(f"Failed to recover JSON from extra data error: {e}")
                               data = {}
                       else:
                           print(f"JSON decode error: {e}")
                           data = {}
                else:
                   data = {} # Fallback
            else:
                data = analysis
                
            # Extract fields
            fields = []
            
            # Common fields
            fields.append(FormField(name="name", label="Deployment Name", type="text", required=True, default=data.get("name", "New Deployment")))
             
            # Environment Variables
            env_vars = data.get("env_vars", [])
            for env in env_vars:
                # Extract key logic (e.g. if it's a dict or str)
                key = env if isinstance(env, str) else env.get("name")
                # Heuristic for type
                ftype = "password" if "KEY" in key.upper() or "SECRET" in key.upper() or "TOKEN" in key.upper() else "text"
                fields.append(FormField(name=f"env_{key}", label=key, type=ftype, required=True, description=f"Environment variable for {key}"))

            # Extract MCP server configuration (tools, resources, prompts, package)
            # This will be passed to the frontend and included in schedule_config when creating deployment
            mcp_config = {
                "package": data.get("package") or data.get("npm_package") or data.get("package_name"),
                "tools": data.get("tools", []),
                "resources": data.get("resources", []),
                "prompts": data.get("prompts", []),
                "server_info": {
                    "name": data.get("name", "Unknown Server"),
                    "version": data.get("version", "0.1.0"),
                    "description": data.get("description", "")
                }
            }

            return FormSchema(
                title=f"Configure {data.get('name', 'Deployment')}",
                description=data.get("description", "Enter the required configuration."),
                fields=fields,
                mcp_config=mcp_config
            )
            
        except Exception as e:
            print(f"Error generating form: {e}")
            # Fallback
            return FormSchema(title="Configuration Error", description="Failed to generate form.", fields=[])

    # 2. Handle Static Schemas
    # Retrieve the schema from the centralized configuration
    schema = FORM_SCHEMAS.get(service_type)
    
    if not schema:
         # If requesting 'custom' but no repo_url, or unknown type
         if service_type == "custom":
             return FormSchema(title="Missing Repository", description="No repository URL provided.", fields=[])
         
         raise HTTPException(status_code=404, detail="Service schema not found")
        
    return schema

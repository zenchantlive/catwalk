import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.form_schemas import FORM_SCHEMAS
from app.db.session import get_db
from app.schemas.dynamic_form import FormField, FormSchema
from app.services.analysis import AnalysisService
from app.services.cache import CacheService
from app.services.registry_service import RegistryService

# Create a new APIRouter instance for form-related endpoints
router = APIRouter()

def get_cache_service(db: AsyncSession = Depends(get_db)):
    return CacheService(db)

def get_analysis_service():
    return AnalysisService()

def get_registry_service():
    return RegistryService.get_instance()

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
                               print(
                                   "Failed to recover JSON from extra data error: "
                                   f"{e}"
                               )
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
            fields.append(
                FormField(
                    name="name",
                    label="Deployment Name",
                    type="text",
                    required=True,
                    default=data.get("name", "New Deployment"),
                )
            )
             
            # Environment Variables
            env_vars = data.get("env_vars", [])
            for env in env_vars:
                # Extract key logic (e.g. if it's a dict or str)
                key = env if isinstance(env, str) else env.get("name")
                # Heuristic for type
                is_secret = any(
                    token in key.upper()
                    for token in ("KEY", "SECRET", "TOKEN")
                )
                ftype = "password" if is_secret else "text"
                fields.append(
                    FormField(
                        name=f"env_{key}",
                        label=key,
                        type=ftype,
                        required=True,
                        description=f"Environment variable for {key}",
                    )
                )

            # Extract MCP server configuration (tools, resources, prompts, package)
            # This will be passed to the frontend and included in schedule_config
            # when creating deployment.
            mcp_config = {
                "package": (
                    data.get("package")
                    or data.get("npm_package")
                    or data.get("package_name")
                ),
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
                description=data.get(
                    "description",
                    "Enter the required configuration.",
                ),
                fields=fields,
                mcp_config=mcp_config
            )
            
        except Exception as e:
            print(f"Error generating form: {e}")
            # Fallback
            return FormSchema(
                title="Configuration Error",
                description="Failed to generate form.",
                fields=[],
            )

    # 2. Handle Static Schemas
    # Retrieve the schema from the centralized configuration
    schema = FORM_SCHEMAS.get(service_type)
    
    if not schema:
         # If requesting 'custom' but no repo_url, or unknown type
         if service_type == "custom":
             return FormSchema(
                 title="Missing Repository",
                 description="No repository URL provided.",
                 fields=[],
             )
         
         raise HTTPException(status_code=404, detail="Service schema not found")

    return schema

@router.get("/generate/registry/{registry_id:path}", response_model=FormSchema)
async def get_registry_form_schema(
    registry_id: str,
    registry_service: RegistryService = Depends(get_registry_service)
):
    """
    Generate form schema directly from Glama registry API data (no LLM analysis).

    Glama provides environmentVariablesJsonSchema for form generation, eliminating
    the need to run expensive repository analysis for registry deployments.

    Args:
        registry_id: Full registry ID (e.g., "ai.exa/exa")

    Returns:
        FormSchema with fields for environment variables and mcp_config

    Raises:
        HTTPException 404: Registry server not found
        HTTPException 400: Server not deployable (no packages)
        HTTPException 500: Failed to parse registry data
    """
    try:
        # Fetch server from Glama cache
        server = await registry_service.get_server(registry_id)
        if not server:
            raise HTTPException(
                status_code=404,
                detail=f"Server '{registry_id}' not found in Glama registry",
            )

        # Verify server is deployable
        if not server.capabilities.deployable:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Server '{registry_id}' is local-only and cannot be deployed "
                    f"to cloud. "
                    f"Please use a remote-capable server."
                )
            )

        # Extract form data from Glama JSON Schema
        form_data = registry_service.extract_form_data(server)

        # Build form fields
        fields = []

        # Deployment name field (always required)
        fields.append(
            FormField(
                name="name",
                label="Deployment Name",
                type="text",
                required=True,
                default=form_data["name"],
                description="A friendly name for this deployment"
            )
        )

        # Environment variable fields
        for env_var in form_data["env_vars"]:
            field_type = "text"
            if env_var.get("options"):
                field_type = "select"
            elif env_var.get("format") in ("boolean", "bool"):
                field_type = "checkbox"
            elif env_var.get("format") in ("number", "integer", "int"):
                field_type = "number"
            elif env_var.get("secret"):
                field_type = "password"

            fields.append(
                FormField(
                    name=f"env_{env_var['name']}",
                    label=env_var['name'],
                    type=field_type,
                    required=env_var["required"],
                    default=env_var.get("default"),
                    options=env_var.get("options"),
                    description=env_var["description"]
                    or f"Environment variable: {env_var['name']}",
                )
            )

        raw_server = registry_service.get_raw_server(registry_id) or {}

        # Build mcp_config (Glama can provide richer metadata than the legacy registry)
        mcp_config = {
            "package": form_data["package"],
            "tools": raw_server.get("tools", []),
            "resources": raw_server.get("resources", []),
            "prompts": raw_server.get("prompts", []),
            "server_info": {
                "name": form_data["name"],
                "version": form_data["version"],
                "description": form_data["description"],
                "source": "glama",
                "registry_id": registry_id,
                "glama_id": registry_id,
                "glama_url": raw_server.get("url", ""),
                "license": (raw_server.get("spdxLicense", {}) or {}).get("name", ""),
                "is_official": False,
            }
        }

        return FormSchema(
            title=f"Configure {form_data['name']}",
            description=form_data["description"]
            or f"Configure environment variables for {form_data['name']}",
            fields=fields,
            mcp_config=mcp_config
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        # Handle extraction errors (missing raw server payload, etc.)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log unexpected errors and return 500
        print(f"Error generating registry form for {registry_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate form schema: {str(e)}"
        )

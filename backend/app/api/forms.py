from fastapi import APIRouter, HTTPException
from typing import Literal
from app.schemas.dynamic_form import FormSchema, FormField

# Create a new APIRouter instance for form-related endpoints
router = APIRouter()

@router.get("/generate/{service_type}", response_model=FormSchema)
async def get_form_schema(service_type: Literal["openai", "anthropic", "github"]):
    """
    Generate a dynamic form schema for a specific service type.
    
    Args:
        service_type (str): The type of service to generate a form for. 
                            Supported: "openai", "anthropic", "github".
                            
    Returns:
        FormSchema: The JSON schema defining the title, description, and fields for the form.
    """
    
    # Logic to return specific schemas based on the service type
    if service_type == "openai":
        # Schema for OpenAI configuration
        return FormSchema(
            title="Configure OpenAI",
            description="Enter your OpenAI API key to enable AI analysis features.",
            fields=[
                FormField(
                    name="api_key",
                    label="API Key",
                    type="password",
                    required=True,
                    description="Starts with sk-..."
                ),
                FormField(
                    name="model",
                    label="Default Model",
                    type="select",
                    options=["gpt-4", "gpt-3.5-turbo"],
                    default="gpt-4"
                )
            ]
        )
    
    elif service_type == "anthropic":
        # Schema for Anthropic configuration
        return FormSchema(
            title="Configure Anthropic",
            description="Enter your Anthropic API key.",
            fields=[
                FormField(
                    name="api_key",
                    label="API Key",
                    type="password",
                    required=True,
                    description="Starts with sk-ant-..."
                )
            ]
        )
        
    elif service_type == "github":
        # Schema for GitHub configuration
        return FormSchema(
            title="Configure GitHub",
            description="Connect your GitHub account.",
            fields=[
                FormField(
                    name="token",
                    label="Personal Access Token",
                    type="password",
                    required=True,
                    description="GitHub PAT with repo scope"
                )
            ]
        )
    
    # Fallback error if service type matches type hint but logic is missing (should be unreachable due to Literal)
    raise HTTPException(status_code=400, detail="Unsupported service type")

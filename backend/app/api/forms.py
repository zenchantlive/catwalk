from fastapi import APIRouter, HTTPException
from typing import Literal
from app.schemas.dynamic_form import FormSchema
from app.core.form_schemas import FORM_SCHEMAS

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
        
    Raises:
        HTTPException: If the service type is not found in the configuration.
    """
    
    # Retrieve the schema from the centralized configuration
    schema = FORM_SCHEMAS.get(service_type)
    
    # Validation check (though Literal type hint catches most cases during request parsing if strict mode is on)
    if not schema:
        raise HTTPException(status_code=404, detail="Service schema not found")
        
    return schema

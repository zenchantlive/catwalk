from typing import Any, List, Optional, Literal
from pydantic import BaseModel, Field

class FormField(BaseModel):
    """
    Represents a single input field in a dynamic form.
    Used by the frontend to render the appropriate input control.
    """
    # Unique identifier for the field (e.g., 'api_key', 'model_name')
    name: str = Field(..., description="The key to be used in the submitted JSON payload")
    
    # Human-readable label for the field
    label: str = Field(..., description="The label displayed to the user")
    
    # Input type hints for frontend rendering
    # text: Standard text input
    # password: Masked text input for secrets
    # select: Dropdown menu (requires 'options' to be set)
    # number: Numeric input
    # checkbox: Boolean toggle
    type: Literal["text", "password", "select", "number", "checkbox"] = Field(
        ..., description="The type of input control to render"
    )
    
    # Whether the field must be filled out before submission
    required: bool = Field(True, description="If True, the field is mandatory")
    
    # Default value for the field, if any
    default: Any | None = Field(None, description="Default value to pre-fill")
    
    # List of options for 'select' type fields
    options: List[str] | None = Field(None, description="Dropdown options, required if type is 'select'")
    
    # Helper text or tooltip to guide the user
    description: str | None = Field(None, description="Helper text/tooltip for the field")

class FormSchema(BaseModel):
    """
    Represents the complete structure of a dynamic form.
    Contains metadata and the list of fields to render.
    """
    # Title of the form (e.g., "Configure OpenAI")
    title: str = Field(..., description="The header title of the form")

    # Brief explanation of what the form is for
    description: str = Field(..., description="Instructional text under the title")

    # Ordered list of fields to display
    fields: List[FormField] = Field(..., description="List of fields to render in order")

    # MCP server configuration metadata (tools, resources, prompts, package)
    # This metadata will be included in schedule_config.mcp_config when creating deployment
    # The frontend should pass this through without modification
    mcp_config: Any | None = Field(None, description="MCP server configuration (tools, package, etc.)")

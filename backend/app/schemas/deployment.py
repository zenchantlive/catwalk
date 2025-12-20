from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID

class DeploymentBase(BaseModel):
    name: str
    schedule_config: Dict[str, Any] = {}
    status: str = "inactive"

class DeploymentCreate(DeploymentBase):
    # Dictionary of service_name -> secret_value
    # e.g., {"openai": "sk-...", "ticktick": "username:password"}
    credentials: Dict[str, str]

class DeploymentResponse(DeploymentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    connection_url: str  # Computed field
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

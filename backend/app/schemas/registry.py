from pydantic import BaseModel
from typing import List, Optional, Dict, Literal

class RegistryServerCapabilities(BaseModel):
    deployable: bool
    connectable: bool

class RegistryServerTrust(BaseModel):
    is_official: bool
    last_updated: str

class RegistryServer(BaseModel):
    id: str  # e.g. "ai.exa/exa"
    name: str
    namespace: str
    description: str
    version: str
    homepage: Optional[str] = None
    repository_url: Optional[str] = None
    
    # Capabilities & Trust
    capabilities: RegistryServerCapabilities
    trust: RegistryServerTrust
    
    # For Installation/Deployment
    install_ref: Optional[str] = None # e.g. "docker.io/aliengiraffe/spotdb:0.1.0"
    
class RegistrySearchParams(BaseModel):
    query: Optional[str] = None
    limit: int = 50
    offset: int = 0

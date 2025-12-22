import httpx
import logging
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.services.user_api_keys import get_effective_api_keys

logger = logging.getLogger(__name__)

class FlyDeploymentService:
    def __init__(self):
        """Initialize service with system-level configuration. API token is fetched per-request."""
        self.app_name = settings.FLY_MCP_APP_NAME
        self.base_url = "https://api.machines.dev/v1"
        self.image = settings.FLY_MCP_IMAGE

        # CRITICAL: Log the configuration on initialization for observability
        logger.info(f"FlyDeploymentService initialized:")
        logger.info(f"  - App Name: {self.app_name}")
        logger.info(f"  - Image: {self.image if self.image else 'NOT SET (WILL FAIL!)'}")
        logger.info(f"  - API Token: Will be fetched per-user")

    def _get_headers(self, api_token: str) -> Dict[str, str]:
        """Generate headers with the provided API token."""
        if not api_token:
            logger.warning("FLY_API_TOKEN is not set. Fly.io deployment will fail.")
        return {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

    async def create_machine(
        self,
        deployment_id: str,
        mcp_config: Dict[str, Any],
        credentials: Dict[str, str],
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> Optional[str]:
        """
        Create a Fly machine for the given deployment using user's Fly.io API token.

        Args:
            deployment_id: The unique ID of the deployment.
            mcp_config: Configuration containing package name, etc.
            credentials: Dictionary of environment variables to inject.
            user_id: The user's UUID (for fetching their Fly.io API token)
            db: Database session

        Returns:
            machine_id: The ID of the created machine, or None if failed.
        """
        # Get user's Fly.io API token (with fallback to system key)
        fly_api_token, _ = await get_effective_api_keys(
            user_id=user_id,
            db=db,
            require_user_keys=False  # Allow fallback to system key
        )
        
        # CRITICAL: Fail fast if no API token available
        if not fly_api_token:
            logger.error("Cannot create machine: No FLY_API_TOKEN available (neither user nor system)")
            raise ValueError(
                "No Fly.io API token available. Please add your Fly.io API token "
                "in Settings (/settings) to create deployments."
            )

        if not self.image:
            logger.error("Cannot create machine: FLY_MCP_IMAGE is not set")
            raise ValueError(
                "FLY_MCP_IMAGE is not configured. Set this environment variable to a valid Docker image "
                "(e.g., registry.fly.io/your-app:latest) before deploying MCP servers."
            )

        # Extract package name from config
        package = mcp_config.get("package")
        if not package:
            logger.error(f"Cannot create machine for {deployment_id}: No package specified in config")
            raise ValueError("No 'package' specified in MCP configuration.")

        # Prepare environment variables
        env = credentials.copy()
        env["MCP_PACKAGE"] = package
        env["DEPLOYMENT_ID"] = deployment_id
        
        # Machine configuration
        # Using a shared CPU (lowest cost)
        config = {
            "config": {
                "image": self.image,
                "guest": {
                    "cpu_kind": "shared",
                    "cpus": 1,
                    "memory_mb": 256
                },
                "env": env,
                # No external services needed - internal-only communication via private network
                # Machines in the same org can communicate directly via IPv6
                "restart": {
                    "policy": "always"
                }
            }
        }

        url = f"{self.base_url}/apps/{self.app_name}/machines"
        
        logger.info(f"Creating Fly machine for deployment {deployment_id} with package {package}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, 
                    json=config, 
                    headers=self._get_headers(fly_api_token), 
                    timeout=30.0
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    machine_id = data.get("id")
                    logger.info(f"Successfully created machine {machine_id} for deployment {deployment_id}")
                    return machine_id
                else:
                    error_text = response.text
                    logger.error(f"Failed to create machine: {response.status_code} - {error_text}")
                    raise Exception(f"Fly.io API Error ({response.status_code}): {error_text}")
            except Exception as e:
                logger.error(f"Error creating Fly machine: {str(e)}")
                raise e

    async def get_machine(
        self, 
        machine_id: str,
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Get details of a specific machine using user's Fly.io API token."""
        # Get user's Fly.io API token
        fly_api_token, _ = await get_effective_api_keys(
            user_id=user_id,
            db=db,
            require_user_keys=False
        )
        
        if not fly_api_token:
            raise ValueError("No Fly.io API token available.")
            
        url = f"{self.base_url}/apps/{self.app_name}/machines/{machine_id}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, 
                    headers=self._get_headers(fly_api_token),
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except Exception as e:
                logger.error(f"Error getting machine {machine_id}: {str(e)}")
                return None

    async def delete_machine(
        self, 
        machine_id: str,
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> bool:
        """Destroy a Fly machine using user's Fly.io API token."""
        # Get user's Fly.io API token
        fly_api_token, _ = await get_effective_api_keys(
            user_id=user_id,
            db=db,
            require_user_keys=False
        )
        
        if not fly_api_token:
            raise ValueError("No Fly.io API token available.")
            
        # Machine must be stopped before destruction? 
        # The API usually allows force=true
        url = f"{self.base_url}/apps/{self.app_name}/machines/{machine_id}?force=true"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    url, 
                    headers=self._get_headers(fly_api_token),
                    timeout=10.0
                )
                if response.status_code in (200, 202):
                    logger.info(f"Successfully deleted machine {machine_id}")
                    return True
                logger.error(f"Failed to delete machine {machine_id}: {response.status_code} - {response.text}")
                return False
            except Exception as e:
                logger.error(f"Error deleting machine {machine_id}: {str(e)}")
                return False

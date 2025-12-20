import httpx
import logging
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class FlyDeploymentService:
    def __init__(self):
        self.api_token = settings.FLY_API_TOKEN
        self.app_name = settings.FLY_MCP_APP_NAME
        self.base_url = "https://api.machines.dev/v1"
        self.image = settings.FLY_MCP_IMAGE

        # CRITICAL: Log the configuration on initialization for observability
        logger.info(f"FlyDeploymentService initialized:")
        logger.info(f"  - App Name: {self.app_name}")
        logger.info(f"  - Image: {self.image if self.image else 'NOT SET (WILL FAIL!)'}")
        logger.info(f"  - API Token: {'SET' if self.api_token else 'NOT SET'}")

    def _get_headers(self) -> Dict[str, str]:
        if not self.api_token:
            logger.warning("FLY_API_TOKEN is not set. Fly.io deployment will fail.")
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    async def create_machine(
        self,
        deployment_id: str,
        mcp_config: Dict[str, Any],
        credentials: Dict[str, str]
    ) -> Optional[str]:
        """
        Create a Fly machine for the given deployment.

        Args:
            deployment_id: The unique ID of the deployment.
            mcp_config: Configuration containing package name, etc.
            credentials: Dictionary of environment variables to inject.

        Returns:
            machine_id: The ID of the created machine, or None if failed.
        """
        # CRITICAL: Fail fast if configuration is invalid
        if not self.api_token:
            logger.error("Cannot create machine: FLY_API_TOKEN is missing")
            raise ValueError("FLY_API_TOKEN is not configured on the backend.")

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
                    headers=self._get_headers(), 
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

    async def get_machine(self, machine_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific machine."""
        if not self.api_token:
            raise ValueError("FLY_API_TOKEN is not configured on the backend.")
            
        url = f"{self.base_url}/apps/{self.app_name}/machines/{machine_id}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, 
                    headers=self._get_headers(),
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except Exception as e:
                logger.error(f"Error getting machine {machine_id}: {str(e)}")
                return None

    async def delete_machine(self, machine_id: str) -> bool:
        """Destroy a Fly machine."""
        if not self.api_token:
            raise ValueError("FLY_API_TOKEN is not configured on the backend.")
            
        # Machine must be stopped before destruction? 
        # The API usually allows force=true
        url = f"{self.base_url}/apps/{self.app_name}/machines/{machine_id}?force=true"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    url, 
                    headers=self._get_headers(),
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

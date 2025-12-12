from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.session import get_db
from app.models.deployment import Deployment
from app.models.credential import Credential
from app.schemas.deployment import DeploymentCreate, DeploymentResponse
from app.services.encryption import EncryptionService
from app.services.mcp_process_manager import start_server
from app.core.config import settings
import logging

router = APIRouter()
encryption_service = EncryptionService()
logger = logging.getLogger(__name__)

@router.post("", response_model=DeploymentResponse)
async def create_deployment(
    deployment_in: DeploymentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # 1. Create Deployment Record
    deployment = Deployment(
        name=deployment_in.name,
        schedule_config=deployment_in.schedule_config,
        status="active" # Auto-activate for now
    )
    db.add(deployment)
    await db.flush() # Generate ID without committing yet

    # 2. Encrypt and Save Credentials
    for service, secret in deployment_in.credentials.items():
        encrypted_val = encryption_service.encrypt(secret)
        credential = Credential(
            service_name=service,
            encrypted_data=encrypted_val,
            deployment_id=deployment.id
        )
        db.add(credential)

    await db.commit()
    await db.refresh(deployment)

    # 3. Start the MCP server subprocess (if package is configured)
    mcp_config = deployment.schedule_config.get("mcp_config", {}) if deployment.schedule_config else {}
    package = mcp_config.get("package")

    logger.info(f"Deployment {deployment.id} MCP config: {mcp_config}")
    logger.info(f"Extracted package: {package}")

    if package:
        # Query credentials separately to avoid greenlet issues
        credentials_result = await db.execute(
            select(Credential).where(Credential.deployment_id == deployment.id)
        )
        credentials = credentials_result.scalars().all()

        # Prepare environment variables from credentials
        env_vars = {}
        for cred in credentials:
            # Decrypt the credential value
            decrypted_value = encryption_service.decrypt(cred.encrypted_data)
            # Add to env vars (use service_name as env var name)
            env_vars[cred.service_name] = decrypted_value

        logger.info(f"Starting MCP server for deployment {deployment.id}: {package}")

        # Start the MCP server process
        success = await start_server(
            deployment_id=str(deployment.id),
            package=package,
            env_vars=env_vars
        )

        if not success:
            logger.error(f"Failed to start MCP server for deployment {deployment.id}")
            # Don't fail the deployment creation, just log the error
            # The deployment can still be used, but tool calls will fail
    else:
        logger.warning(f"No package configured for deployment {deployment.id}, skipping server start")

    # 4. Construct Response
    # Base URL + /api/mcp/{id} (Streamable HTTP unified endpoint)
    # Use PUBLIC_URL if set, otherwise fallback to request.base_url
    base_url = settings.PUBLIC_URL if settings.PUBLIC_URL else str(request.base_url).rstrip("/")
    # New MCP Streamable HTTP transport uses single unified endpoint (no /sse suffix)
    connection_url = f"{base_url}{settings.API_V1_STR}/mcp/{deployment.id}"
    
    # Map to Pydantic
    response = DeploymentResponse(
        id=deployment.id,
        name=deployment.name,
        status=deployment.status,
        schedule_config=deployment.schedule_config,
        created_at=deployment.created_at,
        updated_at=deployment.updated_at,
        connection_url=connection_url
    )
    return response

@router.get("", response_model=List[DeploymentResponse])
async def list_deployments(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Deployment))
    deployments = result.scalars().all()
    
    responses = []
    base_url = settings.PUBLIC_URL if settings.PUBLIC_URL else str(request.base_url).rstrip("/")

    for d in deployments:
        # New MCP Streamable HTTP transport uses single unified endpoint (no /sse suffix)
        connection_url = f"{base_url}{settings.API_V1_STR}/mcp/{d.id}"
        responses.append(DeploymentResponse(
            id=d.id,
            name=d.name,
            status=d.status,
            schedule_config=d.schedule_config,
            created_at=d.created_at,
            updated_at=d.updated_at,
            connection_url=connection_url
        ))
        
    return responses

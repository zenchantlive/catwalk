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

    # 3. Start the MCP server
    mcp_config = deployment.schedule_config.get("mcp_config", {}) if deployment.schedule_config else {}
    package = mcp_config.get("package")

    logger.info(f"Deployment {deployment.id} MCP config: {mcp_config}")
    logger.info(f"Extracted package: {package}")

    if package:
        try:
            # Query credentials separately to avoid greenlet issues
            credentials_result = await db.execute(
                select(Credential).where(Credential.deployment_id == deployment.id)
            )
            credentials_list = credentials_result.scalars().all()

            # Prepare environment variables from credentials
            env_vars = {}
            for cred in credentials_list:
                # Decrypt the credential value
                decrypted_value = encryption_service.decrypt(cred.encrypted_data)
                # Strip 'env_' prefix from service_name to get actual env var name
                # e.g., 'env_TICKTICK_CLIENT_ID' -> 'TICKTICK_CLIENT_ID'
                env_var_name = cred.service_name.removeprefix("env_")
                env_vars[env_var_name] = decrypted_value

            logger.info(f"Starting MCP server for deployment {deployment.id}: {package}")

            # CHECK FOR FLY.IO DEPLOYMENT FIRST
            if settings.FLY_API_TOKEN:
                from app.services.fly_deployment_service import FlyDeploymentService
                fly_service = FlyDeploymentService()
                
                logger.info("FLY_API_TOKEN found, attempting to create Fly.io machine...")
                machine_id = await fly_service.create_machine(
                    deployment_id=str(deployment.id),
                    mcp_config=mcp_config,
                    credentials=env_vars
                )
                
                if machine_id:
                    deployment.machine_id = machine_id
                    deployment.status = "running"
                    await db.commit()
                    logger.info(f"Fly machine {machine_id} started successfully")
                else:
                    # Should be unreachable if create_machine raises exception on failure
                    deployment.status = "failed"
                    deployment.error_message = "Unknown error: Machine ID not returned"
                    await db.commit()
                    
            else:
                # FALLBACK TO LOCAL SUBPROCESS (Dev/WSL2 only)
                logger.info("No FLY_API_TOKEN, falling back to local subprocess manager")
                success = await start_server(
                    deployment_id=str(deployment.id),
                    package=package,
                    env_vars=env_vars
                )

                if not success:
                    deployment.status = "failed"
                    deployment.error_message = "Failed to start local subprocess"
                    await db.commit()
                    logger.error(f"Failed to start local MCP server for deployment {deployment.id}")

        except Exception as e:
            logger.exception(f"Deployment failed for {deployment.id}")
            deployment.status = "failed"
            deployment.error_message = str(e)
            await db.commit()
    else:
        deployment.status = "failed"
        deployment.error_message = "No 'package' specified in MCP config"
        await db.commit()
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
        connection_url=connection_url,
        error_message=deployment.error_message
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
            connection_url=connection_url,
            error_message=d.error_message
        ))
        
    return responses

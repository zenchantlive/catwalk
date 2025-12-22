from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Dict
from app.db.session import get_db
from app.models.deployment import Deployment
from app.models.credential import Credential
from app.models.user import User
from app.core.auth import get_current_user
from app.schemas.deployment import DeploymentCreate, DeploymentResponse
from app.services.encryption import EncryptionService
from app.services.mcp_process_manager import start_server
from app.services.package_validator import PackageValidator
from app.services.credential_validator import CredentialValidator
from app.core.config import settings
import logging
import json

router = APIRouter()
encryption_service = EncryptionService()
package_validator = PackageValidator()
credential_validator = CredentialValidator()
logger = logging.getLogger(__name__)


def _get_error_help(error_type: str, package: str = None) -> str:
    """Return actionable help text for different error types"""
    help_messages = {
        "package_not_found": f"Verify '{package}' is published to npm or PyPI. Check spelling and package name.",
        "credential_validation_failed": "Provide all required credentials. Check the credential form for required fields.",
        "package_validation_failed": "Could not validate package. Check your internet connection or try again later.",
        "runtime_detection_failed": "Could not determine if package is npm or Python. Check package name format.",
    }
    return help_messages.get(error_type, "Check deployment logs for details.")

async def _process_deployment_initialization(
    deployment_id: str,
    package: str,
    credentials_data: Dict[str, str],
    user_id: str,
):
    """Background task to handle package validation and server provisioning."""
    from app.db.session import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        try:
            # 1. Fetch deployment
            result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
            deployment = result.scalar_one_or_none()
            if not deployment:
                logger.error(f"Deployment {deployment_id} not found in background task")
                return

            # 2. Package Validation
            runtime = None
            validation_result = {"valid": False, "error": "Unknown error"}
            
            try:
                # Detect runtime by trying npm first (scoped packages always npm), then falling back to python
                if package.startswith("@") or "/" in package:
                    runtime = "npm"
                    validation_result = await package_validator.validate_npm_package(package)
                else:
                    # Try npm first, then fall back to python
                    validation_result = await package_validator.validate_npm_package(package)
                    if validation_result["valid"]:
                        runtime = "npm"
                    else:
                        validation_result = await package_validator.validate_python_package(package)
                        if validation_result["valid"]:
                            runtime = "python"
                        else:
                            deployment.status = "failed"
                            deployment.error_message = f"Package '{package}' not found in npm or PyPI registries."
                            await db.commit()
                            return

                if not validation_result["valid"]:
                    deployment.status = "failed"
                    deployment.error_message = validation_result.get("error", "Package validation failed")
                    await db.commit()
                    return

                # Store runtime and version
                mcp_config = deployment.schedule_config.setdefault("mcp_config", {})
                mcp_config["runtime"] = runtime
                mcp_config["version"] = validation_result.get("version")
                flag_modified(deployment, "schedule_config")
                
            except Exception as e:
                deployment.status = "failed"
                deployment.error_message = f"Validation error: {str(e)}"
                await db.commit()
                return

            # 3. Start the MCP server
            try:
                # Prepare environment variables from credentials
                env_vars = {}
                for service_name, decrypted_value in credentials_data.items():
                    # Strip 'env_' prefix from service_name to get actual env var name
                    env_var_name = service_name.removeprefix("env_")
                    env_vars[env_var_name] = decrypted_value

                logger.info(f"Starting MCP server for deployment {deployment.id}: {package} ({runtime})")

                # Try Fly.io deployment (uses user's token with fallback to system)
                try:
                    from app.services.fly_deployment_service import FlyDeploymentService
                    import uuid
                    
                    fly_service = FlyDeploymentService()

                    machine_id = await fly_service.create_machine(
                        deployment_id=str(deployment.id),
                        mcp_config=mcp_config,
                        credentials=env_vars,
                        user_id=uuid.UUID(user_id),
                        db=db
                    )

                    if machine_id:
                        deployment.machine_id = machine_id
                        deployment.status = "running"
                        await db.commit()
                        logger.info(f"Fly machine {machine_id} started successfully")
                    else:
                        deployment.status = "failed"
                        deployment.error_message = "Failed to create Fly.io machine"
                        await db.commit()

                except ValueError as e:
                    # User doesn't have Fly.io token - provide helpful error
                    deployment.status = "failed"
                    deployment.error_message = str(e)
                    await db.commit()
                    logger.error(f"Fly.io deployment failed: {str(e)}")
                
                except Exception as e:
                    # Fly.io deployment failed, try local subprocess fallback
                    logger.warning(f"Fly.io deployment failed, falling back to local subprocess: {str(e)}")
                    
                    # FALLBACK TO LOCAL SUBPROCESS
                    try:
                        success = await start_server(
                            deployment_id=str(deployment.id),
                            package=package,
                            env_vars=env_vars,
                            runtime=runtime
                        )

                        if success:
                            deployment.status = "running"
                        else:
                            deployment.status = "failed"
                            deployment.error_message = "Failed to start local subprocess"
                        
                        await db.commit()
                    except Exception as fallback_error:
                        deployment.status = "failed"
                        deployment.error_message = f"Both Fly.io and local deployment failed: {str(fallback_error)}"
                        await db.commit()

            except Exception as e:
                logger.exception(f"Startup failed for deployment {deployment.id}")
                deployment.status = "failed"
                deployment.error_message = str(e)
                await db.commit()

        except Exception as e:
            logger.exception(f"Unexpected error in background task for deployment {deployment_id}")

@router.post("", response_model=DeploymentResponse)
async def create_deployment(
    deployment_in: DeploymentCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Create Deployment Record (associated with user)
    deployment = Deployment(
        name=deployment_in.name,
        schedule_config=deployment_in.schedule_config,
        status="pending",
        user_id=current_user.id  # Associate deployment with user
    )
    db.add(deployment)
    await db.flush()

    # 2. Extract package and validate basic presence
    mcp_config = deployment.schedule_config.get("mcp_config", {}) if deployment.schedule_config else {}
    package = mcp_config.get("package")

    if not package:
        deployment.status = "failed"
        deployment.error_message = "No 'package' specified in MCP config"
        await db.commit()
        raise HTTPException(status_code=400, detail={"error": "package_missing", "message": deployment.error_message})

    # 3. Save Credentials
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

    # 4. Enqueue background initialization (with user_id)
    background_tasks.add_task(
        _process_deployment_initialization,
        deployment_id=str(deployment.id),
        package=package,
        user_id=str(current_user.id)  # Pass user ID for fetching API keys
    )

    # 5. Construct Immediate Response
    base_url = settings.PUBLIC_URL if settings.PUBLIC_URL else str(request.base_url).rstrip("/")
    connection_url = f"{base_url}{settings.API_V1_STR}/mcp/{deployment.id}"
    
    return DeploymentResponse(
        id=deployment.id,
        name=deployment.name,
        status=deployment.status,
        schedule_config=deployment.schedule_config,
        created_at=deployment.created_at,
        updated_at=deployment.updated_at,
        connection_url=connection_url,
        error_message=deployment.error_message
    )

@router.get("", response_model=List[DeploymentResponse])
async def list_deployments(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Deployment).where(Deployment.user_id == current_user.id)
    )
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

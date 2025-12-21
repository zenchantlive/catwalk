"""
Authentication-aware deployment endpoints.

This is a reference implementation showing how to update existing
deployment endpoints to scope by user.

Key changes from original deployments.py:
1. All endpoints require authentication (Depends(get_current_user))
2. Queries filter by user_id
3. Create operations set user_id from authenticated user

Example migration path:
1. Create new authenticated endpoints here
2. Test with frontend
3. Gradually migrate deployments.py endpoints
4. Eventually merge or replace deployments.py
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.deployment import Deployment

router = APIRouter(prefix="/auth/deployments", tags=["deployments (authenticated)"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class DeploymentCreate(BaseModel):
    """Schema for creating a deployment (user-scoped)."""
    name: str
    schedule_config: dict  # Contains mcp_config


class DeploymentResponse(BaseModel):
    """Deployment response (includes user_id for authorization checks)."""
    id: str  # UUID as string
    user_id: str  # UUID as string
    name: str
    status: str
    schedule_config: dict
    machine_id: Optional[str]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


# ============================================================================
# Endpoints (All require authentication)
# ============================================================================

@router.get("/", response_model=List[DeploymentResponse])
async def list_user_deployments(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[DeploymentResponse]:
    """
    List all deployments for the authenticated user.

    Requires: Authorization header with valid JWT token.

    Returns:
        List of deployments owned by current user
    """
    result = await db.execute(
        select(Deployment)
        .where(Deployment.user_id == user.id)
        .order_by(Deployment.created_at.desc())
    )
    deployments = result.scalars().all()

    return [DeploymentResponse.model_validate(d) for d in deployments]


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_user_deployment(
    deployment_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DeploymentResponse:
    """
    Get a specific deployment (only if owned by current user).

    Requires: Authorization header with valid JWT token.

    Args:
        deployment_id: UUID of deployment to retrieve

    Returns:
        Deployment details

    Raises:
        404: If deployment not found or not owned by user
    """
    result = await db.execute(
        select(Deployment)
        .where(Deployment.id == deployment_id)
        .where(Deployment.user_id == user.id)  # Authorization check
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found or access denied"
        )

    return DeploymentResponse.model_validate(deployment)


@router.post("/", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def create_user_deployment(
    deployment_data: DeploymentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DeploymentResponse:
    """
    Create a new deployment for the authenticated user.

    Requires: Authorization header with valid JWT token.

    Args:
        deployment_data: Deployment configuration
        user: Current authenticated user (auto-injected)

    Returns:
        Created deployment

    Note: This is a simplified example. Real implementation should:
    1. Validate schedule_config.mcp_config
    2. Create Fly machine
    3. Store credentials
    4. Handle errors
    """
    deployment = Deployment(
        user_id=user.id,  # Set owner
        name=deployment_data.name,
        schedule_config=deployment_data.schedule_config,
        status="pending"
    )

    db.add(deployment)
    await db.commit()
    await db.refresh(deployment)

    return DeploymentResponse.model_validate(deployment)


@router.delete("/{deployment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_deployment(
    deployment_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a deployment (only if owned by current user).

    Requires: Authorization header with valid JWT token.

    Args:
        deployment_id: UUID of deployment to delete

    Raises:
        404: If deployment not found or not owned by user

    Note: Real implementation should also:
    1. Stop/destroy Fly machine
    2. Cleanup credentials (cascade delete handles this)
    """
    result = await db.execute(
        select(Deployment)
        .where(Deployment.id == deployment_id)
        .where(Deployment.user_id == user.id)  # Authorization check
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found or access denied"
        )

    await db.delete(deployment)
    await db.commit()
    return None


# ============================================================================
# Migration Notes
# ============================================================================

"""
To migrate existing deployments.py endpoints:

1. Add user parameter to each endpoint:
   async def create_deployment(
       data: DeploymentCreate,
       user: User = Depends(get_current_user),  # Add this
       db: AsyncSession = Depends(get_db)
   )

2. Set user_id on create:
   deployment = Deployment(
       user_id=user.id,  # Add this
       name=data.name,
       ...
   )

3. Filter queries by user_id:
   select(Deployment)
   .where(Deployment.user_id == user.id)  # Add this

4. Handle existing deployments without user_id:
   - Option A: Backfill user_id via migration (assign to admin user)
   - Option B: Allow null user_id (legacy deployments)
   - Option C: Delete old deployments (if testing only)

5. Update frontend API calls to include Authorization header:
   headers: {
     "Authorization": `Bearer ${session.token}`
   }
"""

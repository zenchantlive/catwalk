"""Authentication API endpoints."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class SyncUserRequest(BaseModel):
    """Request model for syncing user from Auth.js."""
    email: EmailStr
    name: str | None = None
    avatar_url: str | None = None
    github_id: str | None = None


class UserResponse(BaseModel):
    """Response model for user data."""
    id: str
    email: str
    name: str | None
    avatar_url: str | None
    github_id: str | None
    created_at: datetime
    updated_at: datetime


@router.post("/sync-user", response_model=UserResponse)
async def sync_user(
    user_data: SyncUserRequest,
    x_auth_secret: str | None = Header(default=None, alias="X-Auth-Secret"),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync user from Auth.js to backend database.

    Called by Auth.js signIn callback after successful GitHub OAuth.
    Requires AUTH_SYNC_SECRET to be set and provided in header.

    Args:
        user_data: User information from Auth.js
        x_auth_secret: Shared secret for server-to-server auth
        db: Database session
    """
    from app.core.config import settings

    # Validate Shared Secret
    if not settings.AUTH_SYNC_SECRET:
        # If secret not configured in backend, fail closed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Backend configuration error: Authentication sync secret not set"
        )
    
    if x_auth_secret != settings.AUTH_SYNC_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication secret"
        )

    # Check if user exists by email
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    user = result.scalar_one_or_none()

        if user:
        # Update existing user
        user.name = user_data.name
        user.avatar_url = user_data.avatar_url
        user.github_id = user_data.github_id
        user.updated_at = datetime.utcnow()
        print(f"[AUDIT] User updated via sync: {user.email} (ID: {user.id})")
    else:
        # Create new user
        user = User(
            email=user_data.email,
            name=user_data.name,
            avatar_url=user_data.avatar_url,
            github_id=user_data.github_id,
        )
        db.add(user)
        # Flush to get ID for logging
        await db.flush()
        print(f"[AUDIT] User created via sync: {user.email} (ID: {user.id})")

    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        github_id=user.github_id,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current authenticated user's information.

    Requires valid JWT token in Authorization header.

    Returns:
        UserResponse: Current user's data
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        github_id=current_user.github_id,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )

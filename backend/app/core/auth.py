"""JWT authentication middleware and utilities for FastAPI.

This module integrates with Auth.js (NextAuth v5) on the frontend:
1. Frontend uses GitHub OAuth to generate JWT tokens
2. Frontend sends JWT in Authorization header: "Bearer <token>"
3. Backend verifies JWT signature using shared secret (AUTH_SECRET)
4. Backend extracts user info from JWT payload and attaches to request

JWT Payload Structure (from Auth.js):
{
    "sub": "user-uuid",           # User ID
    "email": "[email protected]",
    "name": "John Doe",
    "picture": "https://...",     # Avatar URL
    "iat": 1234567890,            # Issued at
    "exp": 1234567890             # Expiration
}
"""
import jwt
from datetime import datetime, timedelta
import logging
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

# Security scheme for Swagger UI
security = HTTPBearer(
    scheme_name="JWT Bearer Token",
    description="Enter your JWT token from Auth.js (GitHub OAuth)"
)


class JWTPayload:
    """
    Structured JWT payload from Auth.js.

    Attributes:
        sub: User ID (UUID as string)
        email: User's email address
        name: User's display name
        picture: Avatar URL from GitHub
        iat: Issued at timestamp
        exp: Expiration timestamp
    """
    def __init__(self, payload: dict):
        self.sub: str = payload.get("sub", "")
        self.email: str = payload.get("email", "")
        self.name: Optional[str] = payload.get("name")
        self.picture: Optional[str] = payload.get("picture")
        self.iat: int = payload.get("iat", 0)
        self.exp: int = payload.get("exp", 0)

    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow().timestamp() > self.exp


def verify_jwt_token(token: str) -> JWTPayload:
    """
    Verify JWT token signature and extract payload.

    Args:
        token: JWT token string from Authorization header

    Returns:
        JWTPayload: Parsed and validated JWT payload

    Raises:
        HTTPException: 401 if token is invalid or expired

    Security Notes:
        - Uses HS256 algorithm (symmetric key)
        - Shared secret with frontend via AUTH_SECRET
        - Verifies expiration automatically
    """
    try:
        if not settings.AUTH_SECRET:
            logger.error("AUTH_SECRET is not configured; refusing to verify JWTs")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server authentication is not configured",
            )

        required_claims = ["sub", "email", "exp"]
        if settings.AUTH_JWT_ISSUER:
            required_claims.append("iss")
        if settings.AUTH_JWT_AUDIENCE:
            required_claims.append("aud")

        # Decode and verify JWT signature
        payload = jwt.decode(
            token,
            settings.AUTH_SECRET,
            algorithms=["HS256"],
            issuer=settings.AUTH_JWT_ISSUER,
            audience=settings.AUTH_JWT_AUDIENCE,
            options={
                "verify_signature": True,
                "verify_exp": True,  # Auto-check expiration
                "require": required_claims,  # Required claims
            }
        )

        return JWTPayload(payload)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError as e:
        logger.info("JWT validation failed", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get current authenticated user.

    Usage:
        @app.get("/api/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id, "email": user.email}

    Flow:
        1. Extract Bearer token from Authorization header
        2. Verify JWT signature and expiration
        3. Query database for user by email
        4. Return User object

    Args:
        credentials: HTTP Authorization credentials (auto-injected by FastAPI)
        db: Database session (auto-injected by FastAPI)

    Returns:
        User: Authenticated user from database

    Raises:
        HTTPException: 401 if token invalid or user not found
    """
    # Verify JWT and extract payload
    payload = verify_jwt_token(credentials.credentials)

    user: User | None = None

    # Prefer stable identifier binding when possible.
    try:
        sub_uuid = UUID(payload.sub)
    except ValueError:
        sub_uuid = None

    if sub_uuid:
        result = await db.execute(select(User).where(User.id == sub_uuid))
        user = result.scalar_one_or_none()

    # Backwards-compatible fallback for older tokens / legacy flows.
    if not user and payload.email:
        result = await db.execute(select(User).where(User.email == payload.email))
        user = result.scalar_one_or_none()

    # If both are present, ensure token claims match the stored user.
    if user and payload.email and user.email != payload.email:
        logger.warning(
            "JWT claim mismatch: subject resolved to user_id=%s but email claim differs",
            user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user:
        logger.info("Authenticated user not found for provided token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication - returns User if authenticated, None otherwise.

    Use this for endpoints that work differently for authenticated users
    but don't require authentication.

    Usage:
        @app.get("/api/public")
        async def public_route(user: Optional[User] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello {user.name}"}
            else:
                return {"message": "Hello guest"}

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        User if authenticated, None if not authenticated
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.replace("Bearer ", "")

    try:
        payload = verify_jwt_token(token)
        try:
            sub_uuid = UUID(payload.sub)
        except ValueError:
            sub_uuid = None

        if sub_uuid:
            result = await db.execute(select(User).where(User.id == sub_uuid))
            user = result.scalar_one_or_none()
            if user and payload.email and user.email != payload.email:
                return None
            if user:
                return user

        if payload.email:
            result = await db.execute(select(User).where(User.email == payload.email))
            return result.scalar_one_or_none()

        return None
    except HTTPException:
        return None


def create_test_token(user_email: str, expires_in_minutes: int = 30) -> str:
    """
    Create a test JWT token for development/testing.

    WARNING: Only use in development! Production tokens come from Auth.js.

    Args:
        user_email: Email to include in token
        expires_in_minutes: Token validity duration

    Returns:
        str: Signed JWT token

    Example:
        token = create_test_token("[email protected]")
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/protected", headers=headers)
    """
    if settings.ENVIRONMENT.lower() in {"production", "prod"}:
        raise RuntimeError("create_test_token is not allowed in production")

    if not settings.AUTH_SECRET:
        raise RuntimeError("AUTH_SECRET is not configured")

    now = datetime.utcnow()
    payload = {
        "sub": "test-user-id",
        "email": user_email,
        "name": "Test User",
        "picture": "https://github.com/test.png",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_in_minutes)).timestamp())
    }

    return jwt.encode(payload, settings.AUTH_SECRET, algorithm="HS256")

import os

from cryptography.fernet import Fernet

# Set environment variables for tests before importing the app
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["AUTH_SYNC_SECRET"] = "test-sync-secret"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import asyncio
import uuid
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.user import User

# Use in-memory SQLite for fast integration tests
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

@pytest_asyncio.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database_session():
    """Session-level setup."""
    # We could do nothing here and let db_session handle it
    yield

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for each test by recreating tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        yield session
    
    # Drop all tables after each test to ensure isolation
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an AsyncClient for the FastAPI app with DB override."""
    
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    # Use ASGITransport for testing FastAPI apps
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    # Clean up overrides
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def mock_user(db_session: AsyncSession) -> User:
    """Create a mock user in the test database."""
    user = User(
        email="test@example.com",
        name="Test User",
        github_id="12345678"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
def auth_headers(mock_user: User):
    """Provide authentication headers for a mock user."""
    # In a real app, this would be a JWT. For tests, we'll override get_current_user.
    
    async def override_get_current_user():
        return mock_user
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    # We return a dummy header just to simulate its presence if needed
    return {"Authorization": "Bearer mock-token"}

@pytest.fixture
def api_secret_header():
    """Header for X-Auth-Secret (sync endpoints)."""
    return {"X-Auth-Secret": "test-sync-secret"}

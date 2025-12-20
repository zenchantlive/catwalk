from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
import logging

# Initialize logger for this module
logger = logging.getLogger(__name__)

# Dictionary to hold database connection arguments
connect_args = {}

# Check if we are using SQLite via the DATABASE_URL
if "sqlite" in settings.DATABASE_URL:
    # SQLite-specific optimization: disable check_same_thread because
    # FastAPI handles requests in multiple threads/tasks, but aiosqlite manages connections safely
    connect_args = {"check_same_thread": False}

# Create the async SQLAlchemy engine
# 1. settings.DATABASE_URL: The connection string (Postgres or SQLite)
# 2. echo=False: Disable SQL query logging to console (enable for debugging)
# 3. connect_args: Pass the specific optimized arguments defined above
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)

# Create a customized AsyncSession class (Session Factory)
# This will be used to generate new sessions for each request
AsyncSessionLocal = async_sessionmaker(
    bind=engine,              # Bind to our async engine
    class_=AsyncSession,      # Specify usage of AsyncSession
    expire_on_commit=False,   # Prevent objects from expiring after commit (kept in memory)
    autoflush=False,          # Disable autoflush for better manual control
)

async def get_db() -> AsyncSession:
    """
    Dependency generator for FastAPI to provide a database session.
    Yields an AsyncSession and ensures it's closed after the request is processed.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Yield the session to the path operation function
            yield session
        finally:
            # Ensure the session is closed, returning the connection to the pool
            await session.close()

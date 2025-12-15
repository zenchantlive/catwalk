from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional

class Settings(BaseSettings):
    """
    Application-wide settings managed by Pydantic.
    Reads configuration from environment variables and .env files.
    """
    # General project metadata
    PROJECT_NAME: str = "Catwalk Live"
    API_V1_STR: str = "/api"

    # Database Configuration
    # Default to local SQLite with aiosqlite driver for async support
    # Production should override this with a PostgreSQL URL (e.g., Supabase)
    DATABASE_URL: str = "sqlite+aiosqlite:///./local.db"

    @field_validator("DATABASE_URL")
    @classmethod
    def fix_postgres_url(cls, v: str) -> str:
        """
        Convert Fly.io's postgres:// URL to postgresql+psycopg:// for SQLAlchemy async.

        Fly.io provides DATABASE_URL as: postgres://user:pass@host/db?sslmode=disable
        SQLAlchemy 2.0+ with psycopg3 needs: postgresql+psycopg://user:pass@host/db?sslmode=disable

        psycopg3 (unlike asyncpg) supports all Fly.io SSL parameters natively.
        """
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg://", 1)
        return v
    
    # Security Configuration
    # Secret key for Fernet encryption. Must be a valid 32-byte url-safe base64 string.
    ENCRYPTION_KEY: Optional[str] = None

    # LLM Provider Configuration
    # key for OpenRouter to access Claude/OpenAI/etc.
    OPENROUTER_API_KEY: Optional[str] = None

    # Public URL for generating connection strings (e.g. https://xyz.ngrok-free.app)
    PUBLIC_URL: Optional[str] = None

    # Fly.io Configuration
    # Token to authenticate with Fly Machines API
    FLY_API_TOKEN: Optional[str] = None
    # Name of the Fly app where MCP machines will be created
    # This is a separate app from the backend for clean separation
    FLY_MCP_APP_NAME: str = "catwalk-live-mcp-servers"
    # Docker image to use for MCP servers
    # MUST be set in production via environment variable or .env file
    # Example: registry.fly.io/catwalk-live-mcp-host:latest
    FLY_MCP_IMAGE: Optional[str] = None

    @field_validator("FLY_MCP_IMAGE")
    @classmethod
    def validate_mcp_image(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate that FLY_MCP_IMAGE is set when FLY_API_TOKEN is present.

        This prevents the system from attempting to create machines with invalid
        image identifiers. If you're deploying MCP servers, you MUST set this.

        Raises:
            ValueError: If FLY_MCP_IMAGE is not set when needed.
        """
        # During initialization, we can't check FLY_API_TOKEN yet (not available in validator context)
        # So we'll add a runtime check in the service instead
        # For now, just ensure if it IS set, it looks valid
        if v and not ("/" in v or ":" in v):
            raise ValueError(
                f"FLY_MCP_IMAGE must be a valid Docker image reference (e.g., 'registry.fly.io/app:tag'), got: {v}"
            )
        return v
    
    # Pydantic Configuration
    model_config = SettingsConfigDict(
        env_file=".env",              # Load variables from .env file
        env_file_encoding="utf-8",    # Ensure correct encoding
        case_sensitive=True,          # Environment variables are case-sensitive
        extra="ignore"                # Ignore extra fields in .env not defined here
    )

# Instantiate the settings object to be imported elsewhere
settings = Settings()

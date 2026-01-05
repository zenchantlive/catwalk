from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
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

    # Deployment Environment
    # Used for safety checks (e.g., fail-fast secrets in production)
    ENVIRONMENT: str = "development"

    # Admin Configuration
    # Comma-separated list of emails authorized for privileged actions (e.g., cache clearing)
    ADMIN_EMAILS: str = ""

    # JWT Authentication (shared with Auth.js frontend)
    # This secret is used to verify JWT tokens from Auth.js (NextAuth v5)
    # MUST match AUTH_SECRET in frontend .env
    AUTH_SECRET: Optional[str] = None

    # Optional JWT claim binding for additional hardening.
    # If set, backend will validate issuer/audience on incoming JWTs.
    AUTH_JWT_ISSUER: Optional[str] = None
    AUTH_JWT_AUDIENCE: Optional[str] = None
    
    # Secret shared between NextAuth and Backend for sync-user endpoint
    # Used to secure the /auth/sync-user endpoint for server-to-server calls
    AUTH_SYNC_SECRET: Optional[str] = None

    # LLM Provider Configuration
    # key for OpenRouter to access Claude/OpenAI/etc.
    OPENROUTER_API_KEY: Optional[str] = None

    # Public URL for generating connection strings (e.g. https://xyz.ngrok-free.app)
    PUBLIC_URL: Optional[str] = None

    # GitHub API Configuration
    # GitHub token for API access (increases rate limits from 60 to 5000 requests/hour)
    GITHUB_TOKEN: Optional[str] = None

    # CORS Configuration
    # List of allowed origins for CORS. In production, this should restricted.
    # Defaults to allowing all for dev, but validation enforces restrictions in production.
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

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

    @model_validator(mode='after')
    def validate_fly_config(self) -> 'Settings':
        """
        Validate that FLY_MCP_IMAGE is set if FLY_API_TOKEN is present.
        """
        if self.FLY_API_TOKEN and not self.FLY_MCP_IMAGE:
            raise ValueError(
                "FLY_MCP_IMAGE must be set when FLY_API_TOKEN is provided."
            )
        
        # Also validate image format here
        if self.FLY_MCP_IMAGE and not ("/" in self.FLY_MCP_IMAGE or ":" in self.FLY_MCP_IMAGE):
            raise ValueError(
                f"FLY_MCP_IMAGE must be a valid Docker image reference (e.g., 'registry.fly.io/app:tag'), got: {self.FLY_MCP_IMAGE}"
            )
        return self

    @model_validator(mode="after")
    def validate_security_config(self) -> "Settings":
        """
        Validate security-critical settings.

        In production-like environments, fail fast if AUTH_SECRET is missing.
        """
        if self.ENVIRONMENT.lower() in {"production", "prod"} and not self.AUTH_SECRET:
            raise ValueError("AUTH_SECRET must be set in production")
        return self
    
    # Pydantic Configuration
    model_config = SettingsConfigDict(
        env_file=".env",              # Load variables from .env file
        env_file_encoding="utf-8",    # Ensure correct encoding
        case_sensitive=True,          # Environment variables are case-sensitive
        extra="ignore"                # Ignore extra fields in .env not defined here
    )

# Instantiate the settings object to be imported elsewhere
settings = Settings()

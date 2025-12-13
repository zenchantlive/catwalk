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
    
    # Pydantic Configuration
    model_config = SettingsConfigDict(
        env_file=".env",              # Load variables from .env file
        env_file_encoding="utf-8",    # Ensure correct encoding
        case_sensitive=True,          # Environment variables are case-sensitive
        extra="ignore"                # Ignore extra fields in .env not defined here
    )

# Instantiate the settings object to be imported elsewhere
settings = Settings()

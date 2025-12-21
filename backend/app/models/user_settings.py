"""User settings model for encrypted API keys."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserSettings(Base):
    """
    User settings for storing encrypted API keys.

    All API keys are encrypted using Fernet (app.services.encryption).
    This table has a 1:1 relationship with User.

    Attributes:
        id: Primary key (UUID)
        user_id: Foreign key to User (unique, enforces 1:1)
        encrypted_fly_api_token: Fernet-encrypted FLY_API_TOKEN
        encrypted_openrouter_api_key: Fernet-encrypted OPENROUTER_API_KEY
        created_at: Settings creation timestamp
        updated_at: Last update timestamp

    Security Notes:
        - All fields prefixed with "encrypted_" store Fernet ciphertext
        - Decryption requires ENCRYPTION_KEY from environment (Fly secrets)
        - API keys are NEVER logged or returned in API responses
        - Use app.services.encryption.EncryptionService for encrypt/decrypt
    """
    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Foreign key to User (unique = 1:1 relationship)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    # Encrypted API keys (Fernet ciphertext stored as Text)
    # Use app.services.encryption.EncryptionService to encrypt/decrypt
    encrypted_fly_api_token: Mapped[str | None] = mapped_column(Text)
    encrypted_openrouter_api_key: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="settings"
    )

    def __repr__(self) -> str:
        has_fly = "yes" if self.encrypted_fly_api_token else "no"
        has_router = "yes" if self.encrypted_openrouter_api_key else "no"
        return (
            f"<UserSettings(id={self.id}, user_id={self.user_id}, "
            f"has_fly_key={has_fly}, has_openrouter_key={has_router})>"
        )

"""User model for authentication."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.deployment import Deployment
    from app.models.user_settings import UserSettings


class User(Base):
    """
    User model representing authenticated users.

    Users authenticate via GitHub OAuth (handled by Auth.js on frontend).
    The backend receives JWT tokens and stores minimal user info.

    Attributes:
        id: Primary key (UUID)
        email: User's email (unique, required)
        name: User's display name
        avatar_url: Profile picture URL from GitHub
        github_id: GitHub user ID (for OAuth provider tracking)
        created_at: Account creation timestamp
        updated_at: Last update timestamp

    Relationships:
        deployments: All deployments created by this user
        settings: User's API keys and preferences (1:1)
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Core user info (from GitHub OAuth)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    github_id: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)

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
    deployments: Mapped[list["Deployment"]] = relationship(
        "Deployment",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    settings: Mapped["UserSettings"] = relationship(
        "UserSettings",
        back_populates="user",
        uselist=False,  # 1:1 relationship
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"

import uuid
from datetime import datetime
from typing import Any, Dict
from sqlalchemy import String, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.db.base import Base

class Deployment(Base):
    """
    SQLAlchemy model representing a Deployment configuration.
    Stores the schedule, status, and metadata for a specific automation task.
    """
    __tablename__ = "deployments"

    # Primary Key: UUID, automatically generated if not provided
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    
    # Name of the deployment, indexed for fast lookups
    name: Mapped[str] = mapped_column(String, index=True)
    
    # JSON configuration for scheduling (e.g., cron expressions, intervals)
    schedule_config: Mapped[Dict[str, Any]] = mapped_column(JSON)
    
    # Current status of the deployment (e.g., 'active', 'inactive', 'paused')
    status: Mapped[str] = mapped_column(String, default="inactive")

    # Fly.io Machine ID (Phase 6)
    # Stores the ID of the running container for this deployment
    machine_id: Mapped[str] = mapped_column(String, nullable=True)

    # Error message if the deployment failed
    error_message: Mapped[str] = mapped_column(String, nullable=True)
    
    # Timestamp when the record was created, defaults to UTC now
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Timestamp when the record was last updated, updates automatically on change
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    # One-to-Many relationship with Credential (one deployment can have multiple credentials)
    # cascade="all, delete-orphan" ensures credentials are removed if the deployment is deleted
    credentials = relationship("Credential", back_populates="deployment", cascade="all, delete-orphan")

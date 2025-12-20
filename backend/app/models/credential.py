import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.db.base import Base

class Credential(Base):
    """
    SQLAlchemy model representing a secure Credential.
    Stores encrypted sensitive data (API keys, tokens) linked to a Deployment.
    """
    __tablename__ = "credentials"

    # Primary Key: UUID, automatically generated
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    
    # Name of the service this credential belongs to (e.g., 'openai', 'github')
    service_name: Mapped[str] = mapped_column(String)
    
    # The actual sensitive data, encrypted using Fernet before storage
    # This renders as a url-safe base64 string
    encrypted_data: Mapped[str] = mapped_column(String)
    
    # Foreign Key linking this credential to a specific Deployment ID
    deployment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deployments.id"))
    
    # Relationships
    # Many-to-One relationship back to the Deployment model
    deployment = relationship("Deployment", back_populates="credentials")

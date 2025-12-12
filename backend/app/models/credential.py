import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.db.base import Base

class Credential(Base):
    __tablename__ = "credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    service_name: Mapped[str] = mapped_column(String)
    encrypted_data: Mapped[str] = mapped_column(String) # Fernet blobs are url-safe base64 strings
    
    deployment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deployments.id"))
    
    # Relationships
    deployment = relationship("Deployment", back_populates="credentials")

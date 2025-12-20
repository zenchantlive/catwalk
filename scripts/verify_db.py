import asyncio
import sys
import os

# Add project root/backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.db.session import AsyncSessionLocal, engine
from app.models.deployment import Deployment
from app.models.credential import Credential
from app.services.encryption import EncryptionService
from sqlalchemy import select

async def verify():
    print("Starting verification...")
    
    # 1. Initialize Encryption
    # Generate a key for testing if not set (or rely on config if set)
    # For verification script, we assume settings are loaded from .env
    from app.core.config import settings
    # Ensure we have a key for the test run if none in env
    key = settings.ENCRYPTION_KEY
    if not key:
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        print(f"Generated temporary key for verification script.")

    encryption_service = EncryptionService(key=key)
    secret_value = "sk-test-1234567890"
    encrypted_secret = encryption_service.encrypt(secret_value)
    
    async with AsyncSessionLocal() as session:
        # 2. Create Deployment
        deployment = Deployment(
            name="Test Deployment",
            schedule_config={"cron": "0 0 * * *"},
            status="active"
        )
        session.add(deployment)
        await session.flush() # Get ID
        
        # 3. Create Credential
        credential = Credential(
            service_name="openai",
            encrypted_data=encrypted_secret,
            deployment_id=deployment.id
        )
        session.add(credential)
        await session.commit()
        
        deployment_id = deployment.id
        print(f"Created deployment {deployment_id}")

    # 4. Read back
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Credential).where(Credential.deployment_id == deployment_id)
        )
        fetched_credential = result.scalars().first()
        
        # 5. Verify
        assert fetched_credential is not None
        decrypted = encryption_service.decrypt(fetched_credential.encrypted_data)
        
        print(f"Original: {secret_value}")
        print(f"Decrypted: {decrypted}")
        
        if decrypted == secret_value:
            print("SUCCESS: Encryption round-trip and DB persistence verified.")
        else:
            print("FAILURE: Decrypted value does not match.")
            exit(1)

if __name__ == "__main__":
    asyncio.run(verify())

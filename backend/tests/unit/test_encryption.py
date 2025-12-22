import pytest
from cryptography.fernet import Fernet
from app.services.encryption import EncryptionService

@pytest.fixture
def valid_key():
    return Fernet.generate_key().decode()

def test_encryption_round_trip(valid_key):
    service = EncryptionService(key=valid_key)
    original_text = "secret-api-key-123"
    
    encrypted = service.encrypt(original_text)
    assert encrypted != original_text
    
    decrypted = service.decrypt(encrypted)
    assert decrypted == original_text

def test_service_initialization_failure():
    # Simulate missing key in settings by patching settings.ENCRYPTION_KEY
    from unittest.mock import patch
    with patch("app.services.encryption.settings") as mock_settings:
        mock_settings.ENCRYPTION_KEY = None
        with pytest.raises(ValueError, match="ENCRYPTION_KEY is not set"):
            EncryptionService(key=None)

def test_empty_input(valid_key):
    service = EncryptionService(key=valid_key)
    assert service.encrypt("") == ""
    assert service.decrypt("") == ""

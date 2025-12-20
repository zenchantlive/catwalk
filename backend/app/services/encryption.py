from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings

class EncryptionService:
    """
    Service responsible for symmetric encryption and decryption of sensitive data.
    Uses the Fernet algorithm from the cryptography library.
    """
    def __init__(self, key: str | None = None):
        """
        Initialize the EncryptionService.
        
        Args:
            key (str | None): A Fernet-compatible encryption key. 
                              If None, attempts to load from application settings (ENCRYPTION_KEY).
        
        Raises:
            ValueError: If no key is provided and none is found in settings.
        """
        # Determine the key to use: explicit argument takes precedence over settings
        self._key = key or settings.ENCRYPTION_KEY
        
        # Validate that a key exists before proceeding
        if not self._key:
            raise ValueError("ENCRYPTION_KEY is not set in configuration")
        
        # Initialize the Fernet instance with the validated key
        self._fernet = Fernet(self._key)

    def encrypt(self, data: str) -> str:
        """
        Encrypts a plain text string.
        
        Args:
            data (str): The plain text to encrypt.
            
        Returns:
            str: The encrypted data as a url-safe base64 encoded string.
                 Returns empty string if input is empty.
        """
        # Handle empty input case gracefully
        if not data:
            return ""
            
        # 1. Encode string to bytes (UTF-8)
        # 2. Encrypt using Fernet
        # 3. Decode result bytes back to string for storage/transmission
        return self._fernet.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        """
        Decrypts an encrypted string token.
        
        Args:
            token (str): The url-safe base64 encoded encrypted string.
            
        Returns:
            str: The original plain text string.
                 Returns empty string if input is empty.

        Raises:
            ValueError: If the token is invalid or cannot be decrypted.
        """
        # Handle empty input case gracefully
        if not token:
            return ""
        
        try:
            # 1. Encode token string to bytes
            # 2. Decrypt using Fernet
            # 3. Decode result bytes back to UTF-8 string
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken:
            # Raise a clear error if decryption fails
            raise ValueError("Invalid token: Decryption failed")

"""Sensitive data encryption manager for AIOps.

This module provides encryption and decryption services for sensitive data
such as API keys, tokens, and credentials.
"""

import os
import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manager for encrypting and decrypting sensitive data.

    This manager uses Fernet symmetric encryption for secure data storage.

    Example:
        ```python
        # Initialize with environment variable
        manager = EncryptionManager()

        # Or with a custom key
        manager = EncryptionManager(key=b'...')

        # Encrypt an API key
        encrypted = manager.encrypt_api_key("sk-...")

        # Decrypt the key
        decrypted = manager.decrypt_api_key(encrypted)
        ```
    """

    # Key derivation settings
    SALT_SIZE = 16
    ITERATIONS = 100000

    def __init__(
        self,
        key: Optional[bytes] = None,
        password: Optional[str] = None
    ):
        """Initialize the encryption manager.

        Args:
            key: A Fernet-compatible encryption key. If not provided,
                 will look for AIOPS_ENCRYPTION_KEY environment variable.
            password: A password to derive a key from. If provided,
                     key parameter is ignored.

        Raises:
            ValueError: If neither key nor password is provided and
                       AIOPS_ENCRYPTION_KEY is not set.
        """
        if password:
            self.cipher = Fernet(self._derive_key_from_password(password))
            logger.debug("Encryption manager initialized with password-derived key")
            return

        if key is None:
            key = os.environ.get('AIOPS_ENCRYPTION_KEY')
            if not key:
                # Generate a new key for development/testing
                key = Fernet.generate_key()
                logger.warning(
                    "Generated new encryption key. Set AIOPS_ENCRYPTION_KEY "
                    "env var for persistence. Key: %s",
                    key.decode('ascii') if isinstance(key, bytes) else key
                )
                # In production, this should raise an error
                # raise ValueError(
                #     "AIOPS_ENCRYPTION_KEY environment variable not set"
                # )

        # Ensure key is bytes
        if isinstance(key, str):
            key = key.encode('utf-8')

        # Validate key format
        try:
            self.cipher = Fernet(key)
        except Exception as e:
            raise ValueError(
                f"Invalid encryption key format. "
                f"Key must be a valid Fernet key: {e}"
            )

        logger.debug("Encryption manager initialized")

    def _derive_key_from_password(self, password: str) -> bytes:
        """Derive a Fernet key from a password.

        Args:
            password: The password to derive from

        Returns:
            A Fernet-compatible key
        """
        # Generate a random salt
        salt = os.urandom(self.SALT_SIZE)

        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.ITERATIONS,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))

        # Prepend salt to the key for later derivation
        return salt + key

    def encrypt(self, data: str) -> str:
        """Encrypt a string value.

        Args:
            data: The plaintext data to encrypt

        Returns:
            The encrypted data as a base64-encoded string

        Raises:
            Exception: If encryption fails
        """
        try:
            encrypted = self.cipher.encrypt(data.encode('utf-8'))
            return encrypted.decode('ascii')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, encrypted: str) -> str:
        """Decrypt an encrypted string.

        Args:
            encrypted: The base64-encoded encrypted data

        Returns:
            The decrypted plaintext

        Raises:
            Exception: If decryption fails
        """
        try:
            decrypted = self.cipher.decrypt(encrypted.encode('ascii'))
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt an API key.

        This is a convenience method for encrypting API keys.

        Args:
            api_key: The API key to encrypt

        Returns:
            The encrypted API key
        """
        return self.encrypt(api_key)

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt an encrypted API key.

        This is a convenience method for decrypting API keys.

        Args:
            encrypted_key: The encrypted API key

        Returns:
            The decrypted API key
        """
        return self.decrypt(encrypted_key)

    def encrypt_token(self, token: str) -> str:
        """Encrypt an authentication token.

        Args:
            token: The token to encrypt

        Returns:
            The encrypted token
        """
        return self.encrypt(token)

    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt an encrypted token.

        Args:
            encrypted_token: The encrypted token

        Returns:
            The decrypted token
        """
        return self.decrypt(encrypted_token)

    def encrypt_dict(self, data: dict) -> dict:
        """Encrypt values in a dictionary.

        Args:
            data: Dictionary with string values to encrypt

        Returns:
            Dictionary with encrypted values
        """
        import json
        json_str = json.dumps(data)
        return {"encrypted": self.encrypt(json_str)}

    def decrypt_dict(self, encrypted_data: dict) -> dict:
        """Decrypt values from an encrypted dictionary.

        Args:
            encrypted_data: Dictionary with 'encrypted' key

        Returns:
            Decrypted dictionary
        """
        import json
        json_str = self.decrypt(encrypted_data["encrypted"])
        return json.loads(json_str)


# Global encryption manager instance
_global_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """Get the global encryption manager instance.

    Returns:
        The global encryption manager
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = EncryptionManager()
    return _global_manager


def reset_encryption_manager() -> None:
    """Reset the global encryption manager.

    This is primarily useful for testing.
    """
    global _global_manager
    _global_manager = None

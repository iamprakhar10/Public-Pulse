"""
Encryption helpers for very sensitive OAuth tokens

Google refresh tokens are long-lived, they must be recoverable
because the backend will need to send them to Google's token
endpoint later. We will hash them
"""

from cryptography.fernet import Fernet, InvalidToken

class TokenEncryptionError(ValueError):
    """
    This will be raised when a token can't be encrypted 
    or decrypted safely
    """


def _build_cipher(encryption_key: str) -> Fernet:
    """
    Building a fernet cipher from the application's encryption key in .env
    """
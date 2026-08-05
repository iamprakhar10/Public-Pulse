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
    
    They key is supplied as an argument instead of being read from .env
    This keeps the utility independent and east to test
    """

    if not encryption_key or not encryption_key.strip():
        raise TokenEncryptionError(
            'Token encryption key is missing'
        )

    try:
        return Fernet(
            encryption_key.encode('utf-8')
        )

    except (TypeError, ValueError) as exc:
        raise TokenEncryptionError(
            "Token encryption key is invalid"
        )


def encrypt_token(
        token: str,
        encryption_key: str,
) -> str:
    """
    Encrypting a plain OAuth token

    This will return a text value which is safe to store in postgres
    """

    if not token:
        raise TokenEncryptionError(
            "Token cannot be empty"
        )

    cipher = _build_cipher(
        encryption_key=encryption_key,
    )

    encrypted_token = cipher.encrypt(
        token.encode('utf-8'),
    )

    return encrypted_token.decode('utf-8')



def decrypt_token(
        encrypted_token: str,
        encryption_key: str,
) -> str:
    """
    Decrypting a stored token back to it's original value
    """

    if not encrypted_token:
        raise TokenEncryptionError(
            "Encrypted token can't be empty"
        )

    cipher = _build_cipher(
        encryption_key=encryption_key,
    )

    try:
        decrypted_token = cipher.decrypt(
            encrypted_token.encode('utf-8'),
        )

    except InvalidToken as exc:
        raise TokenEncryptionError(
            "Token could not be decrypted"
        ) from exc

    return decrypted_token.decode("utf-8")

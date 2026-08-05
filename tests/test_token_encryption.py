import pytest
from cryptography.fernet import Fernet

from app.utils.token_encryption import (
    TokenEncryptionError,
    decrypt_token,
    encrypt_token,
)


def create_test_key() -> str:
    """
    Create a separate encryption key for each test.
    """

    return Fernet.generate_key().decode("utf-8")


def test_token_can_be_encrypted_and_decrypted() -> None:
    """
    Encryption followed by decryption must return the original token.
    """

    encryption_key = create_test_key()
    original_token = "google-refresh-token-example"

    encrypted_token = encrypt_token(
        token=original_token,
        encryption_key=encryption_key,
    )

    decrypted_token = decrypt_token(
        encrypted_token=encrypted_token,
        encryption_key=encryption_key,
    )

    assert encrypted_token != original_token
    assert decrypted_token == original_token


def test_same_token_produces_different_ciphertext() -> None:
    """
    Encrypting the same token twice should not expose a predictable
    stored value.
    """

    encryption_key = create_test_key()
    original_token = "google-refresh-token-example"

    first_encrypted_token = encrypt_token(
        token=original_token,
        encryption_key=encryption_key,
    )

    second_encrypted_token = encrypt_token(
        token=original_token,
        encryption_key=encryption_key,
    )

    assert first_encrypted_token != second_encrypted_token

    assert decrypt_token(
        encrypted_token=first_encrypted_token,
        encryption_key=encryption_key,
    ) == original_token

    assert decrypt_token(
        encrypted_token=second_encrypted_token,
        encryption_key=encryption_key,
    ) == original_token


def test_token_cannot_be_decrypted_with_wrong_key() -> None:
    """
    A different application key must not decrypt the stored token.
    """

    correct_key = create_test_key()
    wrong_key = create_test_key()

    encrypted_token = encrypt_token(
        token="google-refresh-token-example",
        encryption_key=correct_key,
    )

    with pytest.raises(
        TokenEncryptionError,
        match="Token could not be decrypted",
    ):
        decrypt_token(
            encrypted_token=encrypted_token,
            encryption_key=wrong_key,
        )


def test_empty_token_is_rejected() -> None:
    """
    Empty token values must never be stored.
    """

    encryption_key = create_test_key()

    with pytest.raises(
        TokenEncryptionError,
        match="Token cannot be empty",
    ):
        encrypt_token(
            token="",
            encryption_key=encryption_key,
        )


def test_invalid_encryption_key_is_rejected() -> None:
    """
    Configuration errors should produce a clear application error.
    """

    with pytest.raises(
        TokenEncryptionError,
        match="Token encryption key is invalid",
    ):
        encrypt_token(
            token="google-refresh-token-example",
            encryption_key="not-a-valid-fernet-key",
        )
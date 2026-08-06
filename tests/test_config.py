import pytest

from app.config import (
    ConfigurationError,
    get_google_oauth_config,
    get_token_encryption_key,
)


def test_get_google_oauth_config_returns_settings(
        monkeypatch,
) -> None:
    """
    Valid Google OAuth environment variables should produce a typed
    configuration object.
    """

    monkeypatch.setenv(
        "GOOGLE_CLIENT_ID",
        "test-client-id",
    )
    monkeypatch.setenv(
        "GOOGLE_CLIENT_SECRET",
        "test-client-secret",
    )
    monkeypatch.setenv(
        "GOOGLE_REDIRECT_URI",
        "http://127.0.0.1:8000/gmail/callback",
    )

    config = get_google_oauth_config()

    assert config.client_id == "test-client-id"
    assert config.client_secret == "test-client-secret"
    assert (
        config.redirect_uri
        == "http://127.0.0.1:8000/gmail/callback"
    )


def test_get_google_oauth_config_rejects_missing_values(
        monkeypatch,
) -> None:
    """
    Missing OAuth configuration should produce a clear error.
    """

    monkeypatch.delenv(
        "GOOGLE_CLIENT_ID",
        raising=False,
    )
    monkeypatch.delenv(
        "GOOGLE_CLIENT_SECRET",
        raising=False,
    )
    monkeypatch.delenv(
        "GOOGLE_REDIRECT_URI",
        raising=False,
    )

    with pytest.raises(
        ConfigurationError,
        match="GOOGLE_CLIENT_ID",
    ):
        get_google_oauth_config()


def test_get_token_encryption_key(
        monkeypatch,
) -> None:
    """
    The configured encryption key should be returned unchanged.
    """

    monkeypatch.setenv(
        "TOKEN_ENCRYPTION_KEY",
        "test-encryption-key",
    )

    encryption_key = get_token_encryption_key()

    assert encryption_key == "test-encryption-key"


def test_missing_token_encryption_key_is_rejected(
        monkeypatch,
) -> None:
    """
    A missing encryption key must fail before token storage is attempted.
    """

    monkeypatch.delenv(
        "TOKEN_ENCRYPTION_KEY",
        raising=False,
    )

    with pytest.raises(
        ConfigurationError,
        match="TOKEN_ENCRYPTION_KEY",
    ):
        get_token_encryption_key()
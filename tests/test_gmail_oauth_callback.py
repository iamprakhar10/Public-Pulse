"""
Tests for completing the Gmail OAuth callback.

Google network calls are replaced with controlled test results.
"""

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import GoogleOAuthConfig
from app.database.gmail_credential_crud import (
    get_gmail_credential_by_user_id,
)
from app.database.models import User
from app.database.session import SessionLocal
from app.services import gmail_oauth
from app.services.gmail_oauth import (
    GoogleAuthorizationResult,
    MissingRefreshTokenError,
    complete_gmail_oauth_connection,
)
from app.services.gmail_oauth_state import create_oauth_state
from app.utils.security import hash_password
from app.utils.token_encryption import decrypt_token


TEST_EMAIL = "gmail-callback-test@example.com"


@pytest.fixture
def db_session():
    """
    Provide a database session and remove callback test records.
    """

    db = SessionLocal()

    try:
        db.execute(
            delete(User).where(
                User.email == TEST_EMAIL,
            )
        )
        db.commit()

        yield db

    finally:
        db.rollback()

        db.execute(
            delete(User).where(
                User.email == TEST_EMAIL,
            )
        )
        db.commit()
        db.close()


@pytest.fixture
def google_config() -> GoogleOAuthConfig:
    """
    Return non-secret Google settings for testing.
    """

    return GoogleOAuthConfig(
        client_id="test-client-id",
        client_secret="test-client-secret",
        redirect_uri=(
            "http://127.0.0.1:8000/gmail/callback"
        ),
    )


@pytest.fixture
def encryption_key() -> str:
    """
    Generate an isolated encryption key for each test.
    """

    return Fernet.generate_key().decode("utf-8")


def create_test_user(
        db: Session,
) -> User:
    """
    Create the Public Pulse user starting Gmail OAuth.
    """

    user = User(
        name="Gmail Callback Test",
        email=TEST_EMAIL,
        phone="9222222222",
        hashed_password=hash_password(
            "test-password",
        ),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def test_complete_gmail_oauth_connection(
        db_session,
        google_config,
        encryption_key,
        monkeypatch,
) -> None:
    """
    A valid state and Google result should create an encrypted
    Gmail credential.
    """

    user = create_test_user(db_session)

    state = create_oauth_state(
        db=db_session,
        user_id=user.id,
    )

    def fake_exchange(
            config,
            authorization_code,
    ) -> GoogleAuthorizationResult:
        assert config == google_config
        assert authorization_code == "test-code"

        return GoogleAuthorizationResult(
            google_account_id="google-user-123",
            google_email="connected@gmail.com",
            refresh_token="plain-google-refresh-token",
            scopes=(
                "openid "
                "https://www.googleapis.com/auth/gmail.send"
            ),
        )

    monkeypatch.setattr(
        gmail_oauth,
        "exchange_google_authorization_code",
        fake_exchange,
    )

    result = complete_gmail_oauth_connection(
        db=db_session,
        state=state,
        authorization_code="test-code",
        config=google_config,
        encryption_key=encryption_key,
    )

    stored_credential = get_gmail_credential_by_user_id(
        db=db_session,
        user_id=user.id,
    )

    assert result.user_id == user.id
    assert result.google_email == "connected@gmail.com"
    assert stored_credential is not None

    assert (
        stored_credential.encrypted_refresh_token
        != "plain-google-refresh-token"
    )

    decrypted_refresh_token = decrypt_token(
        encrypted_token=(
            stored_credential.encrypted_refresh_token
        ),
        encryption_key=encryption_key,
    )

    assert (
        decrypted_refresh_token
        == "plain-google-refresh-token"
    )


def test_first_connection_requires_refresh_token(
        db_session,
        google_config,
        encryption_key,
        monkeypatch,
) -> None:
    """
    A first connection cannot work without a Google refresh token.
    """

    user = create_test_user(db_session)

    state = create_oauth_state(
        db=db_session,
        user_id=user.id,
    )

    monkeypatch.setattr(
        gmail_oauth,
        "exchange_google_authorization_code",
        lambda config, authorization_code: (
            GoogleAuthorizationResult(
                google_account_id="google-user-456",
                google_email="missing-token@gmail.com",
                refresh_token=None,
                scopes="openid",
            )
        ),
    )

    with pytest.raises(
        MissingRefreshTokenError,
        match="did not return a refresh token",
    ):
        complete_gmail_oauth_connection(
            db=db_session,
            state=state,
            authorization_code="test-code",
            config=google_config,
            encryption_key=encryption_key,
        )
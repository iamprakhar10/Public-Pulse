"""
Tests for completing the Gmail OAuth callback.

Google network calls are mocked. These tests verify that:

- OAuth state identifies the correct Public Pulse user.
- The same PKCE code verifier created during /gmail/connect
  reaches the authorization-code exchange.
- Google refresh tokens are encrypted before storage.
- First-time connections require a refresh token.
"""

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import GoogleOAuthConfig
from app.database.db import SessionLocal
from app.database.gmail_credential_crud import (
    get_gmail_credential_by_user_id,
)
from app.database.models import (
    GmailCredential,
    GmailOAuthState,
    User,
)
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
TEST_PHONE = "9222222222"


@pytest.fixture
def db_session():
    """
    Provide a clean database session for Gmail OAuth callback tests.

    Dependent Gmail rows are removed before deleting the test user.
    """

    db = SessionLocal()

    try:
        # Delete dependent records first.
        db.execute(delete(GmailOAuthState))
        db.execute(delete(GmailCredential))

        db.execute(
            delete(User).where(
                User.email == TEST_EMAIL,
            )
        )

        db.commit()

        yield db

    finally:
        db.rollback()

        db.execute(delete(GmailOAuthState))
        db.execute(delete(GmailCredential))

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
    Return fake Google OAuth configuration.

    No real Google credentials are used by these tests.
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
    Generate an isolated Fernet key for each test.
    """

    return Fernet.generate_key().decode("utf-8")


def create_test_user(
        db: Session,
) -> User:
    """
    Create the Public Pulse user who starts Gmail OAuth.
    """

    user = User(
        name="Gmail Callback Test",
        email=TEST_EMAIL,
        phone=TEST_PHONE,
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
    A valid OAuth callback should:

    - consume the correct OAuth state,
    - pass the stored PKCE verifier into Google's token exchange,
    - encrypt the refresh token,
    - save the Gmail credential.
    """

    user = create_test_user(
        db=db_session,
    )

    # create_oauth_state now returns:
    #
    # (
    #     state,
    #     code_verifier,
    # )
    state, code_verifier = create_oauth_state(
        db=db_session,
        user_id=user.id,
    )

    def fake_exchange(
            config,
            authorization_code,
            code_verifier: str,
    ) -> GoogleAuthorizationResult:
        """
        Replace the real Google HTTP exchange.

        Most importantly, confirm that the same PKCE verifier generated
        when OAuth started reaches this callback exchange.
        """

        assert config == google_config
        assert authorization_code == "test-code"

        assert code_verifier == expected_code_verifier

        return GoogleAuthorizationResult(
            google_account_id="google-user-123",
            google_email="connected@gmail.com",
            refresh_token="plain-google-refresh-token",
            scopes=(
                "openid "
                "https://www.googleapis.com/auth/gmail.send"
            ),
        )

    # Store the original verifier under a different name so the
    # fake function can clearly compare against it.
    expected_code_verifier = code_verifier

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

    assert (
        result.google_account_id
        == "google-user-123"
    )

    assert (
        result.google_email
        == "connected@gmail.com"
    )

    assert stored_credential is not None

    assert (
        stored_credential.google_account_id
        == "google-user-123"
    )

    assert (
        stored_credential.google_email
        == "connected@gmail.com"
    )

    # Plain refresh token must never be stored in PostgreSQL.
    assert (
        stored_credential.encrypted_refresh_token
        != "plain-google-refresh-token"
    )

    # But decrypting it with our encryption key must recover
    # Google's original refresh token.
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
    A first Gmail connection cannot complete if Google returns no
    refresh token and we do not already have one stored.
    """

    user = create_test_user(
        db=db_session,
    )

    state, expected_code_verifier = create_oauth_state(
        db=db_session,
        user_id=user.id,
    )

    def fake_exchange(
            config,
            authorization_code,
            code_verifier,
    ) -> GoogleAuthorizationResult:
        """
        Simulate Google returning identity information but no
        refresh token.
        """

        assert config == google_config
        assert authorization_code == "test-code"

        # Again verify PKCE survived from /connect to /callback.
        assert code_verifier == expected_code_verifier

        return GoogleAuthorizationResult(
            google_account_id="google-user-456",
            google_email="missing-token@gmail.com",
            refresh_token=None,
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

    # Since this was the user's first Gmail connection and Google
    # returned no refresh token, no GmailCredential should be stored.
    stored_credential = get_gmail_credential_by_user_id(
        db=db_session,
        user_id=user.id,
    )

    assert stored_credential is None
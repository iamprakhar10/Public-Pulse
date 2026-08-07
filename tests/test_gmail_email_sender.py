"""
Tests for the real Gmail email sender.

Google network calls are mocked so these tests never send real email.
"""

from unittest.mock import MagicMock

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import delete

from app.config import GoogleOAuthConfig
from app.database.db import SessionLocal
from app.database.models import (
    GmailCredential,
    User,
)
from app.services import gmail_email_sender
from app.services.gmail_email_sender import (
    GmailConnectionRequiredError,
    GmailEmailSender,
    get_gmail_email_sender_for_user,
)
from app.utils.security import hash_password
from app.utils.token_encryption import encrypt_token


TEST_EMAIL = "gmail-sender-test@example.com"
TEST_PHONE = "9444444444"


@pytest.fixture
def db_session():
    """
    Provide a clean database session for Gmail sender tests.
    """

    db = SessionLocal()

    try:
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

        db.execute(delete(GmailCredential))

        db.execute(
            delete(User).where(
                User.email == TEST_EMAIL,
            )
        )

        db.commit()
        db.close()


@pytest.fixture
def test_user(
        db_session,
) -> User:
    """
    Create a real Public Pulse user for the tests.
    """

    user = User(
        name="Gmail Sender Test",
        email=TEST_EMAIL,
        phone=TEST_PHONE,
        hashed_password=hash_password(
            "test-password",
        ),
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


def test_gmail_email_sender_sends_message(
        monkeypatch,
) -> None:
    """
    GmailEmailSender should:

    - refresh Google credentials,
    - build the Gmail API client,
    - call users.messages.send().
    """

    config = GoogleOAuthConfig(
        client_id="test-client-id",
        client_secret="test-client-secret",
        redirect_uri=(
            "http://127.0.0.1:8000/gmail/callback"
        ),
    )

    sender = GmailEmailSender(
        refresh_token="test-refresh-token",
        sender_email="sender@gmail.com",
        scopes=[
            "https://www.googleapis.com/auth/gmail.send",
        ],
        config=config,
    )

    fake_credentials = MagicMock()

    monkeypatch.setattr(
        sender,
        "_build_credentials",
        lambda: fake_credentials,
    )

    fake_execute = MagicMock(
        return_value={
            "id": "gmail-message-123",
        }
    )

    fake_send = MagicMock()

    fake_send.return_value.execute = fake_execute

    fake_messages = MagicMock()
    fake_messages.send = fake_send

    fake_users = MagicMock()
    fake_users.messages.return_value = fake_messages

    fake_service = MagicMock()
    fake_service.users.return_value = fake_users

    fake_build = MagicMock(
        return_value=fake_service,
    )

    monkeypatch.setattr(
        gmail_email_sender,
        "build",
        fake_build,
    )

    sender.send_email(
        recipient="authority@example.com",
        subject="Broken road complaint",
        body="The road requires urgent repair.",
    )

    # Access token should be refreshed first.
    fake_credentials.refresh.assert_called_once()

    # Gmail API client should be created.
    fake_build.assert_called_once()

    # Gmail API send endpoint should be called once.
    fake_send.assert_called_once()

    call_kwargs = fake_send.call_args.kwargs

    assert call_kwargs["userId"] == "me"

    assert "raw" in call_kwargs["body"]

    # execute() performs the API request.
    fake_execute.assert_called_once()


def test_get_gmail_email_sender_for_user(
        db_session,
        test_user,
        monkeypatch,
) -> None:
    """
    A stored encrypted refresh token should be decrypted and used
    to construct GmailEmailSender.
    """

    encryption_key = (
        Fernet.generate_key().decode("utf-8")
    )

    encrypted_refresh_token = encrypt_token(
        token="plain-refresh-token",
        encryption_key=encryption_key,
    )

    gmail_credential = GmailCredential(
        user_id=test_user.id,
        google_account_id="google-user-123",
        google_email="connected@gmail.com",
        encrypted_refresh_token=(
            encrypted_refresh_token
        ),
        scopes=(
            "openid "
            "https://www.googleapis.com/auth/gmail.send"
        ),
    )

    db_session.add(gmail_credential)
    db_session.commit()

    monkeypatch.setattr(
        gmail_email_sender,
        "get_token_encryption_key",
        lambda: encryption_key,
    )

    monkeypatch.setattr(
        gmail_email_sender,
        "get_google_oauth_config",
        lambda: GoogleOAuthConfig(
            client_id="test-client-id",
            client_secret="test-client-secret",
            redirect_uri=(
                "http://127.0.0.1:8000/gmail/callback"
            ),
        ),
    )

    sender = get_gmail_email_sender_for_user(
        db=db_session,
        user_id=test_user.id,
    )

    assert isinstance(
        sender,
        GmailEmailSender,
    )

    assert (
        sender.refresh_token
        == "plain-refresh-token"
    )

    assert (
        sender.sender_email
        == "connected@gmail.com"
    )

    assert (
        "https://www.googleapis.com/auth/gmail.send"
        in sender.scopes
    )


def test_get_gmail_email_sender_requires_connection(
        db_session,
        test_user,
) -> None:
    """
    A user who has not connected Gmail cannot get a Gmail sender.
    """

    with pytest.raises(
        GmailConnectionRequiredError,
        match="Connect Gmail",
    ):
        get_gmail_email_sender_for_user(
            db=db_session,
            user_id=test_user.id,
        )
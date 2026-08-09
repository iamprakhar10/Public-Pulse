"""
Tests for Gmail status and disconnect routes.

Tests use the separate test database and never contact real Google.
"""

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.database.db import SessionLocal
from app.database.models import (
    GmailCredential,
    User,
)
from app.main import app
from app.utils.security import (
    create_access_token,
    hash_password,
)
from app.utils.token_encryption import encrypt_token


client = TestClient(app)


TEST_EMAIL = "gmail-connection-routes@example.com"
TEST_PHONE = "9555555555"


@pytest.fixture
def db_session():
    """
    Provide a clean database session for these tests.
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
    Create a real Public Pulse user in the test database.
    """

    user = User(
        name="Gmail Connection Route Test",
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


def authorization_headers(
        user: User,
) -> dict[str, str]:
    """
    Build the Public Pulse Authorization header.

    Keep this call consistent with the create_access_token()
    signature already used in your project.
    """

    token = create_access_token(
        data={
            "sub": str(user.id),
        }
    )

    return {
        "Authorization": f"Bearer {token}",
    }


def create_test_gmail_credential(
        db_session,
        test_user,
        encryption_key: str,
        *,
        google_account_id: str,
        google_email: str,
) -> GmailCredential:
    """
    Create a fake Gmail credential in the test database.
    """

    credential = GmailCredential(
        user_id=test_user.id,
        google_account_id=google_account_id,
        google_email=google_email,
        encrypted_refresh_token=encrypt_token(
            token="fake-refresh-token",
            encryption_key=encryption_key,
        ),
        scopes=(
            "openid "
            "https://www.googleapis.com/auth/gmail.send"
        ),
    )

    db_session.add(credential)
    db_session.commit()
    db_session.refresh(credential)

    return credential


def test_gmail_status_not_connected(
        db_session,
        test_user,
) -> None:
    """
    A user without Gmail credentials should show disconnected.
    """

    response = client.get(
        "/gmail/status",
        headers=authorization_headers(
            test_user,
        ),
    )

    assert response.status_code == 200

    assert response.json() == {
        "connected": False,
        "google_email": None,
    }


def test_gmail_status_connected(
        db_session,
        test_user,
) -> None:
    """
    A user with Gmail credentials should show connected.
    """

    encryption_key = (
        Fernet.generate_key().decode("utf-8")
    )

    create_test_gmail_credential(
        db_session=db_session,
        test_user=test_user,
        encryption_key=encryption_key,
        google_account_id="google-status-test",
        google_email="connected@gmail.com",
    )

    response = client.get(
        "/gmail/status",
        headers=authorization_headers(
            test_user,
        ),
    )

    assert response.status_code == 200

    assert response.json() == {
        "connected": True,
        "google_email": "connected@gmail.com",
    }


def test_disconnect_gmail(
        db_session,
        test_user,
        monkeypatch,
) -> None:
    """
    Disconnect should:

    - decrypt the stored refresh token,
    - revoke it with Google,
    - delete the local Gmail credential.
    """

    encryption_key = (
        Fernet.generate_key().decode("utf-8")
    )

    create_test_gmail_credential(
        db_session=db_session,
        test_user=test_user,
        encryption_key=encryption_key,
        google_account_id="google-disconnect-test",
        google_email="disconnect@gmail.com",
    )

    # The route must use the same key that encrypted our test token.
    monkeypatch.setattr(
        "app.routers.gmail.get_token_encryption_key",
        lambda: encryption_key,
    )

    revoked_tokens: list[str] = []

    def fake_revoke_google_token(
            token: str,
    ) -> None:
        revoked_tokens.append(token)

    # Never contact real Google from tests.
    monkeypatch.setattr(
        "app.routers.gmail.revoke_google_token",
        fake_revoke_google_token,
    )

    response = client.delete(
        "/gmail/disconnect",
        headers=authorization_headers(
            test_user,
        ),
    )

    assert response.status_code == 200

    assert response.json() == {
        "message": "Gmail disconnected successfully.",
    }

    # Proves the decrypted plaintext refresh token was supplied
    # to the revocation service.
    assert revoked_tokens == [
        "fake-refresh-token",
    ]

    # Gmail credential should now be gone.
    status_response = client.get(
        "/gmail/status",
        headers=authorization_headers(
            test_user,
        ),
    )

    assert status_response.status_code == 200

    assert status_response.json() == {
        "connected": False,
        "google_email": None,
    }


def test_disconnect_requires_existing_connection(
        db_session,
        test_user,
) -> None:
    """
    Disconnecting an account that is not connected returns 409.
    """

    response = client.delete(
        "/gmail/disconnect",
        headers=authorization_headers(
            test_user,
        ),
    )

    assert response.status_code == 409

    assert response.json() == {
        "detail": "Gmail is not connected.",
    }


def test_disconnect_does_not_delete_credential_when_google_fails(
        db_session,
        test_user,
        monkeypatch,
) -> None:
    """
    If Google revocation fails, retain the local refresh token so
    revocation can be retried later.
    """

    from app.services.google_token_revocation import (
        GoogleTokenRevocationError,
    )

    encryption_key = (
        Fernet.generate_key().decode("utf-8")
    )

    create_test_gmail_credential(
        db_session=db_session,
        test_user=test_user,
        encryption_key=encryption_key,
        google_account_id="google-revocation-failure",
        google_email="still-connected@gmail.com",
    )

    monkeypatch.setattr(
        "app.routers.gmail.get_token_encryption_key",
        lambda: encryption_key,
    )

    def fake_revoke_google_token(
            token: str,
    ) -> None:
        raise GoogleTokenRevocationError(
            "Google could not revoke Gmail access."
        )

    monkeypatch.setattr(
        "app.routers.gmail.revoke_google_token",
        fake_revoke_google_token,
    )

    response = client.delete(
        "/gmail/disconnect",
        headers=authorization_headers(
            test_user,
        ),
    )

    assert response.status_code == 502

    # Since Google revocation failed, the local credential
    # must still exist.
    status_response = client.get(
        "/gmail/status",
        headers=authorization_headers(
            test_user,
        ),
    )

    assert status_response.status_code == 200

    assert status_response.json() == {
        "connected": True,
        "google_email": "still-connected@gmail.com",
    }
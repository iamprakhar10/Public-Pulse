"""
Tests for Gmail status and disconnect endpoints.

These tests use the test database, so they do not affect the user's
real Gmail connection stored in the development database.
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
    Provide a clean database session for Gmail connection route tests.
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
    Create the authenticated Public Pulse test user.
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
    Create the Authorization header for a Public Pulse user.
    """

    token = create_access_token(
        data={
            "sub": str(user.id),
        }
    )

    return {
        "Authorization": f"Bearer {token}",
    }


def test_gmail_status_not_connected(
        db_session,
        test_user,
) -> None:
    """
    A user without GmailCredential should be reported as disconnected.
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
    A user with GmailCredential should be reported as connected.
    """

    encryption_key = (
        Fernet.generate_key().decode("utf-8")
    )

    credential = GmailCredential(
        user_id=test_user.id,
        google_account_id="google-account-status-test",
        google_email="connected@gmail.com",
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
) -> None:
    """
    Disconnect should delete the user's GmailCredential.
    """

    encryption_key = (
        Fernet.generate_key().decode("utf-8")
    )

    credential = GmailCredential(
        user_id=test_user.id,
        google_account_id="google-account-disconnect-test",
        google_email="disconnect@gmail.com",
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

    # Status should now report disconnected.
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
    Disconnecting when Gmail is not connected should return 409.
    """

    response = client.delete(
        "/gmail/disconnect",
        headers=authorization_headers(
            test_user,
        ),
    )

    assert response.status_code == 409

    assert (
        response.json()["detail"]
        == "Gmail is not connected."
    )